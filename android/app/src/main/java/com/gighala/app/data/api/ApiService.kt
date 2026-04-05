package com.gighala.app.data.api

import com.gighala.app.data.api.models.*
import okhttp3.ResponseBody
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

    @GET("api/profile")
    suspend fun getProfile(): Response<UserDto>

    @PUT("api/profile")
    suspend fun updateProfile(@Body request: UpdateProfileRequest): Response<AuthResponse>

    @FormUrlEncoded
    @POST("settings/password")
    suspend fun changePassword(
        @Field("current_password") currentPassword: String,
        @Field("new_password") newPassword: String,
        @Field("confirm_password") confirmPassword: String
    ): Response<ResponseBody>

    @FormUrlEncoded
    @POST("settings/bank")
    suspend fun updateBankInfo(
        @Field("bank_name") bankName: String,
        @Field("bank_account_number") accountNumber: String,
        @Field("bank_account_holder") accountHolder: String
    ): Response<ResponseBody>

    @FormUrlEncoded
    @POST("settings/fractional")
    suspend fun updateFractional(
        @Field("available_for_fractional") available: Boolean,
        @Field("fractional_role_type") roleType: String,
        @Field("fractional_days_available") daysAvailable: Float
    ): Response<ResponseBody>

    @GET("api/2fa/status")
    suspend fun get2faStatus(): Response<TwoFaStatusResponse>

    @POST("api/2fa/disable")
    suspend fun disable2fa(): Response<AuthResponse>

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

    // ── Worker Updates ────────────────────────────────────────────────────────

    @GET("api/worker-updates")
    suspend fun getWorkerUpdates(
        @Query("days") days: Int = 30,
        @Query("category_id") categoryId: Int? = null,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 24
    ): Response<WorkerUpdatesResponse>

    // ── Billing / Dashboard ───────────────────────────────────────────────────

    @GET("api/billing/stats")
    suspend fun getBillingStats(): Response<BillingStatsResponse>

    @GET("api/billing/wallet")
    suspend fun getWallet(): Response<WalletDto>

    @GET("api/billing/invoices")
    suspend fun getInvoices(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 50,
        @Query("status") status: String? = null
    ): Response<List<InvoiceDto>>

    @GET("api/billing/transactions")
    suspend fun getTransactions(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 50,
        @Query("type") type: String? = null
    ): Response<List<TransactionDto>>

    @GET("api/billing/payouts")
    suspend fun getPayouts(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 50
    ): Response<List<PayoutDto>>

    @POST("api/billing/payouts")
    suspend fun requestPayout(@Body request: PayoutRequest): Response<PayoutResponse>

    @GET("api/billing/socso-contributions")
    suspend fun getSocsoContributions(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 50,
        @Query("year") year: Int? = null
    ): Response<SocsoContributionsResponse>
}
