-- Migration: Add PERKESO Profile Fields
-- Description: Adds the fields required to call PERKESO's Update User Details endpoint
--              (PATCH /api/v1/obs/{ic_no}). Without these, only basic registration
--              (register_user) works — the full profile sync cannot be performed.
-- API Reference: GIG Workers API Documentation v2.1 (PERKESO), Sections 5.2.4–5.2.7
-- Date: 2026-05-08

-- -----------------------------------------------------------------------
-- User table: IC type (required for registration, Section 6.3)
-- -----------------------------------------------------------------------

-- IC type code: B = New MyKad, L = Old IC, PR = Permanent Resident
ALTER TABLE user ADD COLUMN ic_type VARCHAR(5) DEFAULT 'B';

-- -----------------------------------------------------------------------
-- User table: Person status (required for Update User Details, Section 6.6)
-- -----------------------------------------------------------------------

-- Person status: P = Public, RP = Retired Police, RM = Retired Military, O = Others
ALTER TABLE user ADD COLUMN person_status VARCHAR(5) DEFAULT 'P';

-- -----------------------------------------------------------------------
-- User table: Next of KIN (required for Update User Details, Section 5.2.7)
-- -----------------------------------------------------------------------

ALTER TABLE user ADD COLUMN next_of_kin_name VARCHAR(255);
ALTER TABLE user ADD COLUMN next_of_kin_mobile_no VARCHAR(20);

-- Relation codes: W = Wife, H = Husband, C = Children, M = Mother,
--                 F = Father, S = Sibling, O = Others
ALTER TABLE user ADD COLUMN next_of_kin_relation VARCHAR(5);

-- -----------------------------------------------------------------------
-- User table: Optional contact (Section 5.2.5)
-- -----------------------------------------------------------------------

ALTER TABLE user ADD COLUMN house_phone_no VARCHAR(20);

-- -----------------------------------------------------------------------
-- User table: PERKESO state/city integer IDs (Section 5.2.10)
-- GigHala stores state/city as text; PERKESO requires its own integer IDs
-- obtained from GET /api/v1/states. These are populated on first sync.
-- -----------------------------------------------------------------------

ALTER TABLE user ADD COLUMN perkeso_state_id INTEGER;
ALTER TABLE user ADD COLUMN perkeso_city_id INTEGER;

-- -----------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------

CREATE INDEX idx_user_ic_type ON user(ic_type);
CREATE INDEX idx_user_person_status ON user(person_status);
CREATE INDEX idx_user_perkeso_state_id ON user(perkeso_state_id);
