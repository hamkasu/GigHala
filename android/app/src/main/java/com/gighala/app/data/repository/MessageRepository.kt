package com.gighala.app.data.repository

import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MessageRepository @Inject constructor(private val api: ApiService) {

    suspend fun getConversations(): Result<List<ConversationDto>> = runCatching {
        api.getConversations().body() ?: error("Empty response")
    }

    suspend fun getConversation(id: Int): Result<ConversationDetailResponse> = runCatching {
        api.getConversation(id).body() ?: error("Empty response")
    }

    suspend fun sendMessage(conversationId: Int, content: String): Result<SendMessageResponse> =
        runCatching {
            val response = api.sendMessage(SendMessageRequest(conversationId, content))
            val body = response.body() ?: error("Empty response")
            if (!body.success) error("Failed to send message")
            body
        }

    suspend fun pollMessages(conversationId: Int, lastId: Int): Result<List<MessageDto>> =
        runCatching {
            api.pollMessages(conversationId, lastId).body() ?: emptyList()
        }

    suspend fun getNotifications(): Result<NotificationsResponse> = runCatching {
        api.getNotifications().body() ?: error("Empty response")
    }

    suspend fun markNotificationsRead(ids: List<Int>): Result<Unit> = runCatching {
        api.markNotificationsRead(mapOf("ids" to ids))
    }

    suspend fun getBillingStats(): Result<BillingStatsResponse> = runCatching {
        api.getBillingStats().body() ?: error("Empty response")
    }
}
