package com.gighala.app.ui.wallet

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.util.toMyr

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WalletScreen(
    contentPadding: PaddingValues,
    onMenuClick: () -> Unit = {},
    viewModel: WalletViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Wallet") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, contentDescription = "Menu")
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::loadWallet) {
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
        when {
            uiState.isLoading -> {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(innerPadding),
                    contentAlignment = Alignment.Center
                ) { CircularProgressIndicator() }
            }
            uiState.error != null -> {
                Box(
                    Modifier
                        .fillMaxSize()
                        .padding(innerPadding),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(uiState.error!!, color = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.height(12.dp))
                        Button(onClick = viewModel::loadWallet) { Text("Retry") }
                    }
                }
            }
            else -> {
                val w = uiState.wallet
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(top = innerPadding.calculateTopPadding())
                        .padding(bottom = contentPadding.calculateBottomPadding())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Main balance card
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary)
                    ) {
                        Column(
                            modifier = Modifier.padding(24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(
                                Icons.Filled.AccountBalanceWallet,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onPrimary,
                                modifier = Modifier.size(40.dp)
                            )
                            Spacer(Modifier.height(8.dp))
                            Text(
                                "Available Balance",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
                            )
                            Text(
                                (w?.availableBalance ?: 0.0).toMyr(),
                                style = MaterialTheme.typography.displaySmall,
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                        }
                    }

                    // Secondary stats
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        WalletStatCard(
                            label = "Total Earned",
                            value = (w?.totalEarned ?: 0.0).toMyr(),
                            icon = Icons.Filled.TrendingUp,
                            modifier = Modifier.weight(1f)
                        )
                        WalletStatCard(
                            label = "Total Spent",
                            value = (w?.totalSpent ?: 0.0).toMyr(),
                            icon = Icons.Filled.TrendingDown,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        WalletStatCard(
                            label = "Balance",
                            value = (w?.balance ?: 0.0).toMyr(),
                            icon = Icons.Filled.Wallet,
                            modifier = Modifier.weight(1f)
                        )
                        WalletStatCard(
                            label = "On Hold",
                            value = (w?.heldBalance ?: 0.0).toMyr(),
                            icon = Icons.Filled.HourglassEmpty,
                            modifier = Modifier.weight(1f)
                        )
                    }

                    // Info note
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Icon(
                                Icons.Filled.Info,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(20.dp)
                            )
                            Text(
                                "Funds are released 3 business days after gig completion. " +
                                "Held balance is escrowed for active gigs.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WalletStatCard(
    label: String,
    value: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Icon(icon, null, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(6.dp))
            Text(value, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
