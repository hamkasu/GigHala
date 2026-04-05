package com.gighala.app.ui.workers

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.gighala.app.BuildConfig
import com.gighala.app.data.api.models.WorkerUpdateDto
import com.gighala.app.util.toMyr

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkerUpdatesScreen(
    contentPadding: PaddingValues,
    onMenuClick: () -> Unit = {},
    onContactWorker: (workerId: Int) -> Unit = {},
    viewModel: WorkerUpdatesViewModel = hiltViewModel()
) {
    val s by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()

    // Load more when near bottom
    val shouldLoadMore by remember {
        derivedStateOf {
            val lastVisible = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
            lastVisible >= listState.layoutInfo.totalItemsCount - 4
        }
    }
    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore) viewModel.loadMore()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Worker Updates") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, "Menu")
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.load() }) {
                        Icon(Icons.Filled.Refresh, "Refresh", tint = MaterialTheme.colorScheme.onPrimary)
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
            state = listState,
            contentPadding = PaddingValues(
                top = innerPadding.calculateTopPadding(),
                bottom = contentPadding.calculateBottomPadding() + 16.dp
            )
        ) {
            // Hero banner
            item {
                WorkerUpdatesBanner(total = s.total, days = s.selectedDays)
            }

            // Category filters
            item {
                if (s.availableCategories.size > 1) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        s.availableCategories.forEach { cat ->
                            FilterChip(
                                selected = s.selectedCategoryId == cat.id,
                                onClick = { viewModel.selectCategory(cat) },
                                label = { Text(cat.name, style = MaterialTheme.typography.labelSmall) }
                            )
                        }
                    }
                }
            }

            // Time period filter + count
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        DAYS_OPTIONS.forEach { (days, label) ->
                            FilterChip(
                                selected = s.selectedDays == days,
                                onClick = { viewModel.selectDays(days) },
                                label = { Text(label, style = MaterialTheme.typography.labelSmall) }
                            )
                        }
                    }
                    if (s.total > 0) {
                        Text(
                            "${s.total} workers",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Loading / error / empty
            when {
                s.isLoading && s.updates.isEmpty() -> item {
                    Box(Modifier.fillMaxWidth().padding(64.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
                s.error != null && s.updates.isEmpty() -> item {
                    Box(Modifier.fillMaxWidth().padding(48.dp), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Icon(Icons.Filled.ErrorOutline, null, Modifier.size(40.dp), tint = MaterialTheme.colorScheme.error)
                            Text(s.error!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
                            Button(onClick = { viewModel.load() }) { Text("Retry") }
                        }
                    }
                }
                s.updates.isEmpty() && !s.isLoading -> item {
                    Box(Modifier.fillMaxWidth().padding(64.dp), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Icon(Icons.Filled.Update, null, Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("No worker updates", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Try a different time period or category", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
                else -> {
                    items(s.updates, key = { it.id }) { update ->
                        WorkerUpdateCard(update = update, onContact = { onContactWorker(update.worker.id) })
                        HorizontalDivider()
                    }
                    // Load more indicator
                    if (s.isLoading && s.updates.isNotEmpty()) {
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
}

// ── Hero banner ───────────────────────────────────────────────────────────────
@Composable
private fun WorkerUpdatesBanner(total: Int, days: Int) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.horizontalGradient(
                    listOf(MaterialTheme.colorScheme.primary, Color(0xFF16A34A))
                )
            )
            .padding(20.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Filled.Update, null, Modifier.size(24.dp), tint = Color.White)
                Text(
                    "Worker Updates",
                    style = MaterialTheme.typography.headlineSmall,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }
            Text(
                "Workers who have recently updated their skills and rates. Check the latest offers from our talent.",
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.9f)
            )
            if (total > 0) {
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = Color.White.copy(alpha = 0.2f)
                ) {
                    Text(
                        "• $total updated in the last $days days",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        style = MaterialTheme.typography.labelMedium,
                        color = Color.White
                    )
                }
            }
        }
    }
}

// ── Worker update card ────────────────────────────────────────────────────────
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun WorkerUpdateCard(update: WorkerUpdateDto, onContact: () -> Unit) {
    val w = update.worker
    val timeAgo = update.updatedAt?.let { formatTimeAgo(it) } ?: ""

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            // Category image area with UPDATED badge
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(80.dp)
                    .background(MaterialTheme.colorScheme.primaryContainer)
            ) {
                Text(
                    categoryEmoji(update.categorySlug),
                    modifier = Modifier.align(Alignment.Center),
                    style = MaterialTheme.typography.displaySmall
                )
                // UPDATED badge
                Surface(
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .padding(8.dp),
                    shape = MaterialTheme.shapes.small,
                    color = MaterialTheme.colorScheme.primary
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Icon(Icons.Filled.Update, null, Modifier.size(12.dp), tint = Color.White)
                        Text("UPDATED", style = MaterialTheme.typography.labelSmall, color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
                if (update.hasPremium) {
                    Surface(
                        modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
                        shape = MaterialTheme.shapes.small,
                        color = Color(0xFFD97706)
                    ) {
                        Text("PREMIUM", modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                            style = MaterialTheme.typography.labelSmall, color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                // Worker info row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Avatar
                    if (w.profilePhoto != null) {
                        AsyncImage(
                            model = "${BuildConfig.BASE_URL}${w.profilePhoto}",
                            contentDescription = null,
                            modifier = Modifier.size(40.dp).clip(CircleShape),
                            contentScale = ContentScale.Crop
                        )
                    } else {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .background(MaterialTheme.colorScheme.primary, CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                w.name.take(1).uppercase(),
                                style = MaterialTheme.typography.titleMedium,
                                color = Color.White,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(w.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            if (w.isVerified) {
                                Icon(Icons.Filled.Verified, null, Modifier.size(14.dp), tint = MaterialTheme.colorScheme.primary)
                            }
                        }
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (timeAgo.isNotEmpty()) {
                                Text(timeAgo, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            if (!w.location.isNullOrBlank()) {
                                Text("· ${w.location}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                    // Rating
                    if (w.rating > 0) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                            Icon(Icons.Filled.Star, null, Modifier.size(14.dp), tint = Color(0xFFD97706))
                            Text(String.format("%.1f", w.rating), style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }

                // Title
                Text(update.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)

                // Skills chips
                if (update.skills.isNotEmpty()) {
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        update.skills.take(5).forEach { skill ->
                            AssistChip(
                                onClick = {},
                                label = { Text(skill, style = MaterialTheme.typography.labelSmall) },
                                modifier = Modifier.height(26.dp)
                            )
                        }
                    }
                }

                // Price + Contact button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            if (update.priceType == "hourly") "HOURLY RATE" else "FIXED PRICE",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            update.startingPrice.toMyr(),
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Button(
                        onClick = onContact,
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                    ) {
                        Icon(Icons.Filled.Message, null, Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Contact")
                    }
                }
            }
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

private fun categoryEmoji(slug: String): String = when {
    slug.contains("design") || slug.contains("reka") -> "🎨"
    slug.contains("writing") || slug.contains("tulis") -> "✍️"
    slug.contains("video") -> "🎬"
    slug.contains("tutoring") || slug.contains("teaching") -> "📚"
    slug.contains("web") -> "🌐"
    slug.contains("marketing") -> "📣"
    slug.contains("music") -> "🎵"
    slug.contains("photo") -> "📷"
    slug.contains("finance") -> "💰"
    slug.contains("programming") || slug.contains("tech") -> "💻"
    slug.contains("data") -> "📊"
    slug.contains("delivery") -> "🚚"
    slug.contains("events") -> "🎉"
    slug.contains("care") -> "❤️"
    else -> "⚡"
}

private fun formatTimeAgo(isoTimestamp: String): String {
    return try {
        val sdf = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.getDefault())
        sdf.timeZone = java.util.TimeZone.getTimeZone("UTC")
        val date = sdf.parse(isoTimestamp.substringBefore(".").replace(" ", "T")) ?: return ""
        val diffMs = System.currentTimeMillis() - date.time
        val diffDays = diffMs / (1000 * 60 * 60 * 24)
        val diffHours = diffMs / (1000 * 60 * 60)
        when {
            diffDays >= 365 -> "${diffDays / 365}y ago"
            diffDays >= 30 -> "${diffDays / 30}mo ago"
            diffDays >= 1 -> "${diffDays}d ago"
            diffHours >= 1 -> "${diffHours}h ago"
            else -> "Just now"
        }
    } catch (_: Exception) { "" }
}
