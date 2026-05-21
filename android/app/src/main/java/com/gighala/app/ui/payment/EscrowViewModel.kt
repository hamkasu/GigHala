package com.gighala.app.ui.payment

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.CheckoutSessionRequest
import com.gighala.app.data.api.models.EscrowDto
import com.gighala.app.data.api.models.FeeBreakdown
import com.gighala.app.data.api.models.PaymentResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class EscrowUiState(
    val isLoading: Boolean = false,
    val escrow: EscrowDto? = null,
    val feeBreakdown: FeeBreakdown? = null,
    val checkoutUrl: String? = null,
    val paymentResult: PaymentResult? = null,
    val error: String? = null
)

@HiltViewModel
class EscrowViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(EscrowUiState())
    val uiState: StateFlow<EscrowUiState> = _uiState.asStateFlow()

    private val _openBrowser = MutableSharedFlow<String>()
    val openBrowser: SharedFlow<String> = _openBrowser.asSharedFlow()

    fun loadEscrow(gigId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            runCatching { api.getEscrow(gigId) }
                .onSuccess { response ->
                    if (response.isSuccessful) {
                        _uiState.value = _uiState.value.copy(isLoading = false, escrow = response.body())
                    } else {
                        // 404 means no escrow yet — that's fine, user can create one
                        _uiState.value = _uiState.value.copy(isLoading = false)
                    }
                }
                .onFailure { _uiState.value = _uiState.value.copy(isLoading = false, error = it.message) }
        }
    }

    fun initiatePayment(gigId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            runCatching { api.createCheckoutSession(CheckoutSessionRequest(gigId = gigId, mobile = true)) }
                .onSuccess { response ->
                    val body = response.body()
                    if (response.isSuccessful && body?.checkoutUrl != null) {
                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            feeBreakdown = body.feeBreakdown,
                            checkoutUrl = body.checkoutUrl
                        )
                        _openBrowser.emit(body.checkoutUrl)
                    } else {
                        val msg = body?.error ?: "Failed to create payment session"
                        _uiState.value = _uiState.value.copy(isLoading = false, error = msg)
                    }
                }
                .onFailure { _uiState.value = _uiState.value.copy(isLoading = false, error = it.message) }
        }
    }

    fun onPaymentResult(result: PaymentResult) {
        _uiState.value = _uiState.value.copy(paymentResult = result, isLoading = false)
        if (result.status == "success") {
            result.gigId?.let { loadEscrow(it) }
        }
    }

    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
}
