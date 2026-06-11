package com.gighala.app.ui.payment

import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.data.api.models.FeeBreakdown
import com.gighala.app.data.api.models.PaymentResult
import com.gighala.app.util.toMyr

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EscrowScreen(
    gigId: Int,
    gigTitle: String,
    gigAmount: Double,
    paymentResult: PaymentResult?,
    onBack: () -> Unit,
    onPaymentSuccess: () -> Unit,
    viewModel: EscrowViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(gigId) { viewModel.loadEscrow(gigId) }

    LaunchedEffect(paymentResult) {
        paymentResult?.let { viewModel.onPaymentResult(it) }
    }

    LaunchedEffect(Unit) {
        viewModel.openBrowser.collect { url ->
            runCatching {
                CustomTabsIntent.Builder()
                    .setShareState(CustomTabsIntent.SHARE_STATE_OFF)
                    .build()
                    .launchUrl(context, Uri.parse(url))
            }.onFailure {
                // Fallback to plain browser intent
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        }
    }

    LaunchedEffect(state.paymentResult) {
        if (state.paymentResult?.status == "success") onPaymentSuccess()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Fund Escrow") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, "Back") }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        when {
            state.isLoading -> Box(
                Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center
            ) { CircularProgressIndicator() }

            state.escrow?.status == "funded" -> FundedState(padding, gigTitle, state.escrow!!.amount)

            else -> PaymentForm(
                padding = padding,
                gigTitle = gigTitle,
                gigAmount = gigAmount,
                existingEscrow = state.escrow,
                error = state.error,
                onPay = { viewModel.initiatePayment(gigId) },
                onClearError = viewModel::clearError
            )
        }
    }
}

@Composable
private fun FundedState(padding: PaddingValues, gigTitle: String, amount: Double) {
    Box(
        Modifier.fillMaxSize().padding(padding).padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Icon(Icons.Filled.CheckCircle, null, Modifier.size(64.dp), tint = Color(0xFF22C55E))
            Text("Escrow Funded!", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "${amount.toMyr()} is held securely in escrow for\n\"$gigTitle\"",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                "Payment will be released to the freelancer once you approve their work.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun PaymentForm(
    padding: PaddingValues,
    gigTitle: String,
    gigAmount: Double,
    existingEscrow: com.gighala.app.data.api.models.EscrowDto?,
    error: String?,
    onPay: () -> Unit,
    onClearError: () -> Unit
) {
    Column(
        Modifier.fillMaxSize().padding(padding).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Gig title
        Text(gigTitle, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text("Fund the escrow to start work. Payment is held securely and released only when you approve the delivered work.",
            style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

        HorizontalDivider()

        // Fee breakdown from existing escrow or estimated from gig amount
        if (existingEscrow != null) {
            FeeRow("Gig amount", existingEscrow.amount.toMyr())
            FeeRow("Platform fee (2%)", existingEscrow.platformFee.toMyr())
            FeeRow("Worker receives", existingEscrow.netAmount.toMyr(), highlight = true)
        } else {
            val platformFee = gigAmount * 0.02
            FeeRow("Gig amount", gigAmount.toMyr())
            FeeRow("Platform fee (2%)", platformFee.toMyr())
            FeeRow("Worker receives", (gigAmount - platformFee).toMyr(), highlight = true)
            Text("Processing fee added at checkout.", style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        HorizontalDivider()

        // Error
        error?.let {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onErrorContainer, modifier = Modifier.weight(1f))
                    TextButton(onClick = onClearError) { Text("Dismiss") }
                }
            }
        }

        Spacer(Modifier.weight(1f))

        // Halal / security note
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(Icons.Filled.Lock, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Secure & Shariah-compliant payment via Stripe", style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        Button(
            onClick = onPay,
            modifier = Modifier.fillMaxWidth().height(52.dp)
        ) {
            Text("Pay with Card / Google Pay", style = MaterialTheme.typography.titleMedium)
        }
    }
}

@Composable
private fun FeeRow(label: String, value: String, highlight: Boolean = false) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodyMedium,
            color = if (highlight) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium,
            fontWeight = if (highlight) FontWeight.SemiBold else FontWeight.Normal,
            color = if (highlight) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)
    }
}
