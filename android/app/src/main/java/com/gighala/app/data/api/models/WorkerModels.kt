package com.gighala.app.data.api.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class WorkerDto(
    val id: Int,
    val username: String,
    val name: String,
    val location: String? = null,
    val rating: Double = 0.0,
    @Json(name = "review_count") val reviewCount: Int = 0,
    @Json(name = "completed_gigs") val completedGigs: Int = 0,
    @Json(name = "is_verified") val isVerified: Boolean? = false,
    @Json(name = "halal_verified") val halalVerified: Boolean? = false,
    @Json(name = "profile_photo") val profilePhoto: String? = null
)

@JsonClass(generateAdapter = true)
data class WorkerUpdateDto(
    val id: Int,
    val title: String,
    @Json(name = "category_name") val categoryName: String,
    @Json(name = "category_id") val categoryId: Int,
    @Json(name = "category_slug") val categorySlug: String,
    @Json(name = "category_icon") val categoryIcon: String? = null,
    val skills: List<String> = emptyList(),
    @Json(name = "starting_price") val startingPrice: Double = 0.0,
    @Json(name = "price_type") val priceType: String = "fixed",
    @Json(name = "hourly_rate") val hourlyRate: Double? = null,
    @Json(name = "fixed_rate") val fixedRate: Double? = null,
    @Json(name = "has_premium") val hasPremium: Boolean = false,
    @Json(name = "updated_at") val updatedAt: String? = null,
    val worker: WorkerDto
)

@JsonClass(generateAdapter = true)
data class WorkerUpdatesResponse(
    val updates: List<WorkerUpdateDto>,
    val total: Int = 0,
    val page: Int = 1,
    val pages: Int = 1,
    val limit: Int = 24,
    val days: Int = 30
)
