package com.gighala.app.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.*
import com.gighala.app.data.repository.AuthRepository
import com.gighala.app.data.repository.AuthState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val profile: UserDto? = null,
    val isLoading: Boolean = true,
    val loadError: String? = null,

    // Personal Info fields
    val fullName: String = "",
    val phone: String = "",
    val location: String = "",
    val userType: String = "both",
    val language: String = "ms",
    val bio: String = "",
    val portfolioUrl: String = "",
    val icNumber: String = "",
    val socsoMembershipNumber: String = "",
    val socsoConsent: Boolean = false,

    // Skills
    val skills: String = "",   // comma-separated in UI

    // Fractional
    val availableForFractional: Boolean = false,
    val fractionalRoleType: String = "",
    val fractionalDaysAvailable: String = "1.0",

    // Security
    val currentPassword: String = "",
    val newPassword: String = "",
    val confirmPassword: String = "",
    val totpEnabled: Boolean = false,

    // Payment
    val bankName: String = "",
    val bankAccountNumber: String = "",
    val bankAccountHolder: String = "",

    // Status
    val isSaving: Boolean = false,
    val saveSuccess: String? = null,
    val saveError: String? = null
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    // Legacy compatibility — other screens that read user from ProfileViewModel
    val user: StateFlow<UserDto?> = _uiState.map { it.profile }.stateIn(
        viewModelScope, SharingStarted.WhileSubscribed(5000), null
    )

    init {
        loadProfile()
    }

    fun loadProfile() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, loadError = null)
            try {
                val resp = api.getProfile()
                val p = if (resp.isSuccessful) resp.body() else null
                if (p != null) {
                    populateFields(p)
                } else {
                    // Fallback to auth state
                    val authUser = (authRepository.authState.value as? AuthState.Authenticated)?.user
                    if (authUser != null) populateFields(authUser)
                    else _uiState.value = _uiState.value.copy(isLoading = false, loadError = "Failed to load profile")
                }
                // Load 2FA status
                val tfaResp = api.get2faStatus()
                if (tfaResp.isSuccessful) {
                    _uiState.value = _uiState.value.copy(totpEnabled = tfaResp.body()?.totpEnabled ?: false)
                }
            } catch (e: Exception) {
                // Fallback to auth state
                val authUser = (authRepository.authState.value as? AuthState.Authenticated)?.user
                if (authUser != null) populateFields(authUser)
                else _uiState.value = _uiState.value.copy(isLoading = false, loadError = e.message)
            }
        }
    }

    private fun populateFields(p: UserDto) {
        _uiState.value = _uiState.value.copy(
            profile = p,
            isLoading = false,
            fullName = p.fullName ?: "",
            phone = p.phone ?: "",
            location = p.location ?: "",
            userType = p.userType,
            language = p.language ?: "ms",
            bio = p.bio ?: "",
            portfolioUrl = p.portfolioUrl ?: "",
            icNumber = p.icNumber ?: "",
            socsoMembershipNumber = p.socsoMembershipNumber ?: "",
            socsoConsent = p.socsoConsent,
            skills = p.skills ?: "",
            availableForFractional = p.availableForFractional,
            fractionalRoleType = p.fractionalRoleType ?: "",
            fractionalDaysAvailable = p.fractionalDaysAvailable.toString(),
            totpEnabled = p.totpEnabled,
            bankName = p.bankName ?: "",
            bankAccountNumber = p.bankAccountNumber ?: "",
            bankAccountHolder = p.bankAccountHolder ?: ""
        )
    }

    // ── Field update helpers ──────────────────────────────────────────────────
    fun updateFullName(v: String)              { _uiState.value = _uiState.value.copy(fullName = v) }
    fun updatePhone(v: String)                 { _uiState.value = _uiState.value.copy(phone = v) }
    fun updateLocation(v: String)              { _uiState.value = _uiState.value.copy(location = v) }
    fun updateUserType(v: String)              { _uiState.value = _uiState.value.copy(userType = v) }
    fun updateLanguage(v: String)              { _uiState.value = _uiState.value.copy(language = v) }
    fun updateBio(v: String)                   { _uiState.value = _uiState.value.copy(bio = v) }
    fun updatePortfolioUrl(v: String)          { _uiState.value = _uiState.value.copy(portfolioUrl = v) }
    fun updateIcNumber(v: String)              { _uiState.value = _uiState.value.copy(icNumber = v) }
    fun updateSocsoMembershipNumber(v: String) { _uiState.value = _uiState.value.copy(socsoMembershipNumber = v) }
    fun updateSocsoConsent(v: Boolean)         { _uiState.value = _uiState.value.copy(socsoConsent = v) }
    fun updateSkills(v: String)                { _uiState.value = _uiState.value.copy(skills = v) }
    fun updateAvailableForFractional(v: Boolean) { _uiState.value = _uiState.value.copy(availableForFractional = v) }
    fun updateFractionalRoleType(v: String)    { _uiState.value = _uiState.value.copy(fractionalRoleType = v) }
    fun updateFractionalDays(v: String)        { _uiState.value = _uiState.value.copy(fractionalDaysAvailable = v) }
    fun updateCurrentPassword(v: String)       { _uiState.value = _uiState.value.copy(currentPassword = v) }
    fun updateNewPassword(v: String)           { _uiState.value = _uiState.value.copy(newPassword = v) }
    fun updateConfirmPassword(v: String)       { _uiState.value = _uiState.value.copy(confirmPassword = v) }
    fun updateBankName(v: String)              { _uiState.value = _uiState.value.copy(bankName = v) }
    fun updateBankAccountNumber(v: String)     { _uiState.value = _uiState.value.copy(bankAccountNumber = v) }
    fun updateBankAccountHolder(v: String)     { _uiState.value = _uiState.value.copy(bankAccountHolder = v) }
    fun clearMessages()                        { _uiState.value = _uiState.value.copy(saveSuccess = null, saveError = null) }

    // ── Save personal info ────────────────────────────────────────────────────
    fun savePersonalInfo() {
        val s = _uiState.value
        viewModelScope.launch {
            _uiState.value = s.copy(isSaving = true, saveSuccess = null, saveError = null)
            try {
                val skillsList = s.skills.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                val resp = api.updateProfile(UpdateProfileRequest(
                    fullName = s.fullName,
                    phone = s.phone,
                    location = s.location,
                    bio = s.bio,
                    skills = skillsList,
                    userType = s.userType,
                    language = s.language,
                    portfolioUrl = s.portfolioUrl,
                    icNumber = s.icNumber,
                    socsoMembershipNumber = s.socsoMembershipNumber,
                    socsoConsent = s.socsoConsent
                ))
                if (resp.isSuccessful) {
                    _uiState.value = _uiState.value.copy(isSaving = false, saveSuccess = "Profile updated successfully")
                    loadProfile()
                } else {
                    val err = resp.errorBody()?.string() ?: "Update failed"
                    _uiState.value = _uiState.value.copy(isSaving = false, saveError = err)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, saveError = e.message ?: "Network error")
            }
        }
    }

    // ── Save skills (same endpoint) ───────────────────────────────────────────
    fun saveSkills() = savePersonalInfo()

    // ── Save fractional ───────────────────────────────────────────────────────
    fun saveFractional() {
        val s = _uiState.value
        viewModelScope.launch {
            _uiState.value = s.copy(isSaving = true, saveSuccess = null, saveError = null)
            try {
                val days = s.fractionalDaysAvailable.toFloatOrNull() ?: 1.0f
                val resp = api.updateFractional(
                    available = s.availableForFractional,
                    roleType = s.fractionalRoleType,
                    daysAvailable = days
                )
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    saveSuccess = if (resp.isSuccessful) "Fractional settings saved" else null,
                    saveError = if (!resp.isSuccessful) "Save failed" else null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, saveError = e.message)
            }
        }
    }

    // ── Change password ───────────────────────────────────────────────────────
    fun changePassword() {
        val s = _uiState.value
        if (s.newPassword != s.confirmPassword) {
            _uiState.value = s.copy(saveError = "Passwords do not match")
            return
        }
        if (s.newPassword.length < 8) {
            _uiState.value = s.copy(saveError = "Password must be at least 8 characters")
            return
        }
        viewModelScope.launch {
            _uiState.value = s.copy(isSaving = true, saveSuccess = null, saveError = null)
            try {
                val resp = api.changePassword(s.currentPassword, s.newPassword, s.confirmPassword)
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    saveSuccess = if (resp.isSuccessful) "Password changed successfully" else null,
                    saveError = if (!resp.isSuccessful) "Incorrect current password or server error" else null,
                    currentPassword = "", newPassword = "", confirmPassword = ""
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, saveError = e.message)
            }
        }
    }

    // ── Disable 2FA ───────────────────────────────────────────────────────────
    fun disable2fa() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, saveSuccess = null, saveError = null)
            try {
                val resp = api.disable2fa()
                if (resp.isSuccessful) {
                    _uiState.value = _uiState.value.copy(isSaving = false, totpEnabled = false, saveSuccess = "2FA disabled")
                } else {
                    _uiState.value = _uiState.value.copy(isSaving = false, saveError = "Failed to disable 2FA")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, saveError = e.message)
            }
        }
    }

    // ── Save bank info ────────────────────────────────────────────────────────
    fun saveBankInfo() {
        val s = _uiState.value
        viewModelScope.launch {
            _uiState.value = s.copy(isSaving = true, saveSuccess = null, saveError = null)
            try {
                val resp = api.updateBankInfo(s.bankName, s.bankAccountNumber, s.bankAccountHolder)
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    saveSuccess = if (resp.isSuccessful) "Bank info saved" else null,
                    saveError = if (!resp.isSuccessful) "Save failed" else null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSaving = false, saveError = e.message)
            }
        }
    }

    // ── Logout ────────────────────────────────────────────────────────────────
    fun logout() {
        viewModelScope.launch { authRepository.logout() }
    }
}
