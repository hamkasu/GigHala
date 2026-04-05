package com.gighala.app.data.api.models

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ConversationDto(
    val id: Int,
    @Json(name = "gig_id") val gigId: Int? = null,
    @Json(name = "gig_title") val gigTitle: String? = null,
    @Json(name = "other_user") val otherUser: GigClientDto,
    @Json(name = "last_message") val lastMessage: String? = null,
    @Json(name = "last_message_time") val lastMessageTime: String? = null,
    @Json(name = "unread_count") val unreadCount: Int = 0
)

@JsonClass(generateAdapter = true)
data class MessageDto(
    val id: Int,
    @Json(name = "conversation_id") val conversationId: Int,
    @Json(name = "sender_id") val senderId: Int,
    val content: String,
    @Json(name = "image_url") val imageUrl: String? = null,
    @Json(name = "created_at") val createdAt: String,
    @Json(name = "is_read") val isRead: Boolean = false
)

@JsonClass(generateAdapter = true)
data class ConversationDetailResponse(
    val conversation: ConversationDto,
    val messages: List<MessageDto>
)

@JsonClass(generateAdapter = true)
data class SendMessageRequest(
    @Json(name = "conversation_id") val conversationId: Int,
    val content: String
)

@JsonClass(generateAdapter = true)
data class SendMessageResponse(
    val success: Boolean,
    val message: MessageDto? = null
)

@JsonClass(generateAdapter = true)
data class StartConversationRequest(
    @Json(name = "user_id") val userId: Int,
    @Json(name = "gig_id") val gigId: Int? = null
)

@JsonClass(generateAdapter = true)
data class StartConversationResponse(
    val success: Boolean,
    @Json(name = "conversation_id") val conversationId: Int? = null
)

@JsonClass(generateAdapter = true)
data class NotificationDto(
    val id: Int,
    val type: String,
    val subject: String,
    val body: String,
    @Json(name = "is_read") val isRead: Boolean = false,
    @Json(name = "created_at") val createdAt: String
)

@JsonClass(generateAdapter = true)
data class NotificationsResponse(
    val notifications: List<NotificationDto>,
    @Json(name = "unread_count") val unreadCount: Int = 0
)

@JsonClass(generateAdapter = true)
data class BillingStatsResponse(
    @Json(name = "total_earnings") val totalEarnings: Double = 0.0,
    @Json(name = "pending_earnings") val pendingEarnings: Double = 0.0,
    @Json(name = "available_balance") val availableBalance: Double = 0.0,
    @Json(name = "completed_gigs") val completedGigs: Int = 0,
    @Json(name = "active_gigs") val activeGigs: Int = 0,
    @Json(name = "posted_gigs") val postedGigs: Int = 0,
    @Json(name = "total_spent") val totalSpent: Double = 0.0
)
