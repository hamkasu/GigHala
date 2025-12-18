#!/usr/bin/env python3
"""
Migration: Backfill Transaction records for released escrows
This migration ensures all released escrows have corresponding Transaction records
with proper commission tracking for admin financial statistics.
"""

import os
import sys

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Escrow, Transaction
from datetime import datetime

def backfill_transactions():
    """Create Transaction records for all released escrows that don't have them"""
    with app.app_context():
        try:
            # Find all released escrows
            released_escrows = Escrow.query.filter_by(status='released').all()

            created_count = 0
            updated_count = 0
            skipped_count = 0

            print(f"Found {len(released_escrows)} released escrows")

            for escrow in released_escrows:
                # Check if transaction already exists for this gig
                transaction = Transaction.query.filter_by(gig_id=escrow.gig_id).first()

                if not transaction:
                    # Create new transaction
                    transaction = Transaction(
                        gig_id=escrow.gig_id,
                        freelancer_id=escrow.freelancer_id,
                        client_id=escrow.client_id,
                        amount=escrow.amount,
                        commission=escrow.platform_fee,
                        net_amount=escrow.net_amount,
                        payment_method='escrow',
                        status='completed',
                        transaction_date=escrow.released_at or escrow.created_at
                    )
                    db.session.add(transaction)
                    created_count += 1
                    print(f"✓ Created transaction for escrow #{escrow.escrow_number} (Gig #{escrow.gig_id})")

                elif transaction.commission == 0 or transaction.commission is None:
                    # Update existing transaction with commission if missing
                    transaction.commission = escrow.platform_fee
                    transaction.status = 'completed'
                    updated_count += 1
                    print(f"✓ Updated transaction for escrow #{escrow.escrow_number} (Gig #{escrow.gig_id})")

                else:
                    skipped_count += 1
                    print(f"- Skipped escrow #{escrow.escrow_number} (transaction already exists with commission)")

            # Commit all changes
            db.session.commit()

            print("\n" + "="*60)
            print("Migration Summary:")
            print("="*60)
            print(f"Total released escrows: {len(released_escrows)}")
            print(f"New transactions created: {created_count}")
            print(f"Existing transactions updated: {updated_count}")
            print(f"Skipped (already correct): {skipped_count}")
            print("="*60)

            # Calculate total commission
            total_commission = db.session.query(db.func.sum(Transaction.commission)).filter_by(status='completed').scalar() or 0
            print(f"\nTotal commission tracked: RM {total_commission:.2f}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("="*60)
    print("Backfilling Transaction Records for Commission Tracking")
    print("="*60)
    print("\nThis migration will:")
    print("1. Find all released escrows")
    print("2. Create Transaction records for escrows without them")
    print("3. Update Transaction records that are missing commission")
    print("\nStarting migration...\n")

    success = backfill_transactions()

    if success:
        print("\n✓ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Migration failed!")
        sys.exit(1)
