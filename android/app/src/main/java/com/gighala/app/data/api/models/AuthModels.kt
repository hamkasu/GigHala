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
    val phone: String? = null,
    val language: String? = null,
    @Json(name = "portfolio_url") val portfolioUrl: String? = null,
    @Json(name = "ic_number") val icNumber: String? = null,
    @Json(name = "socso_membership_number") val socsoMembershipNumber: String? = null,
    @Json(name = "socso_consent") val socsoConsent: Boolean = false,
    @Json(name = "bank_name") val bankName: String? = null,
    @Json(name = "bank_account_number") val bankAccountNumber: String? = null,
    @Json(name = "bank_account_holder") val bankAccountHolder: String? = null,
    @Json(name = "available_for_fractional") val availableForFractional: Boolean = false,
    @Json(name = "fractional_role_type") val fractionalRoleType: String? = null,
    @Json(name = "fractional_days_available") val fractionalDaysAvailable: Double = 1.0,
    @Json(name = "halal_verified") val halalVerified: Boolean = false,
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

// ── Profile update ─────────────────────────────────────────────────────────

@JsonClass(generateAdapter = true)
data class UpdateProfileRequest(
    @Json(name = "full_name") val fullName: String,
    val phone: String,
    val location: String,
    val bio: String,
    val skills: List<String>,
    @Json(name = "user_type") val userType: String,
    val language: String,
    @Json(name = "portfolio_url") val portfolioUrl: String,
    @Json(name = "ic_number") val icNumber: String,
    @Json(name = "socso_membership_number") val socsoMembershipNumber: String,
    @Json(name = "socso_consent") val socsoConsent: Boolean
)

@JsonClass(generateAdapter = true)
data class TwoFaStatusResponse(
    @Json(name = "totp_enabled") val totpEnabled: Boolean = false,
    @Json(name = "totp_enabled_at") val totpEnabledAt: String? = null
)
