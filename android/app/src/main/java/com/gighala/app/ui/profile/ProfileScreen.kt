package com.gighala.app.ui.profile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.gighala.app.BuildConfig

@Composable
fun ProfileScreen(
    contentPadding: PaddingValues,
    onLogout: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel()
) {
    val user by viewModel.user.collectAsState()
    var showLogoutDialog by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(contentPadding)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Spacer(Modifier.height(8.dp))

        // Avatar
        if (user?.profilePhoto != null) {
            AsyncImage(
                model = "${BuildConfig.BASE_URL}${user!!.profilePhoto}",
                contentDescription = "Profile photo",
                modifier = Modifier.size(96.dp).clip(CircleShape),
                contentScale = ContentScale.Crop
            )
        } else {
            Icon(Icons.Filled.AccountCircle, null, Modifier.size(96.dp), tint = MaterialTheme.colorScheme.primary)
        }

        // Name + username
        Text(user?.fullName ?: user?.username ?: "", style = MaterialTheme.typography.headlineMedium)
        Text("@${user?.username ?: ""}", style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)

        // Verification badges
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (user?.isVerified == true) {
                AssistChip(
                    onClick = {},
                    label = { Text("ID Verified") },
                    leadingIcon = { Icon(Icons.Filled.Verified, null, Modifier.size(16.dp)) }
                )
            }
            user?.userType?.let { type ->
                AssistChip(onClick = {}, label = { Text(type.replaceFirstChar { it.uppercase() }) })
            }
        }

        // Stats row
        user?.let { u ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    ProfileStat("Rating", String.format("%.1f", u.rating))
                    VerticalDivider(modifier = Modifier.height(40.dp))
                    ProfileStat("Completed", "${u.completedGigs}")
                    VerticalDivider(modifier = Modifier.height(40.dp))
                    ProfileStat("Reviews", "${u.reviewCount}")
                }
            }
        }

        // Info rows
        user?.bio?.takeIf { it.isNotBlank() }?.let { bio ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("About", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(4.dp))
                    Text(bio, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        user?.location?.takeIf { it.isNotBlank() }?.let { loc ->
            ListItem(
                headlineContent = { Text("Location") },
                supportingContent = { Text(loc) },
                leadingContent = { Icon(Icons.Filled.Place, null) }
            )
        }

        user?.skills?.takeIf { it.isNotBlank() }?.let { skills ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Skills", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(4.dp))
                    Text(skills, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        OutlinedButton(
            onClick = { showLogoutDialog = true },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
        ) {
            Icon(Icons.Filled.Logout, null, Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text("Log Out")
        }
    }

    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("Log Out") },
            text = { Text("Are you sure you want to log out?") },
            confirmButton = {
                TextButton(onClick = {
                    showLogoutDialog = false
                    viewModel.logout()
                    onLogout()
                }) { Text("Log Out", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutDialog = false }) { Text("Cancel") }
            }
        )
    }
}

@Composable
private fun ProfileStat(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
