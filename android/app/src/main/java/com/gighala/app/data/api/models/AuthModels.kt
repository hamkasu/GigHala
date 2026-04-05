package com.gighala.app.data.api.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(
    val email: String,
    val password: String
)

@JsonClass(generateAdapter = true)
data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "user_type") val userType: String = "both",
    @Json(name = "privacy_consent") val privacyConsent: Boolean = true,
    @Json(name = "socso_consent") val socsoConsent: Boolean = true
)

@JsonClass(generateAdapter = true)
data class AuthResponse(
    val success: Boolean = false,
    val message: String? = null,
    val error: String? = null,
    val user: UserDto? = null,
    @Json(name = "requires_2fa") val requires2fa: Boolean = false
)

@JsonClass(generateAdapter = true)
data class UserDto(
    val id: Int,
    val username: String,
    val email: String,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "user_type") val userType: String = "both",
    @Json(name = "profile_photo") val profilePhoto: String? = null,
    val bio: String? = null,
    val location: String? = null,
    val skills: String? = null,
    val rating: Double = 0.0,
    @Json(name = "review_count") val reviewCount: Int = 0,
    @Json(name = "total_earnings") val totalEarnings: Double = 0.0,
    @Json(name = "completed_gigs") val completedGigs: Int = 0,
    @Json(name = "is_verified") val isVerified: Boolean = false,
    @Json(name = "is_admin") val isAdmin: Boolean = false,
    @Json(name = "totp_enabled") val totpEnabled: Boolean = false,
    @Json(name = "phone_verified") val phoneVerified: Boolean = false
)

@JsonClass(generateAdapter = true)
data class Verify2faRequest(
    val code: String
)

@JsonClass(generateAdapter = true)
data class ForgotPasswordRequest(
    val email: String
)
