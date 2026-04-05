package com.gighala.app.ui.workers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.WorkerUpdateDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

// Categories matching the desktop's MAIN_CATEGORY_SLUGS with display names
val WORKER_CATEGORIES = listOf(
    null to "All",
    // IDs are resolved at runtime from the response; we track by name filter instead
)

data class CategoryFilter(val id: Int?, val name: String)

val DAYS_OPTIONS = listOf(30 to "30 Days", 7 to "7 Days", 1 to "Today")

data class WorkerUpdatesUiState(
    val updates: List<WorkerUpdateDto> = emptyList(),
    val total: Int = 0,
    val isLoading: Boolean = true,
    val error: String? = null,
    val selectedDays: Int = 30,
    val selectedCategoryId: Int? = null,
    val selectedCategoryName: String = "All",
    val availableCategories: List<CategoryFilter> = listOf(CategoryFilter(null, "All")),
    val page: Int = 1,
    val hasMore: Boolean = false
)

@HiltViewModel
class WorkerUpdatesViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(WorkerUpdatesUiState())
    val uiState: StateFlow<WorkerUpdatesUiState> = _uiState.asStateFlow()

    init { load() }

    fun load(reset: Boolean = true) {
        val s = _uiState.value
        val page = if (reset) 1 else s.page + 1
        viewModelScope.launch {
            if (reset) _uiState.value = s.copy(isLoading = true, error = null)
            try {
                val resp = api.getWorkerUpdates(
                    days = s.selectedDays,
                    categoryId = s.selectedCategoryId,
                    page = page
                )
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    val newUpdates = if (reset) body.updates else s.updates + body.updates

                    // Build category list from results on first load
                    val categories = if (reset && page == 1) {
                        val cats = body.updates
                            .groupBy { it.categoryId }
                            .map { (id, items) -> CategoryFilter(id, items.first().categoryName) }
                            .sortedBy { it.name }
                        listOf(CategoryFilter(null, "All")) + cats
                    } else s.availableCategories

                    _uiState.value = _uiState.value.copy(
                        updates = newUpdates,
                        total = body.total,
                        isLoading = false,
                        page = body.page,
                        hasMore = body.page < body.pages,
                        availableCategories = categories
                    )
                } else {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = "Failed to load updates")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message ?: "Network error")
            }
        }
    }

    fun selectDays(days: Int) {
        _uiState.value = _uiState.value.copy(selectedDays = days)
        load()
    }

    fun selectCategory(filter: CategoryFilter) {
        _uiState.value = _uiState.value.copy(
            selectedCategoryId = filter.id,
            selectedCategoryName = filter.name
        )
        load()
    }

    fun loadMore() {
        if (!_uiState.value.hasMore || _uiState.value.isLoading) return
        load(reset = false)
    }
}
