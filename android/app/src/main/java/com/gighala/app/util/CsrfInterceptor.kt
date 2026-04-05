package com.gighala.app.util

import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import org.json.JSONObject
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/**
 * Fetches a CSRF token from /api/csrf-token once (lazy, thread-safe) and
 * attaches it as X-CSRFToken on every mutating request (POST/PUT/PATCH/DELETE).
 * Flask-WTF accepts the token via this header.
 */
class CsrfInterceptor : Interceptor {

    @Volatile private var token: String? = null
    private val lock = ReentrantLock()

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()

        // Only mutating requests need the CSRF token
        if (original.method == "GET" || original.method == "HEAD") {
            return chain.proceed(original)
        }

        val csrfToken = getOrFetchToken(chain)
        if (csrfToken == null) return chain.proceed(original)

        val request = original.newBuilder()
            .header("X-CSRFToken", csrfToken)
            .build()
        val response = chain.proceed(request)

        // If the server rejects the token (403), invalidate and retry once
        if (response.code == 403) {
            response.close()
            lock.withLock { token = null }
            val freshToken = fetchToken(chain) ?: return chain.proceed(request)
            lock.withLock { token = freshToken }
            return chain.proceed(
                original.newBuilder().header("X-CSRFToken", freshToken).build()
            )
        }

        return response
    }

    private fun getOrFetchToken(chain: Interceptor.Chain): String? {
        token?.let { return it }
        return lock.withLock {
            token ?: fetchToken(chain)?.also { token = it }
        }
    }

    private fun fetchToken(chain: Interceptor.Chain): String? {
        return try {
            val baseUrl = chain.request().url.run { "${scheme}://${host}${if (port != 443 && port != 80) ":$port" else ""}" }
            val tokenRequest = Request.Builder()
                .url("$baseUrl/api/csrf-token")
                .get()
                .build()
            val response = chain.proceed(tokenRequest)
            val body = response.body?.string() ?: return null
            response.close()
            JSONObject(body).optString("csrf_token").takeIf { it.isNotEmpty() }
        } catch (_: Exception) {
            null
        }
    }

    fun invalidate() { lock.withLock { token = null } }
}
