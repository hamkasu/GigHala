package com.gighala.app.ui.documents

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.data.api.models.InvoiceDto
import com.gighala.app.util.toMyr

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DocumentsScreen(
    contentPadding: PaddingValues,
    onMenuClick: () -> Unit = {},
    viewModel: DocumentsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Documents") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, contentDescription = "Menu")
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::loadInvoices) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Refresh", tint = MaterialTheme.colorScheme.onPrimary)
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
            when {
                uiState.isLoading -> item {
                    Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
                uiState.error != null -> item {
                    Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(uiState.error!!, color = MaterialTheme.colorScheme.error)
                            Spacer(Modifier.height(12.dp))
                            Button(onClick = viewModel::loadInvoices) { Text("Retry") }
                        }
                    }
                }
                uiState.invoices.isEmpty() -> item {
                    Box(Modifier.fillMaxWidth().padding(64.dp), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                Icons.Filled.Description,
                                null,
                                Modifier.size(48.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(Modifier.height(8.dp))
                            Text("No invoices yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
                else -> {
                    item {
                        Text(
                            "Invoices",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)
                        )
                    }
                    items(uiState.invoices, key = { it.id }) { invoice ->
                        InvoiceItem(invoice)
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}

@Composable
private fun InvoiceItem(invoice: InvoiceDto) {
    val statusColor = when (invoice.status.lowercase()) {
        "paid" -> MaterialTheme.colorScheme.primary
        "pending" -> MaterialTheme.colorScheme.tertiary
        "overdue" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    ListItem(
        headlineContent = {
            Text(invoice.gigTitle, style = MaterialTheme.typography.titleSmall)
        },
        supportingContent = {
            Column {
                Text(
                    invoice.invoiceNumber,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Surface(
                        shape = MaterialTheme.shapes.small,
                        color = statusColor.copy(alpha = 0.12f)
                    ) {
                        Text(
                            invoice.status.replaceFirstChar { it.uppercase() },
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = statusColor
                        )
                    }
                    Text(
                        invoice.role.replaceFirstChar { it.uppercase() },
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        },
        leadingContent = {
            Icon(
                Icons.Filled.Receipt,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary
            )
        },
        trailingContent = {
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    invoice.totalAmount.toMyr(),
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    invoice.createdAt.take(10),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    )
}
