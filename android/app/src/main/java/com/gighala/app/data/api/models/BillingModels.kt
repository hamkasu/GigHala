package com.gighala.app.data.api.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class WalletDto(
    @Json(name = "user_id") val userId: Int = 0,
    val balance: Double = 0.0,
    @Json(name = "held_balance") val heldBalance: Double = 0.0,
    @Json(name = "total_earned") val totalEarned: Double = 0.0,
    @Json(name = "total_spent") val totalSpent: Double = 0.0,
    val currency: String = "MYR",
    @Json(name = "available_balance") val availableBalance: Double = 0.0
)

@JsonClass(generateAdapter = true)
data class InvoiceDto(
    val id: Int,
    @Json(name = "invoice_number") val invoiceNumber: String,
    @Json(name = "gig_title") val gigTitle: String,
    val amount: Double,
    @Json(name = "total_amount") val totalAmount: Double,
    val status: String,
    @Json(name = "created_at") val createdAt: String,
    val role: String = "client"
)
