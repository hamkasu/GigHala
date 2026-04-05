package com.gighala.app.ui.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class DrawerItem(
    val icon: ImageVector,
    val label: String,
    val route: String,
    val badge: String? = null
)

val drawerItems = listOf(
    DrawerItem(Icons.Filled.Home,          "Browse Gigs",    Screen.Home.route),
    DrawerItem(Icons.Filled.Message,       "Messages",       Screen.Messages.route),
    DrawerItem(Icons.Filled.Add,           "Post a Gig",     Screen.PostGig.route),
    DrawerItem(Icons.Filled.Dashboard,     "Dashboard",      Screen.Dashboard.route),
    DrawerItem(Icons.Filled.Notifications, "Notifications",  Screen.Notifications.route),
    DrawerItem(Icons.Filled.Person,        "Profile",        Screen.Profile.route),
    DrawerItem(Icons.Filled.AccountBalanceWallet, "Wallet", Screen.Wallet.route),
    DrawerItem(Icons.Filled.Description,   "Documents",      Screen.Documents.route),
    DrawerItem(Icons.Filled.Update,        "Worker Updates", Screen.WorkerUpdates.route),
    DrawerItem(Icons.Filled.Star,          "Fractional",     Screen.Home.route, badge = "Pro"),
    DrawerItem(Icons.Filled.FlashOn,       "Urgent Help",    Screen.Home.route, badge = "!"),
)

@Composable
fun GigHalaDrawerContent(
    currentRoute: String?,
    onNavigate: (String) -> Unit,
    onClose: () -> Unit
) {
    ModalDrawerSheet(
        modifier = Modifier.width(280.dp)
    ) {
        // Header
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.primary)
                .padding(24.dp)
        ) {
            Column {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .background(MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.2f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Filled.Lock,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(28.dp)
                    )
                }
                Spacer(Modifier.height(12.dp))
                Text(
                    "GigHala",
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    "Malaysia's Halal Gig Economy",
                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f),
                    fontSize = 12.sp
                )
            }
        }

        Spacer(Modifier.height(8.dp))

        drawerItems.forEach { item ->
            val selected = currentRoute == item.route && item.badge == null
            NavigationDrawerItem(
                icon = { Icon(item.icon, contentDescription = null) },
                label = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(item.label)
                        item.badge?.let { badge ->
                            Surface(
                                shape = MaterialTheme.shapes.small,
                                color = if (badge == "!") MaterialTheme.colorScheme.error
                                        else MaterialTheme.colorScheme.tertiary
                            ) {
                                Text(
                                    badge,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onTertiary
                                )
                            }
                        }
                    }
                },
                selected = selected,
                onClick = {
                    onNavigate(item.route)
                    onClose()
                },
                modifier = Modifier.padding(horizontal = 8.dp)
            )
        }

        Spacer(Modifier.weight(1f))
        HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp))
        Spacer(Modifier.height(8.dp))
        NavigationDrawerItem(
            icon = { Icon(Icons.Filled.Help, null) },
            label = { Text("Help & Support") },
            selected = false,
            onClick = onClose,
            modifier = Modifier.padding(horizontal = 8.dp)
        )
        Spacer(Modifier.height(16.dp))
    }
}
