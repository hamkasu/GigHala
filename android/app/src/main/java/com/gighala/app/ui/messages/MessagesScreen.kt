package com.gighala.app.ui.messages

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.data.api.models.ConversationDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MessagesScreen(
    contentPadding: PaddingValues,
    onConversationClick: (Int) -> Unit,
    onMenuClick: () -> Unit = {},
    viewModel: MessagesViewModel = hiltViewModel()
) {
    val uiState by viewModel.messagesState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Messages") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, contentDescription = "Menu")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { innerPadding ->
        LazyColumn(
            contentPadding = PaddingValues(
                top = innerPadding.calculateTopPadding(),
                bottom = contentPadding.calculateBottomPadding() + 16.dp
            )
        ) {
            if (uiState.isLoading) {
                item {
                    Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (uiState.conversations.isEmpty()) {
                item {
                    Box(Modifier.fillMaxWidth().padding(48.dp), contentAlignment = Alignment.Center) {
                        Text("No messages yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                items(uiState.conversations, key = { it.id }) { conversation ->
                    ConversationItem(conversation, onClick = { onConversationClick(conversation.id) })
                    HorizontalDivider()
                }
            }
        }
    }
}

@Composable
private fun ConversationItem(conversation: ConversationDto, onClick: () -> Unit) {
    ListItem(
        headlineContent = {
            Text(conversation.otherUser.fullName ?: conversation.otherUser.username, style = MaterialTheme.typography.titleMedium)
        },
        supportingContent = {
            Column {
                conversation.gigTitle?.let { title ->
                    Text(title, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                conversation.lastMessage?.let { msg ->
                    Text(msg, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        },
        leadingContent = {
            Box {
                Icon(Icons.Filled.AccountCircle, null, Modifier.size(48.dp))
                if (conversation.unreadCount > 0) {
                    Badge(modifier = Modifier.align(Alignment.TopEnd)) {
                        Text("${conversation.unreadCount}")
                    }
                }
            }
        },
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        colors = ListItemDefaults.colors(containerColor = if (conversation.unreadCount > 0) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface),
        trailingContent = {
            conversation.lastMessageTime?.let { time ->
                Text(time.take(10), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    )
}
