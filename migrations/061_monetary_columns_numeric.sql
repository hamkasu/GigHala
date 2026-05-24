-- ============================================================
-- Migration 061: Convert monetary Float columns to NUMERIC(12,2)
-- ============================================================
-- Environments bootstrapped via db.create_all() (rather than the
-- original setup_billing_system.sql) have these columns as
-- DOUBLE PRECISION (float8).  This migration converts them to
-- NUMERIC(12,2) so all monetary values are stored with exact
-- decimal precision.
--
-- The migration is IDEMPOTENT: each ALTER is wrapped in a DO $$
-- block that checks the current column type first; if the column
-- is already NUMERIC it is left untouched.
--
-- SQLite: ALTER COLUMN TYPE is not supported, but SQLite stores
-- all NUMERIC values with exact affinity anyway, so no action is
-- needed in SQLite-based development environments.
-- ============================================================

DO $$
DECLARE
    col_type text;

    -- helper: alter a column to NUMERIC(12,2) only when it is currently DOUBLE PRECISION
    PROCEDURE convert_if_float(p_table text, p_column text) AS $$
    BEGIN
        SELECT data_type
          INTO col_type
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name   = p_table
           AND column_name  = p_column;

        IF col_type = 'double precision' THEN
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN %I TYPE NUMERIC(12,2) USING %I::NUMERIC(12,2)',
                p_table, p_column, p_column
            );
            RAISE NOTICE 'Converted %.% from DOUBLE PRECISION to NUMERIC(12,2)', p_table, p_column;
        ELSE
            RAISE NOTICE 'Skipped %.%: already %', p_table, p_column, col_type;
        END IF;
    END;
    $$ LANGUAGE plpgsql;

BEGIN
    -- user
    CALL convert_if_float('user', 'total_earnings');

    -- referral
    CALL convert_if_float('referral', 'bonus_amount');

    -- gig
    CALL convert_if_float('gig', 'budget_min');
    CALL convert_if_float('gig', 'budget_max');
    CALL convert_if_float('gig', 'approved_budget');
    CALL convert_if_float('gig', 'agreed_amount');

    -- gig_worker
    CALL convert_if_float('gig_worker', 'agreed_amount');

    -- application
    CALL convert_if_float('application', 'proposed_price');

    -- transaction
    CALL convert_if_float('transaction', 'amount');
    CALL convert_if_float('transaction', 'commission');
    CALL convert_if_float('transaction', 'net_amount');
    CALL convert_if_float('transaction', 'socso_amount');

    -- micro_task
    CALL convert_if_float('micro_task', 'reward');

    -- wallet
    CALL convert_if_float('wallet', 'balance');
    CALL convert_if_float('wallet', 'held_balance');
    CALL convert_if_float('wallet', 'total_earned');
    CALL convert_if_float('wallet', 'total_spent');

    -- invoice
    CALL convert_if_float('invoice', 'amount');
    CALL convert_if_float('invoice', 'platform_fee');
    CALL convert_if_float('invoice', 'tax_amount');
    CALL convert_if_float('invoice', 'total_amount');

    -- receipt
    CALL convert_if_float('receipt', 'amount');
    CALL convert_if_float('receipt', 'platform_fee');
    CALL convert_if_float('receipt', 'total_amount');

    -- payout
    CALL convert_if_float('payout', 'amount');
    CALL convert_if_float('payout', 'fee');
    CALL convert_if_float('payout', 'socso_amount');
    CALL convert_if_float('payout', 'net_amount');

    -- payment_history
    CALL convert_if_float('payment_history', 'amount');
    CALL convert_if_float('payment_history', 'socso_amount');
    CALL convert_if_float('payment_history', 'balance_before');
    CALL convert_if_float('payment_history', 'balance_after');

    -- escrow
    CALL convert_if_float('escrow', 'amount');
    CALL convert_if_float('escrow', 'platform_fee');
    CALL convert_if_float('escrow', 'net_amount');
    CALL convert_if_float('escrow', 'refunded_amount');

    -- milestone
    CALL convert_if_float('milestone', 'amount');

    -- milestone_payment
    CALL convert_if_float('milestone_payment', 'amount');
    CALL convert_if_float('milestone_payment', 'platform_fee');
    CALL convert_if_float('milestone_payment', 'net_amount');

    -- socso_contribution
    CALL convert_if_float('socso_contribution', 'gross_amount');
    CALL convert_if_float('socso_contribution', 'platform_commission');
    CALL convert_if_float('socso_contribution', 'net_earnings');
    CALL convert_if_float('socso_contribution', 'socso_amount');
    CALL convert_if_float('socso_contribution', 'final_payout');

    -- worker_specialization
    CALL convert_if_float('worker_specialization', 'base_hourly_rate');
    CALL convert_if_float('worker_specialization', 'base_fixed_rate');

    -- urgent_request
    CALL convert_if_float('urgent_request', 'budget_min');
    CALL convert_if_float('urgent_request', 'budget_max');
    CALL convert_if_float('urgent_request', 'priority_match_price');
    CALL convert_if_float('urgent_request', 'urgent_boost_price');
    CALL convert_if_float('urgent_request', 'total_addons_price');

    -- managed_solution_request
    CALL convert_if_float('managed_solution_request', 'budget_min');
    CALL convert_if_float('managed_solution_request', 'budget_max');

END $$;
