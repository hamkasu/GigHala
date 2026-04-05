package com.gighala.app.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.data.api.models.GigDto
import com.gighala.app.util.toMyr

private val CATEGORIES = listOf(
    "All", "Design", "Writing", "Video", "Web Development", "Mobile",
    "Tutoring", "Marketing", "Photography", "Translation", "Data Entry"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    contentPadding: PaddingValues,
    onGigClick: (Int) -> Unit,
    onPostGigClick: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()

    // Load more when near end
    val shouldLoadMore by remember {
        derivedStateOf {
            val lastVisibleIndex = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
            lastVisibleIndex >= uiState.gigs.size - 5 && !uiState.isLoadingMore && uiState.hasMore
        }
    }
    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore && uiState.searchQuery.isBlank()) viewModel.loadGigs()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    SearchBar(
                        query = uiState.searchQuery,
                        onQueryChange = viewModel::onSearchQueryChange,
                        onSearch = {},
                        active = false,
                        onActiveChange = {},
                        placeholder = { Text("Search gigs…") },
                        modifier = Modifier.fillMaxWidth().padding(end = 8.dp)
                    ) {}
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onPostGigClick,
                icon = { Icon(Icons.Filled.Add, null) },
                text = { Text("Post Gig") },
                containerColor = MaterialTheme.colorScheme.primary
            )
        }
    ) { innerPadding ->
        LazyColumn(
            state = listState,
            contentPadding = PaddingValues(
                top = innerPadding.calculateTopPadding() + 8.dp,
                bottom = contentPadding.calculateBottomPadding() + 80.dp,
                start = 16.dp,
                end = 16.dp
            ),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Category filter chips
            item {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(CATEGORIES) { category ->
                        val selected = when {
                            category == "All" -> uiState.selectedCategory == null
                            else -> uiState.selectedCategory == category
                        }
                        FilterChip(
                            selected = selected,
                            onClick = { viewModel.setCategory(if (category == "All") null else category) },
                            label = { Text(category) }
                        )
                    }
                }
            }

            if (uiState.isLoading) {
                item {
                    Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (uiState.gigs.isEmpty()) {
                item {
                    Box(Modifier.fillMaxWidth().padding(48.dp), contentAlignment = Alignment.Center) {
                        Text("No gigs found", style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                items(uiState.gigs, key = { it.id }) { gig ->
                    GigCard(gig = gig, onClick = { onGigClick(gig.id) })
                }
                if (uiState.isLoadingMore) {
                    item {
                        Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(Modifier.size(24.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun GigCard(gig: GigDto, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        gig.title,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(Modifier.height(4.dp))
                    AssistChip(
                        onClick = {},
                        label = { Text(gig.category, style = MaterialTheme.typography.bodySmall) }
                    )
                }
                if (gig.isHalalVerified) {
                    Icon(
                        Icons.Filled.CheckCircle,
                        contentDescription = "Halal Verified",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(
                gig.description,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Budget
                val budgetText = when {
                    gig.budgetMin != null && gig.budgetMax != null ->
                        "${gig.budgetMin.toMyr()} – ${gig.budgetMax.toMyr()}"
                    gig.budgetMin != null -> "From ${gig.budgetMin.toMyr()}"
                    gig.budgetMax != null -> "Up to ${gig.budgetMax.toMyr()}"
                    else -> "Negotiable"
                }
                Text(budgetText, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)

                // Location / work type
                gig.location?.let { loc ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Place, null, Modifier.size(14.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.width(2.dp))
                        Text(loc, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}
