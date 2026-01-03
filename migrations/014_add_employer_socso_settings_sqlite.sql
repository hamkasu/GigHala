-- Migration: Add Employer SOCSO Settings for Borang 8A (SQLite)
-- Description: Add employer information required for SOCSO Borang 8A monthly submission
-- Date: 2026-01-03

-- Insert employer SOCSO settings into SiteSettings table
-- These settings are required for generating Borang 8A monthly reports

INSERT OR IGNORE INTO site_settings (key, value, description, updated_at)
VALUES
    ('socso_employer_code', '', 'SOCSO Employer Code (from PERKESO registration)', datetime('now')),
    ('socso_ssm_number', '', 'Company SSM/MyCoID Registration Number', datetime('now')),
    ('socso_company_name', 'GigHala Sdn Bhd', 'Registered Company Name for SOCSO', datetime('now')),
    ('socso_company_address', '', 'Company Registered Address for SOCSO Borang 8A', datetime('now')),
    ('socso_company_phone', '', 'Company Contact Phone Number', datetime('now')),
    ('socso_company_email', 'compliance@gighala.com', 'Company Email for SOCSO Correspondence', datetime('now')),
    ('socso_submission_reminder_enabled', 'true', 'Enable monthly SOCSO submission reminders (15th of each month)', datetime('now')),
    ('socso_last_submission_date', '', 'Last SOCSO Borang 8A submission date', datetime('now'));
