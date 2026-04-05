package com.gighala.app.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.*
import androidx.navigation.compose.*
import com.gighala.app.ui.auth.AuthViewModel
import com.gighala.app.ui.auth.LoginScreen
import com.gighala.app.ui.auth.RegisterScreen
import com.gighala.app.ui.auth.SocialLoginScreen
import com.gighala.app.ui.dashboard.DashboardScreen
import com.gighala.app.ui.gig.GigDetailScreen
import com.gighala.app.ui.gig.PostGigScreen
import com.gighala.app.ui.home.HomeScreen
import com.gighala.app.ui.messages.ConversationScreen
import com.gighala.app.ui.messages.MessagesScreen
import com.gighala.app.ui.notifications.NotificationsScreen
import com.gighala.app.ui.profile.ProfileScreen
import kotlinx.coroutines.launch

sealed class Screen(val route: String) {
    object Login          : Screen("login")
    object Register       : Screen("register")
    object SocialLogin    : Screen("social_login/{provider}") {
        fun route(provider: String) = "social_login/$provider"
    }
    object Home           : Screen("home")
    object GigDetail      : Screen("gig/{gigId}") {
        fun route(gigId: Int) = "gig/$gigId"
    }
    object PostGig        : Screen("post_gig")
    object Dashboard      : Screen("dashboard")
    object Messages       : Screen("messages")
    object Conversation   : Screen("conversation/{conversationId}") {
        fun route(id: Int) = "conversation/$id"
    }
    object Notifications  : Screen("notifications")
    object Profile        : Screen("profile")
}

data class BottomNavItem(
    val screen: Screen,
    val icon: ImageVector,
    val label: String
)

val bottomNavItems = listOf(
    BottomNavItem(Screen.Home,          Icons.Filled.Search,         "Browse"),
    BottomNavItem(Screen.Dashboard,     Icons.Filled.Dashboard,      "Dashboard"),
    BottomNavItem(Screen.Messages,      Icons.Filled.Message,        "Messages"),
    BottomNavItem(Screen.Notifications, Icons.Filled.Notifications,  "Alerts"),
    BottomNavItem(Screen.Profile,       Icons.Filled.Person,         "Profile"),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppNavigation(authViewModel: AuthViewModel = hiltViewModel()) {
    val navController = rememberNavController()
    val authState by authViewModel.authState.collectAsState()
    val isAuthenticated = authState is com.gighala.app.data.repository.AuthState.Authenticated

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    val showBottomBar = isAuthenticated && currentRoute in bottomNavItems.map { it.screen.route }
    val showDrawer = isAuthenticated && currentRoute in bottomNavItems.map { it.screen.route }

    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    val openDrawer: () -> Unit = { scope.launch { drawerState.open() } }

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = showDrawer,
        drawerContent = {
            if (showDrawer) {
                GigHalaDrawerContent(
                    currentRoute = currentRoute,
                    onNavigate = { route ->
                        navController.navigate(route) {
                            popUpTo(navController.graph.startDestinationId) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onClose = { scope.launch { drawerState.close() } }
                )
            }
        }
    ) {
        Scaffold(
            bottomBar = {
                if (showBottomBar) {
                    NavigationBar {
                        bottomNavItems.forEach { item ->
                            NavigationBarItem(
                                icon = { Icon(item.icon, contentDescription = item.label) },
                                label = { Text(item.label) },
                                selected = currentRoute == item.screen.route,
                                onClick = {
                                    navController.navigate(item.screen.route) {
                                        popUpTo(navController.graph.startDestinationId) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            )
                        }
                    }
                }
            }
        ) { padding ->
            NavHost(
                navController = navController,
                startDestination = if (isAuthenticated) Screen.Home.route else Screen.Login.route
            ) {
                // Auth
                composable(Screen.Login.route) {
                    LoginScreen(
                        onLoginSuccess = { navController.navigate(Screen.Home.route) { popUpTo(Screen.Login.route) { inclusive = true } } },
                        onNavigateRegister = { navController.navigate(Screen.Register.route) },
                        onSocialLogin = { provider -> navController.navigate(Screen.SocialLogin.route(provider)) }
                    )
                }
                composable(Screen.Register.route) {
                    RegisterScreen(
                        onRegisterSuccess = { navController.navigate(Screen.Home.route) { popUpTo(Screen.Login.route) { inclusive = true } } },
                        onNavigateLogin = { navController.popBackStack() },
                        onSocialLogin = { provider -> navController.navigate(Screen.SocialLogin.route(provider)) }
                    )
                }
                composable(
                    Screen.SocialLogin.route,
                    arguments = listOf(navArgument("provider") { type = NavType.StringType })
                ) { backStack ->
                    SocialLoginScreen(
                        provider = backStack.arguments!!.getString("provider") ?: "google",
                        onSuccess = { navController.navigate(Screen.Home.route) { popUpTo(Screen.Login.route) { inclusive = true } } },
                        onBack = { navController.popBackStack() }
                    )
                }

                // Main
                composable(Screen.Home.route) {
                    HomeScreen(
                        contentPadding = padding,
                        onGigClick = { gigId -> navController.navigate(Screen.GigDetail.route(gigId)) },
                        onPostGigClick = { navController.navigate(Screen.PostGig.route) },
                        onMenuClick = openDrawer
                    )
                }
                composable(
                    Screen.GigDetail.route,
                    arguments = listOf(navArgument("gigId") { type = NavType.IntType })
                ) { backStack ->
                    GigDetailScreen(
                        gigId = backStack.arguments!!.getInt("gigId"),
                        onBack = { navController.popBackStack() },
                        onMessageClient = { convId -> navController.navigate(Screen.Conversation.route(convId)) }
                    )
                }
                composable(Screen.PostGig.route) {
                    PostGigScreen(
                        onBack = { navController.popBackStack() },
                        onSuccess = { navController.navigate(Screen.Dashboard.route) { popUpTo(Screen.PostGig.route) { inclusive = true } } }
                    )
                }
                composable(Screen.Dashboard.route) {
                    DashboardScreen(
                        contentPadding = padding,
                        onGigClick = { gigId -> navController.navigate(Screen.GigDetail.route(gigId)) },
                        onMenuClick = openDrawer
                    )
                }
                composable(Screen.Messages.route) {
                    MessagesScreen(
                        contentPadding = padding,
                        onConversationClick = { convId -> navController.navigate(Screen.Conversation.route(convId)) },
                        onMenuClick = openDrawer
                    )
                }
                composable(
                    Screen.Conversation.route,
                    arguments = listOf(navArgument("conversationId") { type = NavType.IntType })
                ) { backStack ->
                    ConversationScreen(
                        conversationId = backStack.arguments!!.getInt("conversationId"),
                        onBack = { navController.popBackStack() }
                    )
                }
                composable(Screen.Notifications.route) {
                    NotificationsScreen(
                        contentPadding = padding,
                        onMenuClick = openDrawer
                    )
                }
                composable(Screen.Profile.route) {
                    ProfileScreen(
                        contentPadding = padding,
                        onLogout = {
                            navController.navigate(Screen.Login.route) {
                                popUpTo(0) { inclusive = true }
                            }
                        },
                        onMenuClick = openDrawer
                    )
                }
            }
        }
    }
}
