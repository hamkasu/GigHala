package com.gighala.app.ui.documents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.InvoiceDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DocumentsUiState(
    val invoices: List<InvoiceDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class DocumentsViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(DocumentsUiState(isLoading = true))
    val uiState: StateFlow<DocumentsUiState> = _uiState.asStateFlow()

    init {
        loadInvoices()
    }

    fun loadInvoices() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val response = api.getInvoices()
                if (response.isSuccessful) {
                    _uiState.value = DocumentsUiState(invoices = response.body() ?: emptyList())
                } else {
                    _uiState.value = DocumentsUiState(error = "Failed to load invoices")
                }
            } catch (e: Exception) {
                _uiState.value = DocumentsUiState(error = e.message ?: "Network error")
            }
        }
    }
}
