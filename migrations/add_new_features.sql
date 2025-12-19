-- GigHala Database Migration: New Features
-- Run these queries to add support for:
-- 1. Rating & Review System (already exists)
-- 2. Profile Portfolios
-- 3. Real-time Chat/Messaging
-- 4. PWA Notifications
-- 5. Identity Verification
-- 6. Dispute Resolution
-- 7. Escrow Milestone Payments

-- ============================================
-- 1. PORTFOLIO ITEMS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS portfolio_item (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    image_filename VARCHAR(255),
    image_path VARCHAR(500),
    external_url VARCHAR(500),
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_portfolio_item_user_id ON portfolio_item(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_item_category ON portfolio_item(category);

-- ============================================
-- 2. CHAT/MESSAGING TABLES
-- ============================================
CREATE TABLE IF NOT EXISTS conversation (
    id SERIAL PRIMARY KEY,
    gig_id INTEGER REFERENCES gig(id),
    participant_1_id INTEGER NOT NULL REFERENCES "user"(id),
    participant_2_id INTEGER NOT NULL REFERENCES "user"(id),
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived_by_1 BOOLEAN DEFAULT FALSE,
    is_archived_by_2 BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_conversation_participant_1 ON conversation(participant_1_id);
CREATE INDEX IF NOT EXISTS idx_conversation_participant_2 ON conversation(participant_2_id);
CREATE INDEX IF NOT EXISTS idx_conversation_gig_id ON conversation(gig_id);
CREATE INDEX IF NOT EXISTS idx_conversation_last_message ON conversation(last_message_at DESC);

CREATE TABLE IF NOT EXISTS message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id),
    sender_id INTEGER NOT NULL REFERENCES "user"(id),
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    attachment_url VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_message_conversation_id ON message(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_sender_id ON message(sender_id);
CREATE INDEX IF NOT EXISTS idx_message_created_at ON message(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_message_is_read ON message(is_read);

-- ============================================
-- 3. NOTIFICATION TABLES
-- ============================================
CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    link VARCHAR(500),
    related_id INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    is_push_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_user_id ON notification(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_is_read ON notification(is_read);
CREATE INDEX IF NOT EXISTS idx_notification_created_at ON notification(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_type ON notification(notification_type);

CREATE TABLE IF NOT EXISTS notification_preference (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) UNIQUE,
    push_enabled BOOLEAN DEFAULT TRUE,
    push_subscription TEXT,
    email_new_gig BOOLEAN DEFAULT TRUE,
    email_message BOOLEAN DEFAULT TRUE,
    email_payment BOOLEAN DEFAULT TRUE,
    email_review BOOLEAN DEFAULT TRUE,
    push_new_gig BOOLEAN DEFAULT TRUE,
    push_message BOOLEAN DEFAULT TRUE,
    push_payment BOOLEAN DEFAULT TRUE,
    push_review BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_preference_user_id ON notification_preference(user_id);

-- ============================================
-- 4. IDENTITY VERIFICATION TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS identity_verification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    ic_number VARCHAR(12) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    ic_front_image VARCHAR(500),
    ic_back_image VARCHAR(500),
    selfie_image VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    rejection_reason TEXT,
    verified_at TIMESTAMP,
    verified_by INTEGER REFERENCES "user"(id),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_identity_verification_user_id ON identity_verification(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_verification_status ON identity_verification(status);
CREATE INDEX IF NOT EXISTS idx_identity_verification_ic_number ON identity_verification(ic_number);

-- ============================================
-- 5. DISPUTE RESOLUTION TABLES
-- ============================================
CREATE TABLE IF NOT EXISTS dispute (
    id SERIAL PRIMARY KEY,
    dispute_number VARCHAR(50) UNIQUE NOT NULL,
    gig_id INTEGER NOT NULL REFERENCES gig(id),
    escrow_id INTEGER REFERENCES escrow(id),
    filed_by_id INTEGER NOT NULL REFERENCES "user"(id),
    against_id INTEGER NOT NULL REFERENCES "user"(id),
    dispute_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    evidence_files TEXT,
    status VARCHAR(30) DEFAULT 'open',
    resolution TEXT,
    resolution_type VARCHAR(30),
    resolved_by INTEGER REFERENCES "user"(id),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispute_gig_id ON dispute(gig_id);
CREATE INDEX IF NOT EXISTS idx_dispute_escrow_id ON dispute(escrow_id);
CREATE INDEX IF NOT EXISTS idx_dispute_filed_by ON dispute(filed_by_id);
CREATE INDEX IF NOT EXISTS idx_dispute_against ON dispute(against_id);
CREATE INDEX IF NOT EXISTS idx_dispute_status ON dispute(status);
CREATE INDEX IF NOT EXISTS idx_dispute_number ON dispute(dispute_number);

CREATE TABLE IF NOT EXISTS dispute_message (
    id SERIAL PRIMARY KEY,
    dispute_id INTEGER NOT NULL REFERENCES dispute(id),
    sender_id INTEGER NOT NULL REFERENCES "user"(id),
    message TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    attachments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispute_message_dispute_id ON dispute_message(dispute_id);
CREATE INDEX IF NOT EXISTS idx_dispute_message_sender_id ON dispute_message(sender_id);

-- ============================================
-- 6. ESCROW MILESTONE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS milestone (
    id SERIAL PRIMARY KEY,
    escrow_id INTEGER NOT NULL REFERENCES escrow(id),
    gig_id INTEGER NOT NULL REFERENCES gig(id),
    milestone_number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    amount NUMERIC(10, 2) NOT NULL,
    percentage NUMERIC(5, 2),
    due_date TIMESTAMP,
    status VARCHAR(30) DEFAULT 'pending',
    work_submitted BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMP,
    approved_at TIMESTAMP,
    released_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_milestone_escrow_id ON milestone(escrow_id);
CREATE INDEX IF NOT EXISTS idx_milestone_gig_id ON milestone(gig_id);
CREATE INDEX IF NOT EXISTS idx_milestone_status ON milestone(status);

-- ============================================
-- 7. ADD VERIFICATION FIELDS TO USER TABLE (if not exist)
-- ============================================
-- These may already exist, so we use DO block to handle errors gracefully

DO $$ 
BEGIN
    -- Add identity_verified column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'identity_verified') THEN
        ALTER TABLE "user" ADD COLUMN identity_verified BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- Add identity_verified_at column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'identity_verified_at') THEN
        ALTER TABLE "user" ADD COLUMN identity_verified_at TIMESTAMP;
    END IF;
    
    -- Add verification_level column if not exists (basic, verified, premium)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'verification_level') THEN
        ALTER TABLE "user" ADD COLUMN verification_level VARCHAR(20) DEFAULT 'basic';
    END IF;
END $$;

-- ============================================
-- SUMMARY OF NEW TABLES CREATED:
-- ============================================
-- 1. portfolio_item - For freelancer portfolio showcase
-- 2. conversation - For chat conversations between users
-- 3. message - For individual chat messages
-- 4. notification - For user notifications
-- 5. notification_preference - For notification settings
-- 6. identity_verification - For IC/MyKad verification
-- 7. dispute - For dispute cases
-- 8. dispute_message - For messages within disputes
-- 9. milestone - For escrow milestone payments

-- Run this migration using:
-- psql $DATABASE_URL -f migrations/add_new_features.sql
