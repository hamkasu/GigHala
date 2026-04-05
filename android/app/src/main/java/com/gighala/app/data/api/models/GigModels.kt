package com.gighala.app.data.api.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class GigListResponse(
    val gigs: List<GigDto>,
    val total: Int = 0,
    val page: Int = 1,
    val pages: Int = 1,
    @Json(name = "per_page") val perPage: Int = 20
)

@JsonClass(generateAdapter = true)
data class GigDto(
    val id: Int,
    val title: String,
    val description: String,
    val category: String,
    val status: String,
    @Json(name = "budget_min") val budgetMin: Double? = null,
    @Json(name = "budget_max") val budgetMax: Double? = null,
    val location: String? = null,
    @Json(name = "work_type") val workType: String? = null,
    val deadline: String? = null,
    @Json(name = "created_at") val createdAt: String? = null,
    @Json(name = "is_halal_verified") val isHalalVerified: Boolean = false,
    @Json(name = "cover_letter_required") val coverLetterRequired: Boolean = false,
    @Json(name = "preferred_skills") val preferredSkills: String? = null,
    val client: GigClientDto? = null,
    @Json(name = "application_count") val applicationCount: Int = 0,
    @Json(name = "user_has_applied") val userHasApplied: Boolean = false,
    @Json(name = "gig_photos") val gigPhotos: List<GigPhotoDto> = emptyList()
)

@JsonClass(generateAdapter = true)
data class GigClientDto(
    val id: Int,
    val username: String,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "profile_photo") val profilePhoto: String? = null,
    val rating: Double = 0.0,
    @Json(name = "is_verified") val isVerified: Boolean = false
)

@JsonClass(generateAdapter = true)
data class GigPhotoDto(
    val id: Int,
    val url: String
)

@JsonClass(generateAdapter = true)
data class CreateGigRequest(
    val title: String,
    val description: String,
    val category: String,
    @Json(name = "budget_min") val budgetMin: Double? = null,
    @Json(name = "budget_max") val budgetMax: Double? = null,
    val location: String? = null,
    @Json(name = "work_type") val workType: String = "remote",
    val deadline: String? = null,
    @Json(name = "preferred_skills") val preferredSkills: String? = null,
    @Json(name = "cover_letter_required") val coverLetterRequired: Boolean = false
)

@JsonClass(generateAdapter = true)
data class CreateGigResponse(
    val success: Boolean,
    val message: String? = null,
    @Json(name = "gig_id") val gigId: Int? = null
)

@JsonClass(generateAdapter = true)
data class ApplyGigRequest(
    @Json(name = "proposal_text") val proposalText: String,
    @Json(name = "applied_rate") val appliedRate: Double? = null,
    @Json(name = "cover_letter") val coverLetter: String? = null
)

@JsonClass(generateAdapter = true)
data class ApplyGigResponse(
    val success: Boolean,
    val message: String? = null
)

@JsonClass(generateAdapter = true)
data class ApplicationDto(
    val id: Int,
    @Json(name = "gig_id") val gigId: Int,
    val status: String,
    @Json(name = "proposal_text") val proposalText: String? = null,
    @Json(name = "applied_rate") val appliedRate: Double? = null,
    @Json(name = "created_at") val createdAt: String? = null,
    val worker: GigClientDto? = null
)

@JsonClass(generateAdapter = true)
data class GigSearchResponse(
    val gigs: List<GigDto>,
    val query: String? = null,
    val total: Int = 0
)

// Room entity for local caching
@Entity(tableName = "cached_gigs")
data class CachedGig(
    @PrimaryKey val id: Int,
    val title: String,
    val description: String,
    val category: String,
    val status: String,
    val budgetMin: Double?,
    val budgetMax: Double?,
    val location: String?,
    val workType: String?,
    val isHalalVerified: Boolean,
    val cachedAt: Long = System.currentTimeMillis()
)

fun GigDto.toCached() = CachedGig(
    id = id,
    title = title,
    description = description,
    category = category,
    status = status,
    budgetMin = budgetMin,
    budgetMax = budgetMax,
    location = location,
    workType = workType,
    isHalalVerified = isHalalVerified
)
