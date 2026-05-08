package com.gighala.app.ui.gig

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.models.ApplicationDto
import com.gighala.app.data.api.models.ApplyGigRequest
import com.gighala.app.data.api.models.CreateGigRequest
import com.gighala.app.data.api.models.CreateGigResponse
import com.gighala.app.data.api.models.GigDto
import com.gighala.app.data.repository.GigRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class GigDetailUiState(
    val gig: GigDto? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
    val applySuccess: Boolean = false,
    val applyError: String? = null,
    val isApplying: Boolean = false,
    val applications: List<ApplicationDto> = emptyList(),
    val shortlistingId: Int? = null
)

data class PostGigUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val createdGigId: Int? = null
)

@HiltViewModel
class GigViewModel @Inject constructor(
    private val gigRepository: GigRepository
) : ViewModel() {

    private val _detailState = MutableStateFlow(GigDetailUiState())
    val detailState: StateFlow<GigDetailUiState> = _detailState.asStateFlow()

    private val _postState = MutableStateFlow(PostGigUiState())
    val postState: StateFlow<PostGigUiState> = _postState.asStateFlow()

    fun loadGig(gigId: Int) {
        viewModelScope.launch {
            _detailState.update { it.copy(isLoading = true, error = null) }
            gigRepository.getGig(gigId)
                .onSuccess { gig ->
                    _detailState.update { it.copy(gig = gig, isLoading = false) }
                    if (gig.isOwnGig) loadApplications(gigId)
                }
                .onFailure { e -> _detailState.update { it.copy(isLoading = false, error = e.message) } }
        }
    }

    fun loadApplications(gigId: Int) {
        viewModelScope.launch {
            gigRepository.getApplications(gigId)
                .onSuccess { apps -> _detailState.update { it.copy(applications = apps) } }
        }
    }

    fun shortlistApplication(applicationId: Int) {
        viewModelScope.launch {
            _detailState.update { it.copy(shortlistingId = applicationId) }
            gigRepository.shortlistApplication(applicationId)
                .onSuccess { response ->
                    _detailState.update { state ->
                        state.copy(
                            shortlistingId = null,
                            applications = state.applications.map { app ->
                                if (app.id == applicationId) app.copy(isShortlisted = response.isShortlisted) else app
                            }
                        )
                    }
                }
                .onFailure { _detailState.update { it.copy(shortlistingId = null) } }
        }
    }

    fun applyToGig(gigId: Int, proposalText: String, appliedRate: Double?) {
        viewModelScope.launch {
            _detailState.update { it.copy(isApplying = true, applyError = null) }
            gigRepository.applyToGig(gigId, ApplyGigRequest(proposalText, appliedRate))
                .onSuccess { _detailState.update { it.copy(isApplying = false, applySuccess = true) } }
                .onFailure { e -> _detailState.update { it.copy(isApplying = false, applyError = e.message) } }
        }
    }

    fun createGig(
        title: String,
        description: String,
        category: String,
        budgetMin: Double?,
        budgetMax: Double?,
        location: String?,
        workType: String,
        deadline: String?,
        preferredSkills: String?
    ) {
        viewModelScope.launch {
            _postState.update { it.copy(isLoading = true, error = null) }
            gigRepository.createGig(
                CreateGigRequest(
                    title = title.trim(),
                    description = description.trim(),
                    category = category,
                    budgetMin = budgetMin,
                    budgetMax = budgetMax,
                    location = location?.trim(),
                    workType = workType,
                    deadline = deadline,
                    preferredSkills = preferredSkills?.trim()
                )
            ).onSuccess { response ->
                _postState.update { it.copy(isLoading = false, createdGigId = response.gigId) }
            }.onFailure { e ->
                _postState.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun clearApplySuccess() { _detailState.update { it.copy(applySuccess = false) } }
    fun clearPostState() { _postState.value = PostGigUiState() }
}
