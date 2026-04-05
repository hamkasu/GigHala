package com.gighala.app.ui.notifications

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DoneAll
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.data.api.models.NotificationDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsScreen(
    contentPadding: PaddingValues,
    onMenuClick: () -> Unit = {},
    viewModel: NotificationsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Notifications") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, contentDescription = "Menu")
                    }
                },
                actions = {
                    if (uiState.unreadCount > 0) {
                        IconButton(onClick = viewModel::markAllRead) {
                            Icon(Icons.Filled.DoneAll, "Mark all read")
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
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
            } else if (uiState.notifications.isEmpty()) {
                item {
                    Box(Modifier.fillMaxWidth().padding(64.dp), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Filled.Notifications, null, Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(Modifier.height(8.dp))
                            Text("No notifications", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            } else {
                items(uiState.notifications, key = { it.id }) { notification ->
                    NotificationItem(notification)
                    HorizontalDivider()
                }
            }
        }
    }
}

@Composable
private fun NotificationItem(notification: NotificationDto) {
    ListItem(
        headlineContent = { Text(notification.subject, style = MaterialTheme.typography.titleSmall) },
        supportingContent = { Text(notification.body, style = MaterialTheme.typography.bodySmall, maxLines = 2) },
        trailingContent = {
            Text(notification.createdAt.take(10), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        },
        colors = ListItemDefaults.colors(
            containerColor = if (!notification.isRead) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface
        )
    )
}
