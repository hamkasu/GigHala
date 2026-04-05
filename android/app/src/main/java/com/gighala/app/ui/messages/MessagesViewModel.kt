package com.gighala.app.ui.messages

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.models.ConversationDetailResponse
import com.gighala.app.data.api.models.ConversationDto
import com.gighala.app.data.api.models.MessageDto
import com.gighala.app.data.repository.MessageRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MessagesUiState(
    val conversations: List<ConversationDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

data class ConversationUiState(
    val detail: ConversationDetailResponse? = null,
    val isLoading: Boolean = false,
    val isSending: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class MessagesViewModel @Inject constructor(
    private val messageRepository: MessageRepository
) : ViewModel() {

    private val _messagesState = MutableStateFlow(MessagesUiState())
    val messagesState: StateFlow<MessagesUiState> = _messagesState.asStateFlow()

    private val _conversationState = MutableStateFlow(ConversationUiState())
    val conversationState: StateFlow<ConversationUiState> = _conversationState.asStateFlow()

    private var pollingJob: kotlinx.coroutines.Job? = null

    init { loadConversations() }

    fun loadConversations() {
        viewModelScope.launch {
            _messagesState.update { it.copy(isLoading = true) }
            messageRepository.getConversations()
                .onSuccess { conversations -> _messagesState.update { it.copy(conversations = conversations, isLoading = false) } }
                .onFailure { e -> _messagesState.update { it.copy(isLoading = false, error = e.message) } }
        }
    }

    fun openConversation(id: Int) {
        viewModelScope.launch {
            _conversationState.update { it.copy(isLoading = true) }
            messageRepository.getConversation(id)
                .onSuccess { detail -> _conversationState.update { it.copy(detail = detail, isLoading = false) } }
                .onFailure { e -> _conversationState.update { it.copy(isLoading = false, error = e.message) } }
        }
        startPolling(id)
    }

    fun sendMessage(conversationId: Int, content: String) {
        viewModelScope.launch {
            _conversationState.update { it.copy(isSending = true) }
            messageRepository.sendMessage(conversationId, content)
                .onSuccess { response ->
                    response.message?.let { msg ->
                        _conversationState.update { state ->
                            val updated = state.detail?.messages?.toMutableList()?.also { it.add(msg) }
                            state.copy(
                                detail = state.detail?.copy(messages = updated ?: emptyList()),
                                isSending = false
                            )
                        }
                    }
                }
                .onFailure { _conversationState.update { it.copy(isSending = false) } }
        }
    }

    private fun startPolling(conversationId: Int) {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (true) {
                delay(5_000)
                val lastId = _conversationState.value.detail?.messages?.lastOrNull()?.id ?: 0
                messageRepository.pollMessages(conversationId, lastId).onSuccess { newMessages ->
                    if (newMessages.isNotEmpty()) {
                        _conversationState.update { state ->
                            val updated = (state.detail?.messages ?: emptyList()) + newMessages
                            state.copy(detail = state.detail?.copy(messages = updated))
                        }
                    }
                }
            }
        }
    }

    override fun onCleared() {
        pollingJob?.cancel()
        super.onCleared()
    }
}
