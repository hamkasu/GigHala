package com.gighala.app.data.repository

import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.*
import com.gighala.app.data.local.GigDao
import org.json.JSONObject
import retrofit2.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class GigRepository @Inject constructor(
    private val api: ApiService,
    private val gigDao: GigDao
) {
    suspend fun getGigs(
        page: Int = 1,
        category: String? = null,
        workType: String? = null,
        search: String? = null
    ): Result<List<GigDto>> = runCatching {
        val response = api.getGigs(
            category = category,
            search = search?.takeIf { it.isNotBlank() },
            page = page,
            workType = workType
        )
        val gigs = response.bodyOrError("Failed to load gigs")
        // Cache page 1 for offline fallback
        if (page == 1 && search.isNullOrBlank()) {
            gigDao.evictOlderThan(System.currentTimeMillis() - 24 * 60 * 60 * 1000)
            gigDao.insertAll(gigs.map { it.toCached() })
        }
        gigs
    }

    suspend fun getGig(id: Int): Result<GigDto> = runCatching {
        api.getGig(id).bodyOrError("Gig not found")
    }

    suspend fun createGig(request: CreateGigRequest): Result<CreateGigResponse> = runCatching {
        val response = api.createGig(request)
        val body = response.bodyOrError("Failed to create gig")
        if (!body.success) error(body.message ?: "Failed to create gig")
        body
    }

    suspend fun applyToGig(gigId: Int, request: ApplyGigRequest): Result<ApplyGigResponse> =
        runCatching {
            val response = api.applyToGig(gigId, request)
            val body = response.bodyOrError("Failed to apply")
            if (!body.success) error(body.message ?: "Failed to apply")
            body
        }

    suspend fun searchGigs(query: String, page: Int = 1): Result<GigSearchResponse> = runCatching {
        api.searchGigs(query, page).bodyOrError("Search failed")
    }

    suspend fun getApplications(gigId: Int): Result<List<ApplicationDto>> = runCatching {
        api.getGigApplications(gigId).bodyOrError("Failed to load applications")
    }

    suspend fun shortlistApplication(applicationId: Int): Result<ShortlistResponse> = runCatching {
        api.shortlistApplication(applicationId).bodyOrError("Failed to shortlist")
    }

    private fun <T> Response<T>.bodyOrError(fallback: String): T {
        if (isSuccessful) return body() ?: error(fallback)
        val errJson = errorBody()?.string()
        val msg = try {
            if (errJson != null) {
                val obj = JSONObject(errJson)
                obj.optString("error").ifEmpty { obj.optString("message", fallback) }
            } else fallback
        } catch (_: Exception) {
            fallback
        }
        error(msg)
    }
}
