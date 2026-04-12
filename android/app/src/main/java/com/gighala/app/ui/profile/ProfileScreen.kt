package com.gighala.app.ui.profile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.gighala.app.BuildConfig

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    contentPadding: PaddingValues,
    onLogout: () -> Unit,
    onMenuClick: () -> Unit = {},
    viewModel: ProfileViewModel = hiltViewModel()
) {
    val s by viewModel.uiState.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }
    var showLogoutDialog by remember { mutableStateOf(false) }

    val tabs = listOf(
        "Personal Info",
        "Skills",
        "Fractional",
        "Verification",
        "Security",
        "Payment"
    )

    // Show snackbar for save results
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(s.saveSuccess, s.saveError) {
        val msg = s.saveSuccess ?: s.saveError ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(msg)
        viewModel.clearMessages()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Account Settings") },
                navigationIcon = {
                    IconButton(onClick = onMenuClick) {
                        Icon(Icons.Filled.Menu, "Menu")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        if (s.isLoading) {
            Box(Modifier.fillMaxSize().padding(innerPadding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = innerPadding.calculateTopPadding())
                .padding(bottom = contentPadding.calculateBottomPadding())
        ) {
            // ── Profile header ────────────────────────────────────────────
            ProfileHeader(s, onLogoutClick = { showLogoutDialog = true })

            // ── Tab row ───────────────────────────────────────────────────
            ScrollableTabRow(
                selectedTabIndex = selectedTab,
                edgePadding = 16.dp
            ) {
                tabs.forEachIndexed { i, title ->
                    Tab(
                        selected = selectedTab == i,
                        onClick = { selectedTab = i },
                        text = {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(title, style = MaterialTheme.typography.labelMedium)
                                if (i == 2) Text("✨", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    )
                }
            }

            // ── Tab content ───────────────────────────────────────────────
            when (selectedTab) {
                0 -> PersonalInfoTab(s, viewModel)
                1 -> SkillsTab(s, viewModel)
                2 -> FractionalTab(s, viewModel)
                3 -> VerificationTab(s)
                4 -> SecurityTab(s, viewModel)
                5 -> PaymentTab(s, viewModel)
            }
        }
    }

    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("Log Out") },
            text = { Text("Are you sure you want to log out?") },
            confirmButton = {
                TextButton(onClick = { showLogoutDialog = false; viewModel.logout(); onLogout() }) {
                    Text("Log Out", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { showLogoutDialog = false }) { Text("Cancel") } }
        )
    }
}

// ── Profile header ────────────────────────────────────────────────────────────
@Composable
private fun ProfileHeader(s: ProfileUiState, onLogoutClick: () -> Unit) {
    val p = s.profile
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // Avatar
        if (p?.profilePhoto != null) {
            AsyncImage(
                model = "${BuildConfig.BASE_URL}${p.profilePhoto}",
                contentDescription = "Profile photo",
                modifier = Modifier.size(80.dp).clip(CircleShape),
                contentScale = ContentScale.Crop
            )
        } else {
            Icon(Icons.Filled.AccountCircle, null, Modifier.size(80.dp), tint = MaterialTheme.colorScheme.primary)
        }

        Text(p?.fullName ?: p?.username ?: "", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text("@${p?.username ?: ""}", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

        // Badges row
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (p?.isVerified == true) {
                AssistChip(onClick = {}, label = { Text("Verified") },
                    leadingIcon = { Icon(Icons.Filled.Verified, null, Modifier.size(14.dp)) })
            } else {
                AssistChip(
                    onClick = {},
                    label = { Text("Unverified") },
                    colors = AssistChipDefaults.assistChipColors(containerColor = MaterialTheme.colorScheme.errorContainer)
                )
            }
            p?.userType?.let { type ->
                AssistChip(onClick = {}, label = { Text(type.replaceFirstChar { it.uppercase() }) })
            }
        }

        // Stats
        Card(modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
                ProfileStat("Rating", String.format("%.1f", p?.rating ?: 0.0))
                VerticalDivider(Modifier.height(36.dp))
                ProfileStat("Completed", "${p?.completedGigs ?: 0}")
                VerticalDivider(Modifier.height(36.dp))
                ProfileStat("Reviews", "${p?.reviewCount ?: 0}")
            }
        }

        // Logout
        OutlinedButton(
            onClick = onLogoutClick,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
        ) {
            Icon(Icons.Filled.Logout, null, Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text("Log Out")
        }
    }
    HorizontalDivider()
}

@Composable
private fun ProfileStat(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

// ── TAB 1: Personal Info ──────────────────────────────────────────────────────
@Composable
private fun PersonalInfoTab(s: ProfileUiState, vm: ProfileViewModel) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        SectionTitle("Personal Information")
        Text("Update your profile details. This information is visible to clients and other workers.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            ProfileField("Full Name", s.fullName, vm::updateFullName, Modifier.weight(1f))
            ProfileField("Username", s.profile?.username ?: "", {}, Modifier.weight(1f),
                readOnly = true, supportingText = "Cannot be changed")
        }

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            ProfileField("Phone Number", s.phone, vm::updatePhone, Modifier.weight(1f),
                keyboardType = KeyboardType.Phone)
            LocationDropdown(s.location, vm::updateLocation, Modifier.weight(1f))
        }

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            UserTypeDropdown(s.userType, vm::updateUserType, Modifier.weight(1f))
            LanguageDropdown(s.language, vm::updateLanguage, Modifier.weight(1f))
        }

        ProfileField("Bio / About Me", s.bio, vm::updateBio,
            minLines = 3, maxLines = 6,
            placeholder = "Tell us about yourself, your experience and skills...")

        ProfileField("Personal Portfolio URL", s.portfolioUrl, vm::updatePortfolioUrl,
            placeholder = "https://example.com/portfolio",
            keyboardType = KeyboardType.Uri,
            supportingText = "Link to your portfolio or professional profile (LinkedIn, GitHub, personal website).")

        HorizontalDivider()
        SectionTitle("SOCSO & Identity")
        Text("Required for identity verification and SOCSO contributions (Gig Workers Act 2025).",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        ProfileField("IC Number (No. Kad Pengenalan)", s.icNumber, vm::updateIcNumber,
            placeholder = "901234567890",
            keyboardType = KeyboardType.Number,
            supportingText = "12 digits without dashes (-). Required for identity verification.")

        ProfileField("SOCSO Membership Number", s.socsoMembershipNumber, vm::updateSocsoMembershipNumber,
            placeholder = "1234567890",
            supportingText = "Your SOCSO membership number (if available).")

        // SOCSO consent
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (s.socsoConsent) MaterialTheme.colorScheme.primaryContainer
                                 else MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.Top
            ) {
                Checkbox(checked = s.socsoConsent, onCheckedChange = vm::updateSocsoConsent)
                Column {
                    Text("I Agree to SOCSO Deduction", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text("I understand and agree to deduct SOCSO contributions of 1.25% from my earnings for social protection.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }

        SaveButton(s, onClick = vm::savePersonalInfo)
        Spacer(Modifier.height(16.dp))
    }
}

// ── TAB 2: Skills ─────────────────────────────────────────────────────────────
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SkillsTab(s: ProfileUiState, vm: ProfileViewModel) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        SectionTitle("Expertise & Skills")
        Text("Add your skills to help clients find you. Separate skills with commas.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        OutlinedTextField(
            value = s.skills,
            onValueChange = vm::updateSkills,
            label = { Text("Skills") },
            placeholder = { Text("e.g. Graphic Design, Video Editing, Web Development") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 4,
            maxLines = 8,
            supportingText = { Text("Max 20 skills, 50 characters each. Separate with commas.") }
        )

        // Preview chips
        val skillList = s.skills.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        if (skillList.isNotEmpty()) {
            Text("Preview:", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                skillList.take(20).forEach { skill ->
                    AssistChip(onClick = {}, label = { Text(skill, style = MaterialTheme.typography.bodySmall) })
                }
            }
        }

        SaveButton(s, onClick = vm::saveSkills)
        Spacer(Modifier.height(16.dp))
    }
}

// ── TAB 3: Fractional ─────────────────────────────────────────────────────────
@Composable
private fun FractionalTab(s: ProfileUiState, vm: ProfileViewModel) {
    val fractionalRoles = listOf(
        "cto" to "CTO / Tech Lead",
        "cmo" to "CMO / Marketing Lead",
        "cfo" to "CFO / Finance Lead",
        "coo" to "COO / Operations Lead",
        "advisor" to "Advisor / Consultant",
        "other" to "Other"
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        SectionTitle("Fractional Role")

        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Filled.Star, null, tint = MaterialTheme.colorScheme.onSecondaryContainer)
                Column(Modifier.weight(1f)) {
                    Text("Available for Fractional Work", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text("Offer your expertise on a part-time or contract basis to multiple companies.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.8f))
                }
                Switch(checked = s.availableForFractional, onCheckedChange = vm::updateAvailableForFractional)
            }
        }

        if (s.availableForFractional) {
            DropdownField(
                label = "Fractional Role Type",
                selected = s.fractionalRoleType,
                options = fractionalRoles.map { it.first },
                optionLabels = fractionalRoles.map { it.second },
                onSelect = vm::updateFractionalRoleType
            )

            ProfileField(
                "Days Available Per Week",
                s.fractionalDaysAvailable,
                vm::updateFractionalDays,
                keyboardType = KeyboardType.Decimal,
                supportingText = "0.5 to 5.0 days per week"
            )

            SaveButton(s, onClick = vm::saveFractional)
        }
        Spacer(Modifier.height(16.dp))
    }
}

// ── TAB 4: Verification ───────────────────────────────────────────────────────
@Composable
private fun VerificationTab(s: ProfileUiState) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        SectionTitle("Identity Verification")
        Text("Verify your identity to unlock all features and build trust with clients.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        // Verification status card
        val isVerified = s.profile?.isVerified == true
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (isVerified) MaterialTheme.colorScheme.primaryContainer
                                 else MaterialTheme.colorScheme.errorContainer
            )
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    if (isVerified) Icons.Filled.Verified else Icons.Filled.Warning,
                    null,
                    tint = if (isVerified) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                )
                Column {
                    Text(
                        if (isVerified) "Identity Verified" else "Not Verified",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        if (isVerified) "Your identity has been successfully verified."
                        else "Your identity has not been verified yet.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        // Syariah Compliant verified
        val halalVerified = s.profile?.halalVerified == true
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (halalVerified) MaterialTheme.colorScheme.primaryContainer
                                 else MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(if (halalVerified) "✅" else "⏳", style = MaterialTheme.typography.titleMedium)
                Column {
                    Text("Syariah Compliant Verification", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text(
                        if (halalVerified) "Syariah Compliant compliance verified."
                        else "Not yet Syariah Compliant verified.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Document upload note
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Upload, null, tint = MaterialTheme.colorScheme.primary)
                    Text("Upload IC Documents", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                }
                Text("To upload your IC front and back images for identity verification, please visit the GigHala website on a browser.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("gighala.my/settings", style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

// ── TAB 5: Security ───────────────────────────────────────────────────────────
@Composable
private fun SecurityTab(s: ProfileUiState, vm: ProfileViewModel) {
    var showCurrent by remember { mutableStateOf(false) }
    var showNew by remember { mutableStateOf(false) }
    var showConfirm by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        SectionTitle("Change Password")

        PasswordField("Current Password", s.currentPassword, vm::updateCurrentPassword, showCurrent) { showCurrent = !showCurrent }
        PasswordField("New Password", s.newPassword, vm::updateNewPassword, showNew) { showNew = !showNew }
        PasswordField("Confirm New Password", s.confirmPassword, vm::updateConfirmPassword, showConfirm) { showConfirm = !showConfirm }

        if (s.newPassword.isNotEmpty() && s.confirmPassword.isNotEmpty() && s.newPassword != s.confirmPassword) {
            Text("Passwords do not match", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
        }

        Button(
            onClick = vm::changePassword,
            enabled = s.currentPassword.isNotBlank() && s.newPassword.length >= 8 &&
                    s.newPassword == s.confirmPassword && !s.isSaving,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (s.isSaving) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
            else Text("Change Password")
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))
        SectionTitle("Two-Factor Authentication (2FA)")

        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (s.totpEnabled) MaterialTheme.colorScheme.primaryContainer
                                 else MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Filled.Security, null,
                    tint = if (s.totpEnabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
                Column(Modifier.weight(1f)) {
                    Text(if (s.totpEnabled) "2FA Enabled" else "2FA Disabled",
                        style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text(
                        if (s.totpEnabled) "Two-factor authentication is active. Your account is secured."
                        else "Enable 2FA from the web portal to add an extra layer of security.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                if (s.totpEnabled) {
                    TextButton(
                        onClick = vm::disable2fa,
                        colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                    ) { Text("Disable") }
                }
            }
        }

        if (!s.totpEnabled) {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Filled.Info, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                    Text("To enable 2FA, visit gighala.my/settings on a browser with your authenticator app ready.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

// ── TAB 6: Payment ────────────────────────────────────────────────────────────
@Composable
private fun PaymentTab(s: ProfileUiState, vm: ProfileViewModel) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        SectionTitle("Bank Account")
        Text("Add your bank account to receive payouts. Must match your registered name.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        val malaysianBanks = listOf(
            "Maybank", "CIMB Bank", "Public Bank", "RHB Bank", "Hong Leong Bank",
            "AmBank", "Bank Islam", "Bank Rakyat", "BSN", "Affin Bank",
            "OCBC Bank", "Standard Chartered", "HSBC Bank", "Alliance Bank",
            "Bank Simpanan Nasional", "Other"
        )
        DropdownField(
            label = "Bank Name",
            selected = s.bankName,
            options = malaysianBanks,
            optionLabels = malaysianBanks,
            onSelect = vm::updateBankName,
            allowCustom = true
        )

        ProfileField(
            "Account Number",
            s.bankAccountNumber,
            vm::updateBankAccountNumber,
            keyboardType = KeyboardType.Number,
            supportingText = "8-20 digits"
        )
        ProfileField("Account Holder Name", s.bankAccountHolder, vm::updateBankAccountHolder)

        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
            Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Top) {
                Icon(Icons.Filled.Info, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                Text("Account holder name must match your IC name exactly. Bank transfers may take 1-3 business days.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        SaveButton(s, onClick = vm::saveBankInfo)
        Spacer(Modifier.height(16.dp))
    }
}

// ── Shared helpers ────────────────────────────────────────────────────────────

@Composable
private fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun ProfileField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    readOnly: Boolean = false,
    keyboardType: KeyboardType = KeyboardType.Text,
    minLines: Int = 1,
    maxLines: Int = 1,
    placeholder: String? = null,
    supportingText: String? = null
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it) } },
        modifier = modifier.fillMaxWidth(),
        readOnly = readOnly,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        minLines = minLines,
        maxLines = maxLines,
        supportingText = supportingText?.let { { Text(it, style = MaterialTheme.typography.bodySmall) } },
        colors = if (readOnly) OutlinedTextFieldDefaults.colors(
            disabledBorderColor = MaterialTheme.colorScheme.outline,
            disabledTextColor = MaterialTheme.colorScheme.onSurfaceVariant
        ) else OutlinedTextFieldDefaults.colors()
    )
}

@Composable
private fun PasswordField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    visible: Boolean,
    onToggle: () -> Unit
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        modifier = Modifier.fillMaxWidth(),
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        trailingIcon = {
            IconButton(onClick = onToggle) {
                Icon(if (visible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility, null)
            }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LocationDropdown(selected: String, onSelect: (String) -> Unit, modifier: Modifier = Modifier) {
    val states = listOf("Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan",
        "Pahang", "Perak", "Perlis", "Pulau Pinang", "Sabah", "Sarawak", "Selangor",
        "Terengganu", "Kuala Lumpur", "Labuan", "Putrajaya")
    DropdownField("Location", selected, states, states, onSelect, modifier)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UserTypeDropdown(selected: String, onSelect: (String) -> Unit, modifier: Modifier = Modifier) {
    DropdownField(
        "User Type", selected,
        listOf("freelancer", "client", "both"),
        listOf("Freelancer (Job Seeker)", "Client (Employer)", "Both"),
        onSelect, modifier
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LanguageDropdown(selected: String, onSelect: (String) -> Unit, modifier: Modifier = Modifier) {
    DropdownField(
        "Preferred Language", selected,
        listOf("ms", "en"),
        listOf("Bahasa Melayu", "English"),
        onSelect, modifier
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DropdownField(
    label: String,
    selected: String,
    options: List<String>,
    optionLabels: List<String>,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
    allowCustom: Boolean = false
) {
    var expanded by remember { mutableStateOf(false) }
    val displayValue = if (allowCustom && selected !in options) selected
                       else optionLabels.getOrNull(options.indexOf(selected)) ?: selected

    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }, modifier = modifier) {
        OutlinedTextField(
            value = displayValue,
            onValueChange = if (allowCustom) onSelect else { _ -> },
            readOnly = !allowCustom,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier.fillMaxWidth().menuAnchor()
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEachIndexed { i, opt ->
                DropdownMenuItem(
                    text = { Text(optionLabels.getOrElse(i) { opt }) },
                    onClick = { onSelect(opt); expanded = false }
                )
            }
        }
    }
}

@Composable
private fun SaveButton(s: ProfileUiState, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = !s.isSaving,
        modifier = Modifier.fillMaxWidth()
    ) {
        if (s.isSaving) {
            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
            Spacer(Modifier.width(8.dp))
            Text("Saving…")
        } else {
            Text("Save Changes")
        }
    }
}
