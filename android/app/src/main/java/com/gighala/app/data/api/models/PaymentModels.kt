package com.gighala.app.data.api.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class EscrowDto(
    val id: Int,
    val status: String,
    val amount: Double,
    @Json(name = "platform_fee") val platformFee: Double,
    @Json(name = "net_amount") val netAmount: Double,
    @Json(name = "escrow_number") val escrowNumber: String,
    @Json(name = "gig_id") val gigId: Int,
    @Json(name = "funded_at") val fundedAt: String? = null
)

@JsonClass(generateAdapter = true)
data class CheckoutSessionRequest(
    @Json(name = "gig_id") val gigId: Int,
    val amount: Double? = null,
    val mobile: Boolean = true
)

@JsonClass(generateAdapter = true)
data class FeeBreakdown(
    @Json(name = "gig_amount") val gigAmount: Double,
    @Json(name = "platform_fee") val platformFee: Double,
    @Json(name = "processing_fee") val processingFee: Double,
    @Json(name = "total_charge") val totalCharge: Double,
    @Json(name = "freelancer_receives") val freelancerReceives: Double
)

@JsonClass(generateAdapter = true)
data class CheckoutSessionResponse(
    val success: Boolean = false,
    @Json(name = "checkout_url") val checkoutUrl: String? = null,
    @Json(name = "session_id") val sessionId: String? = null,
    @Json(name = "fee_breakdown") val feeBreakdown: FeeBreakdown? = null,
    val error: String? = null
)

data class PaymentResult(val status: String, val gigId: Int?)
