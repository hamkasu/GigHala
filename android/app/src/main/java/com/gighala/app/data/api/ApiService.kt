package com.gighala.app.data.api

import com.gighala.app.data.api.models.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ── Auth ──────────────────────────────────────────────────────────────────

    @POST("api/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @POST("api/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @GET("api/logout")
    suspend fun logout(): Response<AuthResponse>

    @POST("api/2fa/verify")
    suspend fun verify2fa(@Body request: Verify2faRequest): Response<AuthResponse>

    @GET("api/me")
    suspend fun getCurrentUser(): Response<UserDto>

    @POST("api/forgot-password")
    suspend fun forgotPassword(@Body request: ForgotPasswordRequest): Response<AuthResponse>

    // ── Gigs ──────────────────────────────────────────────────────────────────

    @GET("api/gigs")
    suspend fun getGigs(
        @Query("category") category: String? = null,
        @Query("location") location: String? = null,
        @Query("search") search: String? = null
    ): Response<List<GigDto>>

    @GET("api/gigs/{id}")
    suspend fun getGig(@Path("id") id: Int): Response<GigDto>

    @POST("api/gigs")
    suspend fun createGig(@Body request: CreateGigRequest): Response<CreateGigResponse>

    @POST("api/gigs/{id}/apply")
    suspend fun applyToGig(
        @Path("id") gigId: Int,
        @Body request: ApplyGigRequest
    ): Response<ApplyGigResponse>

    @GET("api/gigs/{id}/applications")
    suspend fun getGigApplications(@Path("id") gigId: Int): Response<List<ApplicationDto>>

    @POST("api/gigs/{id}/cancel")
    suspend fun cancelGig(@Path("id") gigId: Int): Response<AuthResponse>

    @POST("api/gigs/{id}/mark-completed")
    suspend fun markGigCompleted(@Path("id") gigId: Int): Response<AuthResponse>

    @POST("api/gigs/{id}/approve-work")
    suspend fun approveWork(@Path("id") gigId: Int): Response<AuthResponse>

    // ── Applications ─────────────────────────────────────────────────────────

    @POST("api/applications/{id}/accept")
    suspend fun acceptApplication(@Path("id") applicationId: Int): Response<AuthResponse>

    @POST("api/applications/{id}/reject")
    suspend fun rejectApplication(@Path("id") applicationId: Int): Response<AuthResponse>

    // ── Search ────────────────────────────────────────────────────────────────

    @GET("api/search")
    suspend fun searchGigs(
        @Query("q") query: String,
        @Query("page") page: Int = 1
    ): Response<GigSearchResponse>

    @GET("api/search/suggestions")
    suspend fun getSearchSuggestions(@Query("q") query: String): Response<List<String>>

    // ── Messages ─────────────────────────────────────────────────────────────

    @GET("api/messages/conversations")
    suspend fun getConversations(): Response<List<ConversationDto>>

    @GET("api/messages/{conversationId}")
    suspend fun getConversation(
        @Path("conversationId") conversationId: Int
    ): Response<ConversationDetailResponse>

    @POST("api/messages/send")
    suspend fun sendMessage(@Body request: SendMessageRequest): Response<SendMessageResponse>

    @POST("api/messages/start")
    suspend fun startConversation(
        @Body request: StartConversationRequest
    ): Response<StartConversationResponse>

    @GET("api/messages/poll/{conversationId}")
    suspend fun pollMessages(
        @Path("conversationId") conversationId: Int,
        @Query("last_id") lastId: Int = 0
    ): Response<List<MessageDto>>

    // ── Notifications ─────────────────────────────────────────────────────────

    @GET("api/notifications")
    suspend fun getNotifications(): Response<NotificationsResponse>

    @POST("api/notifications/mark-read")
    suspend fun markNotificationsRead(@Body ids: Map<String, List<Int>>): Response<AuthResponse>

    // ── Billing / Dashboard ───────────────────────────────────────────────────

    @GET("api/billing/stats")
    suspend fun getBillingStats(): Response<BillingStatsResponse>
}
