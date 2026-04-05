package com.gighala.app.ui.wallet

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class WalletUiState(
    // Header cards
    val wallet: WalletDto? = null,
    val totalSocso: Double = 0.0,
    val isLoadingWallet: Boolean = true,
    val walletError: String? = null,

    // Transactions tab
    val transactions: List<TransactionDto> = emptyList(),
    val isLoadingTransactions: Boolean = false,
    val transactionTypeFilter: String = "all", // all | sent | received

    // Invoices tab
    val invoices: List<InvoiceDto> = emptyList(),
    val isLoadingInvoices: Boolean = false,

    // Payouts tab
    val payouts: List<PayoutDto> = emptyList(),
    val isLoadingPayouts: Boolean = false,

    // SOCSO tab
    val socsoContributions: List<SocsoContributionDto> = emptyList(),
    val socsoTotals: SocsoTotals = SocsoTotals(),
    val isLoadingSocso: Boolean = false,

    // Payout request dialog
    val showPayoutDialog: Boolean = false,
    val payoutAmount: String = "",
    val payoutBankName: String = "",
    val payoutAccountNumber: String = "",
    val payoutAccountName: String = "",
    val isSubmittingPayout: Boolean = false,
    val payoutSuccess: String? = null,
    val payoutError: String? = null
)

@HiltViewModel
class WalletViewModel @Inject constructor(
    private val api: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(WalletUiState())
    val uiState: StateFlow<WalletUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        loadWallet()
        loadTransactions()
        loadInvoices()
        loadPayouts()
        loadSocso()
    }

    fun loadWallet() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingWallet = true, walletError = null)
            try {
                val walletDef = async { api.getWallet() }
                val statsDef  = async { api.getBillingStats() }
                val walletResp = walletDef.await()
                val statsResp  = statsDef.await()
                _uiState.value = _uiState.value.copy(
                    isLoadingWallet = false,
                    wallet = if (walletResp.isSuccessful) walletResp.body() else null,
                    totalSocso = if (statsResp.isSuccessful) statsResp.body()?.totalSocso ?: 0.0 else 0.0,

                    walletError = if (!walletResp.isSuccessful) "Failed to load wallet" else null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoadingWallet = false, walletError = e.message)
            }
        }
    }

    fun loadTransactions(type: String = _uiState.value.transactionTypeFilter) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingTransactions = true, transactionTypeFilter = type)
            try {
                val resp = api.getTransactions(type = if (type == "all") null else type)
                _uiState.value = _uiState.value.copy(
                    isLoadingTransactions = false,
                    transactions = if (resp.isSuccessful) resp.body() ?: emptyList() else emptyList()
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoadingTransactions = false)
            }
        }
    }

    fun loadInvoices() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingInvoices = true)
            try {
                val resp = api.getInvoices()
                _uiState.value = _uiState.value.copy(
                    isLoadingInvoices = false,
                    invoices = if (resp.isSuccessful) resp.body() ?: emptyList() else emptyList()
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoadingInvoices = false)
            }
        }
    }

    fun loadPayouts() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingPayouts = true)
            try {
                val resp = api.getPayouts()
                _uiState.value = _uiState.value.copy(
                    isLoadingPayouts = false,
                    payouts = if (resp.isSuccessful) resp.body() ?: emptyList() else emptyList()
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoadingPayouts = false)
            }
        }
    }

    fun loadSocso() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingSocso = true)
            try {
                val resp = api.getSocsoContributions()
                val body = if (resp.isSuccessful) resp.body() else null
                _uiState.value = _uiState.value.copy(
                    isLoadingSocso = false,
                    socsoContributions = body?.contributions ?: emptyList(),
                    socsoTotals = body?.totals ?: SocsoTotals()
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoadingSocso = false)
            }
        }
    }

    fun setTransactionFilter(type: String) = loadTransactions(type)

    fun showPayoutDialog() {
        _uiState.value = _uiState.value.copy(showPayoutDialog = true, payoutSuccess = null, payoutError = null)
    }
    fun dismissPayoutDialog() {
        _uiState.value = _uiState.value.copy(showPayoutDialog = false, payoutSuccess = null, payoutError = null)
    }
    fun updatePayoutAmount(v: String)        { _uiState.value = _uiState.value.copy(payoutAmount = v) }
    fun updatePayoutBankName(v: String)      { _uiState.value = _uiState.value.copy(payoutBankName = v) }
    fun updatePayoutAccountNumber(v: String) { _uiState.value = _uiState.value.copy(payoutAccountNumber = v) }
    fun updatePayoutAccountName(v: String)   { _uiState.value = _uiState.value.copy(payoutAccountName = v) }

    fun submitPayout() {
        val s = _uiState.value
        val amount = s.payoutAmount.toDoubleOrNull() ?: return
        viewModelScope.launch {
            _uiState.value = s.copy(isSubmittingPayout = true, payoutError = null)
            try {
                val resp = api.requestPayout(PayoutRequest(
                    amount = amount,
                    paymentMethod = "bank_transfer",
                    bankName = s.payoutBankName,
                    accountNumber = s.payoutAccountNumber,
                    accountName = s.payoutAccountName
                ))
                val body = resp.body()
                if (resp.isSuccessful && body != null) {
                    _uiState.value = _uiState.value.copy(
                        isSubmittingPayout = false,
                        payoutSuccess = "Payout ${body.payoutNumber} submitted (${body.netAmount?.let { "Net: RM%.2f".format(it) } ?: ""})",
                        showPayoutDialog = false,
                        payoutAmount = "", payoutBankName = "", payoutAccountNumber = "", payoutAccountName = ""
                    )
                    loadWallet()
                    loadPayouts()
                } else {
                    val errBody = resp.errorBody()?.string() ?: ""
                    _uiState.value = _uiState.value.copy(isSubmittingPayout = false, payoutError = errBody.ifBlank { "Payout failed" })
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSubmittingPayout = false, payoutError = e.message ?: "Network error")
            }
        }
    }
}
