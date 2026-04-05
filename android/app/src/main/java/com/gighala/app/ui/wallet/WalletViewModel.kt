package com.gighala.app.ui.wallet

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.WalletDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class WalletUiState(
    val wallet: WalletDto? = null,
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class WalletViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(WalletUiState(isLoading = true))
    val uiState: StateFlow<WalletUiState> = _uiState.asStateFlow()

    init {
        loadWallet()
    }

    fun loadWallet() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val response = api.getWallet()
                if (response.isSuccessful) {
                    _uiState.value = WalletUiState(wallet = response.body())
                } else {
                    _uiState.value = WalletUiState(error = "Failed to load wallet")
                }
            } catch (e: Exception) {
                _uiState.value = WalletUiState(error = e.message ?: "Network error")
            }
        }
    }
}
