package com.gighala.app.data.repository

import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.*
import com.gighala.app.data.local.GigDao
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
        workType: String? = null
    ): Result<GigListResponse> = runCatching {
        val response = api.getGigs(page = page, category = category, workType = workType)
        val body = response.body() ?: error("Empty response")
        // Cache page 1 for offline fallback
        if (page == 1) {
            gigDao.evictOlderThan(System.currentTimeMillis() - 24 * 60 * 60 * 1000)
            gigDao.insertAll(body.gigs.map { it.toCached() })
        }
        body
    }

    suspend fun getGig(id: Int): Result<GigDto> = runCatching {
        val response = api.getGig(id)
        response.body() ?: error("Gig not found")
    }

    suspend fun createGig(request: CreateGigRequest): Result<CreateGigResponse> = runCatching {
        val response = api.createGig(request)
        val body = response.body() ?: error("Empty response")
        if (!body.success) error(body.message ?: "Failed to create gig")
        body
    }

    suspend fun applyToGig(gigId: Int, request: ApplyGigRequest): Result<ApplyGigResponse> =
        runCatching {
            val response = api.applyToGig(gigId, request)
            val body = response.body() ?: error("Empty response")
            if (!body.success) error(body.message ?: "Failed to apply")
            body
        }

    suspend fun searchGigs(query: String, page: Int = 1): Result<GigSearchResponse> = runCatching {
        val response = api.searchGigs(query, page)
        response.body() ?: error("Empty response")
    }

    suspend fun getApplications(gigId: Int): Result<List<ApplicationDto>> = runCatching {
        val response = api.getGigApplications(gigId)
        response.body() ?: error("Empty response")
    }
}
