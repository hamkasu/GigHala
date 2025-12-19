"""
PayHalal Integration Module for GigHala
Malaysia's First Shariah-Compliant Payment Gateway

This module provides integration with PayHalal (https://payhalal.my/) for processing
halal-compliant payments including FPX, cards, and e-wallets.

Configuration Required:
- PAYHALAL_MERCHANT_ID: Your PayHalal merchant ID
- PAYHALAL_API_KEY: Your PayHalal API key
- PAYHALAL_SECRET_KEY: Your PayHalal secret key
- PAYHALAL_SANDBOX: Set to 'true' for sandbox mode
"""

import os
import hashlib
import hmac
import requests
from datetime import datetime
from typing import Dict, Optional, Any
import json

class PayHalalConfig:
    """PayHalal configuration settings"""
    SANDBOX_URL = "https://sandbox.payhalal.my/api"
    PRODUCTION_URL = "https://api.payhalal.my/api"
    
    def __init__(self):
        self.merchant_id = os.environ.get('PAYHALAL_MERCHANT_ID', '')
        self.api_key = os.environ.get('PAYHALAL_API_KEY', '')
        self.secret_key = os.environ.get('PAYHALAL_SECRET_KEY', '')
        self.is_sandbox = os.environ.get('PAYHALAL_SANDBOX', 'true').lower() == 'true'
    
    @property
    def base_url(self) -> str:
        return self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL
    
    @property
    def is_configured(self) -> bool:
        return bool(self.merchant_id and self.api_key and self.secret_key)


class PayHalalClient:
    """
    PayHalal API Client for Malaysia's Shariah-Compliant Payment Gateway
    
    Supported Payment Methods:
    - FPX (Online Banking)
    - Credit/Debit Cards (Visa, Mastercard)
    - E-Wallets (Touch 'n Go, GrabPay - Shariah-screened)
    
    Usage:
        client = PayHalalClient()
        if client.is_available():
            result = client.create_payment(
                amount=100.00,
                order_id="GIG-001",
                description="Payment for gig",
                customer_email="customer@email.com",
                customer_name="Ahmad",
                return_url="https://yoursite.com/payment/success",
                callback_url="https://yoursite.com/api/payhalal/webhook"
            )
    """
    
    def __init__(self):
        self.config = PayHalalConfig()
    
    def is_available(self) -> bool:
        """Check if PayHalal is properly configured"""
        return self.config.is_configured
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC signature for API request"""
        sorted_data = sorted(data.items())
        message = '&'.join([f"{k}={v}" for k, v in sorted_data if v is not None and v != ''])
        signature = hmac.new(
            self.config.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint: str, data: Dict[str, Any], method: str = 'POST') -> Dict:
        """Make API request to PayHalal"""
        url = f"{self.config.base_url}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.api_key}',
            'X-Merchant-ID': self.config.merchant_id
        }
        
        data['signature'] = self._generate_signature(data)
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                response = requests.get(url, params=data, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'error_code': 'REQUEST_FAILED'
            }
    
    def create_payment(
        self,
        amount: float,
        order_id: str,
        description: str,
        customer_email: str,
        customer_name: str,
        return_url: str,
        callback_url: str,
        customer_phone: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new payment request
        
        Args:
            amount: Payment amount in MYR
            order_id: Unique order/invoice ID
            description: Payment description
            customer_email: Customer email address
            customer_name: Customer full name
            return_url: URL to redirect after payment
            callback_url: URL for payment notification webhook
            customer_phone: Customer phone number (optional)
            payment_method: Specific payment method - fpx, card, ewallet (optional)
        
        Returns:
            Dict with payment_url for redirect, or error details
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'PayHalal is not configured. Please set PAYHALAL_MERCHANT_ID, PAYHALAL_API_KEY, and PAYHALAL_SECRET_KEY.',
                'error_code': 'NOT_CONFIGURED'
            }
        
        data = {
            'merchant_id': self.config.merchant_id,
            'order_id': order_id,
            'amount': f"{amount:.2f}",
            'currency': 'MYR',
            'description': description,
            'customer_email': customer_email,
            'customer_name': customer_name,
            'return_url': return_url,
            'callback_url': callback_url,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if customer_phone:
            data['customer_phone'] = customer_phone
        
        if payment_method:
            data['payment_method'] = payment_method
        
        result = self._make_request('payments/create', data)
        
        if result.get('success') or result.get('payment_url'):
            return {
                'success': True,
                'payment_url': result.get('payment_url'),
                'payment_id': result.get('payment_id'),
                'order_id': order_id
            }
        
        return {
            'success': False,
            'error': result.get('error', 'Payment creation failed'),
            'error_code': result.get('error_code', 'UNKNOWN')
        }
    
    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Verify payment status
        
        Args:
            payment_id: PayHalal payment ID
        
        Returns:
            Dict with payment status details
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'PayHalal is not configured',
                'error_code': 'NOT_CONFIGURED'
            }
        
        data = {
            'merchant_id': self.config.merchant_id,
            'payment_id': payment_id
        }
        
        result = self._make_request('payments/verify', data, method='GET')
        
        return {
            'success': result.get('success', False),
            'status': result.get('status'),
            'amount': result.get('amount'),
            'payment_method': result.get('payment_method'),
            'paid_at': result.get('paid_at'),
            'error': result.get('error')
        }
    
    def verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify webhook signature from PayHalal
        
        Args:
            payload: Webhook payload data
            signature: Signature from X-PayHalal-Signature header
        
        Returns:
            True if signature is valid
        """
        expected_signature = self._generate_signature(payload)
        return hmac.compare_digest(expected_signature, signature)
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """
        Get available payment methods for the merchant
        
        Returns:
            Dict with available payment methods
        """
        return {
            'success': True,
            'methods': [
                {
                    'id': 'fpx',
                    'name': 'FPX Online Banking',
                    'description': 'Pay directly from your Malaysian bank account',
                    'icon': '🏦',
                    'supported_banks': [
                        'Maybank', 'CIMB', 'Public Bank', 'RHB', 'Hong Leong',
                        'AmBank', 'Bank Islam', 'Bank Rakyat', 'BSN', 'Affin Bank'
                    ]
                },
                {
                    'id': 'card',
                    'name': 'Credit/Debit Card',
                    'description': 'Visa and Mastercard accepted',
                    'icon': '💳',
                    'supported_cards': ['Visa', 'Mastercard']
                },
                {
                    'id': 'ewallet',
                    'name': 'E-Wallet',
                    'description': 'Touch n Go, GrabPay (Shariah-screened)',
                    'icon': '📱',
                    'supported_wallets': ['Touch n Go', 'GrabPay']
                }
            ]
        }


def get_payhalal_client() -> PayHalalClient:
    """Get PayHalal client instance"""
    return PayHalalClient()


PROCESSING_FEE_PERCENT_PAYHALAL = 0.02
PROCESSING_FEE_FIXED_PAYHALAL = 0.00

def calculate_payhalal_processing_fee(amount: float) -> float:
    """Calculate PayHalal processing fee (2% with no fixed fee)"""
    return round(amount * PROCESSING_FEE_PERCENT_PAYHALAL + PROCESSING_FEE_FIXED_PAYHALAL, 2)
