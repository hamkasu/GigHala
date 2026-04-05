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
data class BillingStatsResponse(
    @Json(name = "available_balance") val availableBalance: Double = 0.0,
    @Json(name = "total_earned") val totalEarned: Double = 0.0,
    @Json(name = "held_balance") val heldBalance: Double = 0.0,
    @Json(name = "total_spent") val totalSpent: Double = 0.0,
    @Json(name = "total_socso") val totalSocso: Double = 0.0,
    // dashboard fields
    @Json(name = "completed_gigs") val completedGigs: Int = 0,
    @Json(name = "active_gigs") val activeGigs: Int = 0
)

@JsonClass(generateAdapter = true)
data class InvoiceDto(
    val id: Int,
    @Json(name = "invoice_number") val invoiceNumber: String,
    @Json(name = "gig_id") val gigId: Int? = null,
    @Json(name = "gig_title") val gigTitle: String,
    @Json(name = "gig_code") val gigCode: String? = null,
    @Json(name = "client_id") val clientId: Int? = null,
    @Json(name = "client_name") val clientName: String? = null,
    @Json(name = "freelancer_id") val freelancerId: Int? = null,
    @Json(name = "freelancer_name") val freelancerName: String? = null,
    val amount: Double,
    @Json(name = "platform_fee") val platformFee: Double = 0.0,
    @Json(name = "tax_amount") val taxAmount: Double = 0.0,
    @Json(name = "total_amount") val totalAmount: Double,
    val status: String,
    @Json(name = "payment_method") val paymentMethod: String? = null,
    @Json(name = "created_at") val createdAt: String,
    @Json(name = "issue_date") val issueDate: String? = null,
    @Json(name = "paid_at") val paidAt: String? = null,
    @Json(name = "due_date") val dueDate: String? = null,
    val role: String = "client"
)

@JsonClass(generateAdapter = true)
data class TransactionDto(
    val id: Int,
    @Json(name = "gig_id") val gigId: Int? = null,
    @Json(name = "gig_title") val gigTitle: String? = null,
    @Json(name = "client_name") val clientName: String? = null,
    @Json(name = "freelancer_name") val freelancerName: String? = null,
    val amount: Double,
    val commission: Double = 0.0,
    @Json(name = "net_amount") val netAmount: Double = 0.0,
    @Json(name = "payment_method") val paymentMethod: String? = null,
    val status: String = "",
    @Json(name = "transaction_date") val transactionDate: String? = null,
    val date: String? = null,
    val type: String = "received"  // "sent" | "received"
)

@JsonClass(generateAdapter = true)
data class PayoutDto(
    val id: Int,
    @Json(name = "payout_number") val payoutNumber: String,
    val amount: Double,
    val fee: Double = 0.0,
    @Json(name = "net_amount") val netAmount: Double,
    @Json(name = "payment_method") val paymentMethod: String? = null,
    @Json(name = "payout_method") val payoutMethod: String? = null,
    @Json(name = "bank_name") val bankName: String? = null,
    @Json(name = "account_number") val accountNumber: String? = null,
    val status: String,
    @Json(name = "requested_at") val requestedAt: String,
    @Json(name = "completed_at") val completedAt: String? = null,
    @Json(name = "failure_reason") val failureReason: String? = null
)

@JsonClass(generateAdapter = true)
data class SocsoContributionDto(
    val id: Int,
    @Json(name = "gig_id") val gigId: Int? = null,
    @Json(name = "gross_amount") val grossAmount: Double,
    @Json(name = "platform_commission") val platformCommission: Double = 0.0,
    @Json(name = "net_earnings") val netEarnings: Double = 0.0,
    @Json(name = "socso_amount") val socsoAmount: Double,
    @Json(name = "final_payout") val finalPayout: Double = 0.0,
    @Json(name = "contribution_month") val contributionMonth: String? = null,
    @Json(name = "contribution_year") val contributionYear: Int? = null,
    @Json(name = "contribution_type") val contributionType: String? = null,
    @Json(name = "remitted_to_socso") val remittedToSocso: Boolean = false,
    @Json(name = "remittance_date") val remittanceDate: String? = null,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class SocsoTotals(
    @Json(name = "total_socso") val totalSocso: Double = 0.0,
    @Json(name = "total_net_earnings") val totalNetEarnings: Double = 0.0,
    @Json(name = "total_final_payout") val totalFinalPayout: Double = 0.0,
    @Json(name = "transaction_count") val transactionCount: Int = 0
)

@JsonClass(generateAdapter = true)
data class SocsoContributionsResponse(
    val contributions: List<SocsoContributionDto>,
    val totals: SocsoTotals = SocsoTotals()
)

@JsonClass(generateAdapter = true)
data class PayoutRequest(
    val amount: Double,
    @Json(name = "payment_method") val paymentMethod: String,
    @Json(name = "bank_name") val bankName: String,
    @Json(name = "account_number") val accountNumber: String,
    @Json(name = "account_name") val accountName: String
)

@JsonClass(generateAdapter = true)
data class PayoutResponse(
    val message: String? = null,
    @Json(name = "payout_number") val payoutNumber: String? = null,
    val status: String? = null,
    val amount: Double? = null,
    val fee: Double? = null,
    @Json(name = "net_amount") val netAmount: Double? = null,
    val error: String? = null
)
