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
}
