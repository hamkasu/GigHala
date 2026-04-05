package com.gighala.app.ui.wallet

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.data.api.models.*
import com.gighala.app.util.toMyr

private val OrangeCard  = Color(0xFFE87D0D)
private val PurpleCard  = Color(0xFF7B2FBE)
private val BlueCard    = Color(0xFF2563EB)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WalletScreen(
    contentPadding: PaddingValues,
    onMenuClick: () -> Unit = {},
    viewModel: WalletViewModel = hiltViewModel()
) {
    val s by viewModel.uiState.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("Transactions", "Invoices", "Payouts", "SOCSO")

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Wallet & Billing") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, contentDescription = "Menu")
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::loadAll) {
                        Icon(Icons.Filled.Refresh, "Refresh", tint = MaterialTheme.colorScheme.onPrimary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        },
        floatingActionButton = {
            if (selectedTab == 2) { // Payouts tab
                ExtendedFloatingActionButton(
                    onClick = viewModel::showPayoutDialog,
                    icon = { Icon(Icons.Filled.Send, null) },
                    text = { Text("Request Payout") },
                    containerColor = MaterialTheme.colorScheme.primary
                )
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = innerPadding.calculateTopPadding())
                .padding(bottom = contentPadding.calculateBottomPadding())
        ) {
            // ── 5 balance cards ──────────────────────────────────────────
            if (s.isLoadingWallet) {
                Box(Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    BalanceCard(
                        label = "Available Balance",
                        sub = "Malaysian Ringgit",
                        value = (s.wallet?.availableBalance ?: 0.0).toMyr(),
                        bgColor = MaterialTheme.colorScheme.primary
                    )
                    BalanceCard(
                        label = "Total Earned",
                        sub = "All-time earnings",
                        value = (s.wallet?.totalEarned ?: 0.0).toMyr(),
                        bgColor = Color(0xFF16A34A) // darker green
                    )
                    BalanceCard(
                        label = "Held Balance",
                        sub = "Pending payouts",
                        value = (s.wallet?.heldBalance ?: 0.0).toMyr(),
                        bgColor = OrangeCard
                    )
                    BalanceCard(
                        label = "SOCSO Contributions",
                        sub = "Mandatory 1.25% deductions",
                        value = s.totalSocso.toMyr(),
                        bgColor = PurpleCard
                    )
                    BalanceCard(
                        label = "Total Spent",
                        sub = "All payments made",
                        value = (s.wallet?.totalSpent ?: 0.0).toMyr(),
                        bgColor = BlueCard
                    )
                }
            }

            // ── Tabs ─────────────────────────────────────────────────────
            TabRow(selectedTabIndex = selectedTab) {
                tabs.forEachIndexed { index, title ->
                    Tab(
                        selected = selectedTab == index,
                        onClick = { selectedTab = index },
                        text = { Text(title, style = MaterialTheme.typography.labelMedium) }
                    )
                }
            }

            // ── Tab content ───────────────────────────────────────────────
            when (selectedTab) {
                0 -> TransactionsTab(s, viewModel)
                1 -> InvoicesTab(s)
                2 -> PayoutsTab(s)
                3 -> SocsoTab(s)
            }
        }
    }

    // ── Payout dialog ────────────────────────────────────────────────────
    if (s.showPayoutDialog) {
        PayoutDialog(
            state = s,
            onAmountChange = viewModel::updatePayoutAmount,
            onBankChange = viewModel::updatePayoutBankName,
            onAccountNumChange = viewModel::updatePayoutAccountNumber,
            onAccountNameChange = viewModel::updatePayoutAccountName,
            onSubmit = viewModel::submitPayout,
            onDismiss = viewModel::dismissPayoutDialog
        )
    }

    // ── Success snackbar ─────────────────────────────────────────────────
    s.payoutSuccess?.let { msg ->
        LaunchedEffect(msg) {
            // consumed after showing; just clear after a moment
        }
    }
}

// ── Balance card ─────────────────────────────────────────────────────────────
@Composable
private fun BalanceCard(label: String, sub: String, value: String, bgColor: Color) {
    Card(
        modifier = Modifier.width(200.dp),
        colors = CardDefaults.cardColors(containerColor = bgColor)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(label, style = MaterialTheme.typography.bodySmall, color = Color.White.copy(alpha = 0.85f))
            Spacer(Modifier.height(4.dp))
            Text(value, style = MaterialTheme.typography.headlineSmall, color = Color.White, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(4.dp))
            Text(sub, style = MaterialTheme.typography.bodySmall, color = Color.White.copy(alpha = 0.7f))
        }
    }
}

// ── Transactions tab ─────────────────────────────────────────────────────────
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TransactionsTab(s: WalletUiState, viewModel: WalletViewModel) {
    val filterOptions = listOf("all" to "All Transactions", "received" to "Received", "sent" to "Sent")

    Column(modifier = Modifier.fillMaxSize()) {
        // Filter row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            filterOptions.forEach { (value, label) ->
                FilterChip(
                    selected = s.transactionTypeFilter == value,
                    onClick = { viewModel.setTransactionFilter(value) },
                    label = { Text(label, style = MaterialTheme.typography.labelSmall) }
                )
            }
        }

        if (s.isLoadingTransactions) {
            Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (s.transactions.isEmpty()) {
            EmptyState(Icons.Filled.SwapHoriz, "No Transactions Yet", "Your transaction history will appear here")
        } else {
            LazyColumn {
                items(s.transactions, key = { it.id }) { tx ->
                    TransactionItem(tx)
                    HorizontalDivider()
                }
            }
        }
    }
}

@Composable
private fun TransactionItem(tx: TransactionDto) {
    val isReceived = tx.type == "received"
    val amountColor = if (isReceived) Color(0xFF16A34A) else MaterialTheme.colorScheme.error
    val amountPrefix = if (isReceived) "+" else "-"
    val dateStr = (tx.transactionDate ?: tx.date)?.take(10) ?: ""

    ListItem(
        headlineContent = { Text(tx.gigTitle ?: "Transaction #${tx.id}", style = MaterialTheme.typography.titleSmall) },
        supportingContent = {
            Column {
                val counterpart = if (isReceived) tx.clientName else tx.freelancerName
                counterpart?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                if (tx.commission > 0) {
                    Text("Commission: ${tx.commission.toMyr()} · Net: ${tx.netAmount.toMyr()}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        },
        leadingContent = {
            Icon(
                if (isReceived) Icons.Filled.ArrowDownward else Icons.Filled.ArrowUpward,
                contentDescription = null,
                tint = amountColor
            )
        },
        trailingContent = {
            Column(horizontalAlignment = Alignment.End) {
                Text("$amountPrefix${tx.amount.toMyr()}", style = MaterialTheme.typography.titleSmall, color = amountColor, fontWeight = FontWeight.SemiBold)
                Text(dateStr, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                StatusBadge(tx.status)
            }
        }
    )
}

// ── Invoices tab ─────────────────────────────────────────────────────────────
@Composable
private fun InvoicesTab(s: WalletUiState) {
    if (s.isLoadingInvoices) {
        Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }
    if (s.invoices.isEmpty()) {
        EmptyState(Icons.Filled.Receipt, "No Invoices", "Invoices will appear here after gigs are completed")
        return
    }
    LazyColumn {
        items(s.invoices, key = { it.id }) { inv ->
            InvoiceItem(inv)
            HorizontalDivider()
        }
    }
}

@Composable
private fun InvoiceItem(inv: InvoiceDto) {
    val isFreelancer = inv.role == "freelancer"
    ListItem(
        headlineContent = { Text(inv.gigTitle, style = MaterialTheme.typography.titleSmall) },
        supportingContent = {
            Column {
                Text(inv.invoiceNumber, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                val counterpart = if (isFreelancer) inv.clientName else inv.freelancerName
                counterpart?.let { Text(if (isFreelancer) "From: $it" else "To: $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                if (inv.platformFee > 0) {
                    Text("Fee: ${inv.platformFee.toMyr()}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        },
        leadingContent = {
            Icon(Icons.Filled.Description, null, tint = MaterialTheme.colorScheme.primary)
        },
        trailingContent = {
            Column(horizontalAlignment = Alignment.End) {
                Text(inv.totalAmount.toMyr(), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
                Text((inv.issueDate ?: inv.createdAt).take(10), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                StatusBadge(inv.status)
            }
        }
    )
}

// ── Payouts tab ───────────────────────────────────────────────────────────────
@Composable
private fun PayoutsTab(s: WalletUiState) {
    if (s.isLoadingPayouts) {
        Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }
    if (s.payouts.isEmpty()) {
        EmptyState(Icons.Filled.AccountBalance, "No Payouts Yet", "Request your first payout using the button below")
        return
    }
    LazyColumn(contentPadding = PaddingValues(bottom = 80.dp)) {
        items(s.payouts, key = { it.id }) { payout ->
            PayoutItem(payout)
            HorizontalDivider()
        }
    }
}

@Composable
private fun PayoutItem(payout: PayoutDto) {
    ListItem(
        headlineContent = { Text(payout.payoutNumber, style = MaterialTheme.typography.titleSmall) },
        supportingContent = {
            Column {
                payout.bankName?.let { Text("$it · ****${payout.accountNumber?.takeLast(4) ?: ""}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                if (payout.fee > 0) {
                    Text("Fee: ${payout.fee.toMyr()} · Net: ${payout.netAmount.toMyr()}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                payout.failureReason?.let { Text("Reason: $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error) }
            }
        },
        leadingContent = {
            Icon(Icons.Filled.Send, null, tint = MaterialTheme.colorScheme.primary)
        },
        trailingContent = {
            Column(horizontalAlignment = Alignment.End) {
                Text(payout.amount.toMyr(), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
                Text(payout.requestedAt.take(10), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                StatusBadge(payout.status)
            }
        }
    )
}

// ── SOCSO tab ─────────────────────────────────────────────────────────────────
@Composable
private fun SocsoTab(s: WalletUiState) {
    if (s.isLoadingSocso) {
        Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LazyColumn {
        // Summary card
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                colors = CardDefaults.cardColors(containerColor = PurpleCard)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("SOCSO Contributions", style = MaterialTheme.typography.titleSmall, color = Color.White)
                    Text("Gig Workers (Social Protection) Act 2025 — 1.25% deduction", style = MaterialTheme.typography.bodySmall, color = Color.White.copy(alpha = 0.8f))
                    Spacer(Modifier.height(12.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        SocsoStat("Total SOCSO", s.socsoTotals.totalSocso.toMyr(), Color.White)
                        SocsoStat("Net Earnings", s.socsoTotals.totalNetEarnings.toMyr(), Color.White)
                        SocsoStat("Final Payout", s.socsoTotals.totalFinalPayout.toMyr(), Color.White)
                    }
                }
            }
        }

        if (s.socsoContributions.isEmpty()) {
            item {
                EmptyState(Icons.Filled.Shield, "No Contributions", "SOCSO deductions appear here after gig earnings")
            }
        } else {
            items(s.socsoContributions, key = { it.id }) { contrib ->
                SocsoItem(contrib)
                HorizontalDivider()
            }
        }
    }
}

@Composable
private fun SocsoStat(label: String, value: String, textColor: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleSmall, color = textColor, fontWeight = FontWeight.Bold)
        Text(label, style = MaterialTheme.typography.bodySmall, color = textColor.copy(alpha = 0.8f))
    }
}

@Composable
private fun SocsoItem(contrib: SocsoContributionDto) {
    ListItem(
        headlineContent = {
            Text(contrib.contributionMonth ?: "Contribution #${contrib.id}", style = MaterialTheme.typography.titleSmall)
        },
        supportingContent = {
            Column {
                Text("Gross: ${contrib.grossAmount.toMyr()} · Net: ${contrib.netEarnings.toMyr()}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Final payout: ${contrib.finalPayout.toMyr()}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        },
        leadingContent = {
            Icon(Icons.Filled.Shield, null, tint = PurpleCard)
        },
        trailingContent = {
            Column(horizontalAlignment = Alignment.End) {
                Text(contrib.socsoAmount.toMyr(), style = MaterialTheme.typography.titleSmall, color = PurpleCard, fontWeight = FontWeight.SemiBold)
                val remitted = if (contrib.remittedToSocso) "Remitted" else "Pending"
                StatusBadge(remitted)
            }
        }
    )
}

// ── Payout dialog ─────────────────────────────────────────────────────────────
@Composable
private fun PayoutDialog(
    state: WalletUiState,
    onAmountChange: (String) -> Unit,
    onBankChange: (String) -> Unit,
    onAccountNumChange: (String) -> Unit,
    onAccountNameChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit
) {
    val available = state.wallet?.availableBalance ?: 0.0
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Request Payout") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Available: ${available.toMyr()}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

                OutlinedTextField(
                    value = state.payoutAmount,
                    onValueChange = onAmountChange,
                    label = { Text("Amount (MYR)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = state.payoutBankName,
                    onValueChange = onBankChange,
                    label = { Text("Bank Name") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = state.payoutAccountNumber,
                    onValueChange = onAccountNumChange,
                    label = { Text("Account Number") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = state.payoutAccountName,
                    onValueChange = onAccountNameChange,
                    label = { Text("Account Holder Name") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                state.payoutError?.let {
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }

                Text("2% platform fee applies. Processed within 1 business day.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        },
        confirmButton = {
            val valid = state.payoutAmount.toDoubleOrNull() != null &&
                state.payoutAmount.toDoubleOrNull()!! > 0 &&
                state.payoutBankName.isNotBlank() &&
                state.payoutAccountNumber.isNotBlank() &&
                state.payoutAccountName.isNotBlank()
            Button(
                onClick = onSubmit,
                enabled = valid && !state.isSubmittingPayout
            ) {
                if (state.isSubmittingPayout) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                else Text("Submit")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

// ── Shared helpers ────────────────────────────────────────────────────────────
@Composable
private fun StatusBadge(status: String) {
    val (bgColor, textColor) = when (status.lowercase()) {
        "paid", "completed", "remitted"  -> Color(0xFF16A34A) to Color.White
        "pending"                         -> Color(0xFFD97706) to Color.White
        "failed", "rejected", "overdue"   -> MaterialTheme.colorScheme.error to MaterialTheme.colorScheme.onError
        else                              -> MaterialTheme.colorScheme.surfaceVariant to MaterialTheme.colorScheme.onSurfaceVariant
    }
    Surface(shape = MaterialTheme.shapes.small, color = bgColor) {
        Text(
            status.replaceFirstChar { it.uppercase() },
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
            style = MaterialTheme.typography.labelSmall,
            color = textColor
        )
    }
}

@Composable
private fun EmptyState(icon: ImageVector, title: String, sub: String) {
    Box(Modifier.fillMaxWidth().padding(64.dp), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(icon, null, Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(title, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(sub, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
