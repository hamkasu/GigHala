#!/usr/bin/env python3
"""
Database Migration Script to Add Milestone Payment Support

This migration adds:
1. payment_type field to the gig table
2. milestone table for tracking milestones
3. milestone_payment table for tracking milestone-based escrow payments

Date: 2026-01-10
"""

import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import inspect, text

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def check_table_exists(table_name):
    """Check if a table exists"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()

def add_milestone_payment_support():
    """Add milestone payment support to the database"""

    print("\n🔧 Adding milestone payment support...")
    print("-" * 60)

    try:
        # Check if payment_type column exists in gig table
        if not check_column_exists('gig', 'payment_type'):
            print("➕ Adding payment_type column to gig table...")
            db.session.execute(text(
                "ALTER TABLE gig ADD COLUMN payment_type VARCHAR(20) DEFAULT 'full_payment'"
            ))
            print("   ✅ Added payment_type column")
        else:
            print("ℹ️  payment_type column already exists in gig table")

        # Create milestone table if it doesn't exist
        if not check_table_exists('milestone'):
            print("➕ Creating milestone table...")

            # Determine database type
            db_type = db.engine.dialect.name

            if db_type == 'postgresql':
                db.session.execute(text("""
                    CREATE TABLE milestone (
                        id SERIAL PRIMARY KEY,
                        gig_id INTEGER NOT NULL REFERENCES gig(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        amount FLOAT NOT NULL,
                        "order" INTEGER NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        due_date TIMESTAMP,
                        completed_at TIMESTAMP,
                        approved_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:  # SQLite
                db.session.execute(text("""
                    CREATE TABLE milestone (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        gig_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        description TEXT,
                        amount REAL NOT NULL,
                        "order" INTEGER NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        due_date DATETIME,
                        completed_at DATETIME,
                        approved_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (gig_id) REFERENCES gig(id) ON DELETE CASCADE
                    )
                """))

            print("   ✅ Created milestone table")
        else:
            print("ℹ️  milestone table already exists")

        # Create milestone_payment table if it doesn't exist
        if not check_table_exists('milestone_payment'):
            print("➕ Creating milestone_payment table...")

            db_type = db.engine.dialect.name

            if db_type == 'postgresql':
                db.session.execute(text("""
                    CREATE TABLE milestone_payment (
                        id SERIAL PRIMARY KEY,
                        milestone_id INTEGER NOT NULL REFERENCES milestone(id) ON DELETE CASCADE,
                        escrow_number VARCHAR(50) UNIQUE NOT NULL,
                        gig_id INTEGER NOT NULL REFERENCES gig(id) ON DELETE CASCADE,
                        client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                        freelancer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                        amount FLOAT NOT NULL,
                        platform_fee FLOAT DEFAULT 0.0,
                        net_amount FLOAT NOT NULL,
                        status VARCHAR(30) DEFAULT 'pending',
                        payment_reference VARCHAR(100),
                        payment_gateway VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        funded_at TIMESTAMP,
                        released_at TIMESTAMP,
                        refunded_at TIMESTAMP
                    )
                """))
            else:  # SQLite
                db.session.execute(text("""
                    CREATE TABLE milestone_payment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        milestone_id INTEGER NOT NULL,
                        escrow_number VARCHAR(50) UNIQUE NOT NULL,
                        gig_id INTEGER NOT NULL,
                        client_id INTEGER NOT NULL,
                        freelancer_id INTEGER NOT NULL,
                        amount REAL NOT NULL,
                        platform_fee REAL DEFAULT 0.0,
                        net_amount REAL NOT NULL,
                        status VARCHAR(30) DEFAULT 'pending',
                        payment_reference VARCHAR(100),
                        payment_gateway VARCHAR(50),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        funded_at DATETIME,
                        released_at DATETIME,
                        refunded_at DATETIME,
                        FOREIGN KEY (milestone_id) REFERENCES milestone(id) ON DELETE CASCADE,
                        FOREIGN KEY (gig_id) REFERENCES gig(id) ON DELETE CASCADE,
                        FOREIGN KEY (client_id) REFERENCES user(id) ON DELETE CASCADE,
                        FOREIGN KEY (freelancer_id) REFERENCES user(id) ON DELETE CASCADE
                    )
                """))

            print("   ✅ Created milestone_payment table")
        else:
            print("ℹ️  milestone_payment table already exists")

        # Create indexes
        print("➕ Creating indexes...")

        # Indexes for milestone table
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_milestone_gig_id ON milestone(gig_id)"))
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_milestone_status ON milestone(status)"))

        # Indexes for milestone_payment table
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_milestone_payment_milestone_id ON milestone_payment(milestone_id)"))
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_milestone_payment_gig_id ON milestone_payment(gig_id)"))
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_milestone_payment_status ON milestone_payment(status)"))
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_milestone_payment_escrow_number ON milestone_payment(escrow_number)"))

        # Index for gig payment_type
        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_gig_payment_type ON gig(payment_type)"))

        print("   ✅ Created indexes")

        # Commit all changes
        db.session.commit()
        print("\n" + "-" * 60)
        print("✅ Migration completed successfully!")

        return True

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main migration entry point"""
    print("=" * 60)
    print("GigHala Milestone Payment Migration")
    print("=" * 60)

    try:
        success = add_milestone_payment_support()

        if success:
            print("\n✅ Migration completed successfully!")
            print("\n📝 Summary:")
            print("   - Added payment_type field to gig table")
            print("   - Created milestone table for tracking milestones")
            print("   - Created milestone_payment table for escrow payments")
            print("   - Created necessary indexes for performance")
            print("\n🚀 Milestone payment feature is now ready to use!")
            return 0
        else:
            print("\n❌ Migration failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
