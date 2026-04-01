"""
GigHala Retainer Escrow Service
================================
Handles fractional / retained engagement escrow lifecycle:
  - Initiating a monthly retainer
  - Releasing a monthly payment to the expert
  - Marking a month as complete (client confirmation)
  - Requesting 30-day termination notice

Circular-import note: all app-level objects (db, models) are imported
lazily inside each function — the same pattern used in gig_matching_service.py.
"""

import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Commission
# ---------------------------------------------------------------------------

def calculate_commission(amount, listing_type):
    """Return platform commission amount.

    8 % for fractional/retained engagements, 10 % for standard gigs.

    Args:
        amount      : Gross amount (numeric or float).
        listing_type: 'fractional' | 'retained' | 'gig'.

    Returns:
        Float commission amount rounded to 2 d.p.
    """
    rate = 0.08 if listing_type in ('fractional', 'retained') else 0.10
    return round(float(amount) * rate, 2)


# ---------------------------------------------------------------------------
# Initiate retainer
# ---------------------------------------------------------------------------

def initiate_retainer(gig_id, client_id, freelancer_id, monthly_amount):
    """Create an Escrow record to start a monthly retainer engagement.

    Args:
        gig_id          : ID of the fractional Gig listing.
        client_id       : ID of the client User.
        freelancer_id   : ID of the expert/freelancer User.
        monthly_amount  : Monthly retainer amount (MYR).

    Returns:
        (escrow, None)           on success.
        (None, error_message)    on failure.
    """
    from app import db, Escrow, Gig

    try:
        gig = Gig.query.get(gig_id)
        if not gig:
            return None, f'Gig {gig_id} not found'

        amount = float(monthly_amount)
        platform_fee = calculate_commission(amount, 'fractional')
        net_amount = round(amount - platform_fee, 2)

        escrow_number = 'RET-' + uuid.uuid4().hex[:8].upper()
        now = datetime.utcnow()

        escrow = Escrow(
            escrow_number=escrow_number,
            gig_id=gig_id,
            client_id=client_id,
            freelancer_id=freelancer_id,
            amount=amount,
            platform_fee=platform_fee,
            net_amount=net_amount,
            status='active_retainer',
            retainer_start_date=now,
            retainer_next_due=now + timedelta(days=30),
        )
        db.session.add(escrow)
        db.session.commit()

        logger.info(
            'Retainer initiated: escrow=%s gig=%s client=%s freelancer=%s amount=%.2f',
            escrow_number, gig_id, client_id, freelancer_id, amount
        )
        return escrow, None

    except Exception as e:
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error('initiate_retainer error: %s', str(e))
        return None, str(e)


# ---------------------------------------------------------------------------
# Release monthly payment
# ---------------------------------------------------------------------------

def release_monthly_payment(escrow_id):
    """Release the current month's retainer payment to the freelancer.

    Sets released_at, advances retainer_next_due by 30 days, and keeps
    status as 'active_retainer' so the engagement continues.

    Args:
        escrow_id: ID of the Escrow record.

    Returns:
        (True, None)             on success.
        (False, error_message)   on failure.
    """
    from app import db, Escrow, AuditLog

    try:
        escrow = Escrow.query.get(escrow_id)
        if not escrow:
            return False, f'Escrow {escrow_id} not found'

        if escrow.status not in ('active_retainer', 'month_complete'):
            return False, (
                f'Cannot release payment — escrow status is '
                f'"{escrow.status}", expected "active_retainer"'
            )

        now = datetime.utcnow()
        prev_due = escrow.retainer_next_due or now
        escrow.released_at = now
        escrow.retainer_next_due = prev_due + timedelta(days=30)
        escrow.status = 'active_retainer'

        # Audit trail
        try:
            audit = AuditLog(
                event_category='financial',
                event_type='retainer_payment_released',
                severity='low',
                action=f'Monthly retainer payment released for escrow {escrow.escrow_number}',
                resource_type='escrow',
                resource_id=str(escrow_id),
                status='success',
                message=f'Net amount MYR {escrow.net_amount:.2f} released to freelancer {escrow.freelancer_id}',
            )
            db.session.add(audit)
        except Exception:
            pass  # Audit failure must not block payment release

        db.session.commit()

        logger.info(
            'Monthly payment released: escrow=%s next_due=%s',
            escrow.escrow_number, escrow.retainer_next_due
        )
        return True, None

    except Exception as e:
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error('release_monthly_payment error escrow %s: %s', escrow_id, str(e))
        return False, str(e)


# ---------------------------------------------------------------------------
# Mark month complete
# ---------------------------------------------------------------------------

def mark_month_complete(escrow_id):
    """Client confirms delivery for the current month, then auto-releases payment.

    Transitions: active_retainer → month_complete → active_retainer.

    Args:
        escrow_id: ID of the Escrow record.

    Returns:
        (True, None)             on success.
        (False, error_message)   on failure.
    """
    from app import db, Escrow

    try:
        escrow = Escrow.query.get(escrow_id)
        if not escrow:
            return False, f'Escrow {escrow_id} not found'

        if escrow.status != 'active_retainer':
            return False, (
                f'Cannot mark month complete — status is "{escrow.status}"'
            )

        # Temporarily mark as month_complete, then release
        escrow.status = 'month_complete'
        db.session.commit()

        success, error = release_monthly_payment(escrow_id)
        if not success:
            # Roll back to active_retainer if release fails
            escrow.status = 'active_retainer'
            db.session.commit()
            return False, error

        return True, None

    except Exception as e:
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error('mark_month_complete error escrow %s: %s', escrow_id, str(e))
        return False, str(e)


# ---------------------------------------------------------------------------
# Request termination
# ---------------------------------------------------------------------------

def request_termination(escrow_id, requesting_party):
    """Issue a 30-day termination notice for a retainer engagement.

    Args:
        escrow_id        : ID of the Escrow record.
        requesting_party : 'client' or 'freelancer'.

    Returns:
        Updated Escrow object on success, or None on failure.
    """
    from app import db, Escrow, AuditLog

    if requesting_party not in ('client', 'freelancer'):
        logger.error(
            'request_termination: invalid requesting_party "%s"', requesting_party
        )
        return None

    try:
        escrow = Escrow.query.get(escrow_id)
        if not escrow:
            logger.error('request_termination: escrow %s not found', escrow_id)
            return None

        now = datetime.utcnow()
        effective_date = now + timedelta(days=30)

        escrow.termination_requested = True
        escrow.termination_requested_by = requesting_party
        escrow.termination_notice_date = now

        # Audit trail
        try:
            audit = AuditLog(
                event_category='financial',
                event_type='retainer_termination_requested',
                severity='medium',
                action=(
                    f'Termination notice issued by {requesting_party} '
                    f'for escrow {escrow.escrow_number}'
                ),
                resource_type='escrow',
                resource_id=str(escrow_id),
                status='success',
                message=(
                    f'30-day notice period starts {now.strftime("%d %b %Y")}; '
                    f'effective {effective_date.strftime("%d %b %Y")}'
                ),
            )
            db.session.add(audit)
        except Exception:
            pass

        db.session.commit()

        logger.info(
            'Termination requested: escrow=%s by=%s effective=%s',
            escrow.escrow_number, requesting_party,
            effective_date.strftime('%Y-%m-%d')
        )
        return escrow

    except Exception as e:
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        logger.error('request_termination error escrow %s: %s', escrow_id, str(e))
        return None
