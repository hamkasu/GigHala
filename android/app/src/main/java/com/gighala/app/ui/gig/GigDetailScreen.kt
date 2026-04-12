package com.gighala.app.ui.gig

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.util.toMyr

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GigDetailScreen(
    gigId: Int,
    onBack: () -> Unit,
    onMessageClient: (Int) -> Unit,
    viewModel: GigViewModel = hiltViewModel()
) {
    val uiState by viewModel.detailState.collectAsState()
    var showApplySheet by remember { mutableStateOf(false) }

    LaunchedEffect(gigId) { viewModel.loadGig(gigId) }
    LaunchedEffect(uiState.applySuccess) {
        if (uiState.applySuccess) {
            showApplySheet = false
            viewModel.clearApplySuccess()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.gig?.title ?: "Gig Detail") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, "Back") }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        },
        bottomBar = {
            uiState.gig?.let { gig ->
                if (gig.status == "open" && !gig.userHasApplied) {
                    Surface(shadowElevation = 8.dp) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(16.dp),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            OutlinedButton(
                                onClick = { /* message client */ },
                                modifier = Modifier.weight(1f)
                            ) {
                                Icon(Icons.Filled.Message, null, Modifier.size(16.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("Message")
                            }
                            Button(
                                onClick = { showApplySheet = true },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Apply Now")
                            }
                        }
                    }
                } else if (gig.userHasApplied) {
                    Surface(shadowElevation = 8.dp) {
                        Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.CheckCircle, null, tint = MaterialTheme.colorScheme.primary)
                                Spacer(Modifier.width(8.dp))
                                Text("Application Submitted", style = MaterialTheme.typography.labelLarge)
                            }
                        }
                    }
                }
            }
        }
    ) { padding ->
        when {
            uiState.isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            uiState.error != null -> Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
                Text(uiState.error!!, color = MaterialTheme.colorScheme.error)
            }
            uiState.gig != null -> {
                val gig = uiState.gig!!
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(padding)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Status + Syariah Compliant badge
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        AssistChip(onClick = {}, label = { Text(gig.status.replaceFirstChar { it.uppercase() }) })
                        if (gig.isHalalVerified) {
                            AssistChip(
                                onClick = {},
                                label = { Text("Syariah Compliant Verified") },
                                leadingIcon = { Icon(Icons.Filled.CheckCircle, null, Modifier.size(16.dp)) }
                            )
                        }
                        AssistChip(onClick = {}, label = { Text(gig.category) })
                    }

                    // Budget
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text("Budget", style = MaterialTheme.typography.labelMedium)
                                val budgetText = when {
                                    gig.budgetMin != null && gig.budgetMax != null ->
                                        "${gig.budgetMin.toMyr()} – ${gig.budgetMax.toMyr()}"
                                    gig.budgetMin != null -> "From ${gig.budgetMin.toMyr()}"
                                    gig.budgetMax != null -> "Up to ${gig.budgetMax.toMyr()}"
                                    else -> "Negotiable"
                                }
                                Text(budgetText, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
                            }
                            gig.deadline?.let { dl ->
                                Column(horizontalAlignment = Alignment.End) {
                                    Text("Deadline", style = MaterialTheme.typography.labelMedium)
                                    Text(dl, style = MaterialTheme.typography.titleMedium)
                                }
                            }
                        }
                    }

                    // Description
                    Text("Description", style = MaterialTheme.typography.titleMedium)
                    Text(gig.description, style = MaterialTheme.typography.bodyMedium)

                    // Skills
                    gig.preferredSkills?.takeIf { it.isNotBlank() }?.let { skills ->
                        Text("Preferred Skills", style = MaterialTheme.typography.titleMedium)
                        Text(skills, style = MaterialTheme.typography.bodyMedium)
                    }

                    // Location / work type
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        gig.location?.let { loc ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.Place, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Spacer(Modifier.width(4.dp))
                                Text(loc, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                        gig.workType?.let { wt ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Filled.Work, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                Spacer(Modifier.width(4.dp))
                                Text(wt.replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }

                    // Client info
                    gig.client?.let { client ->
                        HorizontalDivider()
                        Text("Posted By", style = MaterialTheme.typography.titleMedium)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Icon(Icons.Filled.AccountCircle, null, Modifier.size(40.dp))
                            Column {
                                Text(client.fullName ?: client.username, style = MaterialTheme.typography.titleMedium)
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Filled.Star, null, Modifier.size(14.dp), tint = MaterialTheme.colorScheme.secondary)
                                    Text(" ${client.rating}", style = MaterialTheme.typography.bodySmall)
                                    if (client.isVerified) {
                                        Spacer(Modifier.width(8.dp))
                                        Icon(Icons.Filled.Verified, null, Modifier.size(14.dp), tint = MaterialTheme.colorScheme.primary)
                                        Text(" Verified", style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }

                    Spacer(Modifier.height(80.dp))
                }
            }
        }
    }

    // Apply bottom sheet
    if (showApplySheet) {
        ApplyBottomSheet(
            gigId = gigId,
            isLoading = uiState.isApplying,
            error = uiState.applyError,
            requiresCoverLetter = uiState.gig?.coverLetterRequired == true,
            onDismiss = { showApplySheet = false },
            onSubmit = { proposal, rate -> viewModel.applyToGig(gigId, proposal, rate) }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ApplyBottomSheet(
    gigId: Int,
    isLoading: Boolean,
    error: String?,
    requiresCoverLetter: Boolean,
    onDismiss: () -> Unit,
    onSubmit: (String, Double?) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var proposal by remember { mutableStateOf("") }
    var rateText by remember { mutableStateOf("") }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp).padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Submit Application", style = MaterialTheme.typography.titleLarge)

            OutlinedTextField(
                value = proposal,
                onValueChange = { proposal = it },
                label = { Text(if (requiresCoverLetter) "Cover Letter (required)" else "Proposal / Introduction") },
                minLines = 4,
                maxLines = 8,
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = rateText,
                onValueChange = { rateText = it },
                label = { Text("Your Rate (RM) — optional") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }

            Button(
                onClick = { onSubmit(proposal, rateText.toDoubleOrNull()) },
                enabled = proposal.isNotBlank() && !isLoading,
                modifier = Modifier.fillMaxWidth().height(50.dp)
            ) {
                if (isLoading) CircularProgressIndicator(Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                else Text("Submit Application")
            }
        }
    }
}
