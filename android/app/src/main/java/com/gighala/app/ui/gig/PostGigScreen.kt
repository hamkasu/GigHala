package com.gighala.app.ui.gig

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

private val GIG_CATEGORIES = listOf(
    "Design", "Writing", "Video", "Web Development", "Mobile Development",
    "Tutoring", "Marketing", "Photography", "Translation", "Data Entry",
    "Accounting", "Legal", "Consulting", "Music", "Voice Over"
)

private val WORK_TYPES = listOf("remote" to "Remote", "on-site" to "On-Site", "hybrid" to "Hybrid")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PostGigScreen(
    onBack: () -> Unit,
    onSuccess: (Int) -> Unit,
    viewModel: GigViewModel = hiltViewModel()
) {
    val postState by viewModel.postState.collectAsState()

    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var category by remember { mutableStateOf(GIG_CATEGORIES.first()) }
    var budgetMin by remember { mutableStateOf("") }
    var budgetMax by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var workType by remember { mutableStateOf("remote") }
    var skills by remember { mutableStateOf("") }
    var categoryExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(postState.createdGigId) {
        postState.createdGigId?.let { id ->
            onSuccess(id)
            viewModel.clearPostState()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Post a Gig") },
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
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = title,
                onValueChange = { title = it },
                label = { Text("Gig Title *") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("Description *") },
                minLines = 4,
                maxLines = 10,
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                modifier = Modifier.fillMaxWidth()
            )

            // Category dropdown
            ExposedDropdownMenuBox(
                expanded = categoryExpanded,
                onExpandedChange = { categoryExpanded = it }
            ) {
                OutlinedTextField(
                    value = category,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Category *") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(categoryExpanded) },
                    modifier = Modifier.fillMaxWidth().menuAnchor()
                )
                ExposedDropdownMenu(
                    expanded = categoryExpanded,
                    onDismissRequest = { categoryExpanded = false }
                ) {
                    GIG_CATEGORIES.forEach { cat ->
                        DropdownMenuItem(
                            text = { Text(cat) },
                            onClick = { category = cat; categoryExpanded = false }
                        )
                    }
                }
            }

            // Budget range
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = budgetMin,
                    onValueChange = { budgetMin = it },
                    label = { Text("Budget Min (RM)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.weight(1f)
                )
                OutlinedTextField(
                    value = budgetMax,
                    onValueChange = { budgetMax = it },
                    label = { Text("Budget Max (RM)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.weight(1f)
                )
            }

            OutlinedTextField(
                value = location,
                onValueChange = { location = it },
                label = { Text("Location (optional)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            // Work type chips
            Text("Work Type", style = MaterialTheme.typography.labelLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                WORK_TYPES.forEach { (type, label) ->
                    FilterChip(
                        selected = workType == type,
                        onClick = { workType = type },
                        label = { Text(label) }
                    )
                }
            }

            OutlinedTextField(
                value = skills,
                onValueChange = { skills = it },
                label = { Text("Preferred Skills (comma-separated)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            postState.error?.let { error ->
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                    Text(error, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(12.dp))
                }
            }

            Button(
                onClick = {
                    viewModel.createGig(
                        title = title,
                        description = description,
                        category = category,
                        budgetMin = budgetMin.toDoubleOrNull(),
                        budgetMax = budgetMax.toDoubleOrNull(),
                        location = location.ifBlank { null },
                        workType = workType,
                        deadline = null,
                        preferredSkills = skills.ifBlank { null }
                    )
                },
                enabled = title.isNotBlank() && description.isNotBlank() && !postState.isLoading,
                modifier = Modifier.fillMaxWidth().height(50.dp)
            ) {
                if (postState.isLoading) CircularProgressIndicator(Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                else Text("Post Gig")
            }

            Spacer(Modifier.height(16.dp))
        }
    }
}
