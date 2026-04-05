package com.gighala.app.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.models.BillingStatsResponse
import com.gighala.app.data.api.models.GigDto
import com.gighala.app.data.repository.GigRepository
import com.gighala.app.data.repository.MessageRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val stats: BillingStatsResponse? = null,
    val myGigs: List<GigDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val gigRepository: GigRepository,
    private val messageRepository: MessageRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init { loadDashboard() }

    fun loadDashboard() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            // Load billing stats and gigs concurrently
            val statsResult = runCatching { messageRepository.getBillingStats() }
            val gigsResult = gigRepository.getGigs(page = 1)

            _uiState.update { state ->
                state.copy(
                    isLoading = false,
                    stats = statsResult.getOrNull()?.getOrNull(),
                    myGigs = gigsResult.getOrNull()?.gigs ?: state.myGigs,
                    error = gigsResult.exceptionOrNull()?.message
                )
            }
        }
    }
}
