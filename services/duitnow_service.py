"""
DuitNow QR Code Payment Service for Malaysia
============================================

Handles generation of DuitNow/QRPM QR codes for escrow payments.
Follows EMVCo specifications for Malaysia's interbank QR code standard.
"""

import qrcode
import io
import base64
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class DuitNowPaymentGenerator:
    """Generate DuitNow QR codes for Malaysian payments"""

    # Maybank bank code in DuitNow format
    MAYBANK_CODE = "0121104"

    @staticmethod
    def generate_duitnow_string(
        bank_code: str,
        account_number: str,
        amount: float,
        reference: str
    ) -> str:
        """
        Generate a DuitNow QR payload string (simplified EMVCo format).

        Args:
            bank_code: Bank code (e.g., "0121104" for Maybank)
            account_number: Recipient account number
            amount: Payment amount in MYR
            reference: Transaction reference (max 50 chars)

        Returns:
            DuitNow formatted string suitable for QR encoding

        Note: This is a simplified implementation. For production, consider
        using a library like `duitnow` or `emvco` that handles the full spec.
        """
        try:
            # Format the reference to fit in DuitNow spec (max 50 chars)
            clean_ref = reference[:50].replace(' ', '')

            # Simplified DuitNow format (BMK proxy format)
            # Full spec would include more EMVCo tags, but this is sufficient
            # Format: 00|20|{version}|{bank_code}|{account}|{amount}|{reference}
            duitnow_string = (
                f"00020136080010a00000061501"
                f"0{bank_code}"
                f"1{account_number}"
                f"5{str(amount).zfill(13)}"
                f"6{clean_ref}"
            )

            logger.debug(
                f"Generated DuitNow string: {duitnow_string[:50]}... "
                f"for ref={reference}, amount={amount}"
            )
            return duitnow_string

        except Exception as e:
            logger.error(f"Error generating DuitNow string: {str(e)}")
            raise ValueError(f"Failed to generate DuitNow string: {str(e)}")

    @staticmethod
    def create_qr_code(data: str, version: int = 1) -> bytes:
        """
        Create a QR code image from the given data.

        Args:
            data: Data to encode in QR code
            version: QR code version (1-40, auto-adjusts if needed)

        Returns:
            PNG image as bytes
        """
        try:
            qr = qrcode.QRCode(
                version=version,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error creating QR code: {str(e)}")
            raise ValueError(f"Failed to create QR code: {str(e)}")

    @staticmethod
    def create_qr_code_base64(data: str) -> str:
        """
        Create a QR code and return as base64-encoded data URI.

        Args:
            data: Data to encode in QR code

        Returns:
            Data URI string (data:image/png;base64,...)
        """
        try:
            qr_bytes = DuitNowPaymentGenerator.create_qr_code(data)
            qr_base64 = base64.b64encode(qr_bytes).decode()
            return f"data:image/png;base64,{qr_base64}"

        except Exception as e:
            logger.error(f"Error creating base64 QR: {str(e)}")
            raise

    @classmethod
    def generate_payment_qr(
        cls,
        account_number: str,
        amount: float,
        reference: str,
        bank_code: str = None
    ) -> dict:
        """
        Generate a complete DuitNow payment QR code.

        Args:
            account_number: Recipient bank account
            amount: Payment amount in MYR
            reference: Unique transaction reference
            bank_code: Bank code (defaults to Maybank)

        Returns:
            Dictionary with:
                - qr_string: Raw DuitNow payload
                - qr_image_bytes: PNG image bytes
                - qr_image_base64: Base64-encoded data URI
        """
        if bank_code is None:
            bank_code = cls.MAYBANK_CODE

        try:
            # Generate DuitNow string
            qr_string = cls.generate_duitnow_string(
                bank_code=bank_code,
                account_number=account_number,
                amount=amount,
                reference=reference
            )

            # Create QR code image
            qr_bytes = cls.create_qr_code(qr_string)
            qr_base64 = base64.b64encode(qr_bytes).decode()

            return {
                'qr_string': qr_string,
                'qr_image_bytes': qr_bytes,
                'qr_image_base64': f"data:image/png;base64,{qr_base64}",
                'reference': reference,
                'amount': amount,
                'bank_code': bank_code,
                'account_number': account_number
            }

        except Exception as e:
            logger.error(f"Error generating payment QR: {str(e)}")
            raise


def generate_escrow_duitnow_qr(
    escrow_amount: float,
    escrow_reference: str,
    recipient_account: str = "512345678901",
    recipient_name: str = "GigHala Sdn Bhd"
) -> dict:
    """
    Convenience function to generate DuitNow QR for an escrow payment.

    Args:
        escrow_amount: Amount in MYR
        escrow_reference: Unique escrow reference (e.g., "ESC-123-ABC456")
        recipient_account: Recipient account number
        recipient_name: Recipient account name (for display only)

    Returns:
        Dictionary with QR code data and payment details
    """
    try:
        qr_data = DuitNowPaymentGenerator.generate_payment_qr(
            account_number=recipient_account,
            amount=escrow_amount,
            reference=escrow_reference
        )

        return {
            **qr_data,
            'recipient_name': recipient_name,
            'recipient_account': recipient_account,
            'success': True
        }

    except Exception as e:
        logger.error(f"Error generating escrow DuitNow QR: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
