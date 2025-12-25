-- Migration: Add SOCSO Registration Fields
-- Description: Add additional fields required for complete SOCSO registration under SESKSO (Gig Workers Bill 2025)
-- Date: 2025-12-25

-- Add SOCSO registration fields to User table
ALTER TABLE user ADD COLUMN date_of_birth DATE;
ALTER TABLE user ADD COLUMN gender VARCHAR(10);
ALTER TABLE user ADD COLUMN marital_status VARCHAR(20);
ALTER TABLE user ADD COLUMN nationality VARCHAR(50) DEFAULT 'Malaysian';
ALTER TABLE user ADD COLUMN race VARCHAR(50);
ALTER TABLE user ADD COLUMN address_line1 VARCHAR(255);
ALTER TABLE user ADD COLUMN address_line2 VARCHAR(255);
ALTER TABLE user ADD COLUMN postcode VARCHAR(10);
ALTER TABLE user ADD COLUMN city VARCHAR(100);
ALTER TABLE user ADD COLUMN state VARCHAR(100);
ALTER TABLE user ADD COLUMN country VARCHAR(100) DEFAULT 'Malaysia';
ALTER TABLE user ADD COLUMN self_employment_start_date DATE;
ALTER TABLE user ADD COLUMN monthly_income_range VARCHAR(50);
ALTER TABLE user ADD COLUMN socso_registration_date DATETIME;

-- Add indexes for common queries
CREATE INDEX idx_user_state ON user(state);
CREATE INDEX idx_user_city ON user(city);
CREATE INDEX idx_user_socso_registered ON user(socso_registered);
CREATE INDEX idx_user_socso_data_complete ON user(socso_data_complete);
