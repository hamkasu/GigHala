package com.gighala.app.util

import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import java.util.concurrent.ConcurrentHashMap

/**
 * In-memory cookie jar that persists the Flask session cookie across requests.
 * The Flask backend uses session cookies for authentication — this ensures
 * every API call carries the active session without modifying the backend.
 */
class PersistentCookieJar : CookieJar {

    private val store = ConcurrentHashMap<String, MutableList<Cookie>>()

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val host = url.host
        store.getOrPut(host) { mutableListOf() }.apply {
            removeAll { existing -> cookies.any { it.name == existing.name } }
            addAll(cookies)
        }
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> =
        store[url.host] ?: emptyList()

    fun clearAll() = store.clear()

    fun hasSession(): Boolean =
        store.values.flatten().any { it.name == "session" }

    /** Inject a raw cookie string from a WebView (e.g. after social OAuth). */
    fun injectRawCookies(host: String, rawCookieHeader: String) {
        val url = okhttp3.HttpUrl.Builder()
            .scheme("https").host(host).build()
        val cookies = rawCookieHeader.split(";")
            .mapNotNull { part ->
                val kv = part.trim().split("=", limit = 2)
                if (kv.size == 2) {
                    Cookie.Builder()
                        .domain(host)
                        .name(kv[0].trim())
                        .value(kv[1].trim())
                        .build()
                } else null
            }
        if (cookies.isNotEmpty()) saveFromResponse(url, cookies)
    }
}
