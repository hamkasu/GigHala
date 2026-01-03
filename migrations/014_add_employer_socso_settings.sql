-- Migration: Add Employer SOCSO Settings for Borang 8A
-- Description: Add employer information required for SOCSO Borang 8A monthly submission
-- Date: 2026-01-03

-- Insert employer SOCSO settings into SiteSettings table
-- These settings are required for generating Borang 8A monthly reports

INSERT INTO site_settings (key, value, description, updated_at)
VALUES
    ('socso_employer_code', '', 'SOCSO Employer Code (from PERKESO registration)', NOW()),
    ('socso_ssm_number', '', 'Company SSM/MyCoID Registration Number', NOW()),
    ('socso_company_name', 'GigHala Sdn Bhd', 'Registered Company Name for SOCSO', NOW()),
    ('socso_company_address', '', 'Company Registered Address for SOCSO Borang 8A', NOW()),
    ('socso_company_phone', '', 'Company Contact Phone Number', NOW()),
    ('socso_company_email', 'compliance@gighala.com', 'Company Email for SOCSO Correspondence', NOW()),
    ('socso_submission_reminder_enabled', 'true', 'Enable monthly SOCSO submission reminders (15th of each month)', NOW()),
    ('socso_last_submission_date', '', 'Last SOCSO Borang 8A submission date', NOW())
ON CONFLICT (key) DO NOTHING;
