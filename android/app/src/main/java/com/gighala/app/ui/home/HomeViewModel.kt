package com.gighala.app.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.models.GigDto
import com.gighala.app.data.repository.GigRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val gigs: List<GigDto> = emptyList(),
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val error: String? = null,
    val currentPage: Int = 1,
    val hasMore: Boolean = true,
    val selectedCategory: String? = null,
    val selectedWorkType: String? = null,
    val searchQuery: String = ""
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val gigRepository: GigRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private val _searchQuery = MutableStateFlow("")

    init {
        loadGigs(refresh = true)

        @OptIn(FlowPreview::class)
        viewModelScope.launch {
            _searchQuery
                .debounce(400)
                .distinctUntilChanged()
                .collect { query ->
                    if (query.isBlank()) loadGigs(refresh = true)
                    else searchGigs(query)
                }
        }
    }

    fun loadGigs(refresh: Boolean = false) {
        val page = if (refresh) 1 else _uiState.value.currentPage + 1
        if (!refresh && !_uiState.value.hasMore) return

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = refresh, isLoadingMore = !refresh, error = null) }
            gigRepository.getGigs(
                page = page,
                category = _uiState.value.selectedCategory,
                workType = _uiState.value.selectedWorkType
            ).onSuccess { gigs ->
                _uiState.update { state ->
                    state.copy(
                        gigs = if (refresh) gigs else state.gigs + gigs,
                        isLoading = false,
                        isLoadingMore = false,
                        currentPage = page,
                        hasMore = gigs.size >= 20
                    )
                }
            }.onFailure { error ->
                _uiState.update { it.copy(isLoading = false, isLoadingMore = false, error = error.message) }
            }
        }
    }

    fun onSearchQueryChange(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
        _searchQuery.value = query
    }

    fun setCategory(category: String?) {
        _uiState.update { it.copy(selectedCategory = category) }
        loadGigs(refresh = true)
    }

    fun setWorkType(workType: String?) {
        _uiState.update { it.copy(selectedWorkType = workType) }
        loadGigs(refresh = true)
    }

    private fun searchGigs(query: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            gigRepository.getGigs(category = _uiState.value.selectedCategory, search = query)
                .onSuccess { gigs ->
                    _uiState.update { it.copy(gigs = gigs, isLoading = false, hasMore = false) }
                }.onFailure { error ->
                    _uiState.update { it.copy(isLoading = false, error = error.message) }
                }
        }
    }
}
