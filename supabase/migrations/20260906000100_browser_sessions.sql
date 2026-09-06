-- Persist revocable opaque browser sessions. Only token digests are stored.
BEGIN;
SELECT pg_advisory_xact_lock(1279873875, 3);

CREATE TABLE lms.browser_sessions (
    token_hash text PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    user_id bigint NOT NULL REFERENCES lms.users(id) ON DELETE CASCADE,
    csrf_hash text NOT NULL CHECK (csrf_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    idle_expires_at timestamptz NOT NULL,
    absolute_expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (last_seen_at >= created_at),
    CHECK (idle_expires_at > created_at),
    CHECK (absolute_expires_at > created_at),
    CHECK (idle_expires_at <= absolute_expires_at),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at)
);
CREATE INDEX browser_sessions_user_active_idx
    ON lms.browser_sessions(user_id, absolute_expires_at)
    WHERE revoked_at IS NULL;
CREATE INDEX browser_sessions_expiry_idx
    ON lms.browser_sessions(absolute_expires_at);

CREATE FUNCTION lms.revoke_sessions_for_inactive_user() RETURNS trigger
LANGUAGE plpgsql
SET search_path = lms, pg_catalog
AS $$
BEGIN
    IF OLD.is_active AND NOT NEW.is_active THEN
        UPDATE lms.browser_sessions
        SET revoked_at = CURRENT_TIMESTAMP
        WHERE user_id = NEW.id AND revoked_at IS NULL;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_revoke_sessions_after_deactivation
AFTER UPDATE OF is_active ON lms.users
FOR EACH ROW EXECUTE FUNCTION lms.revoke_sessions_for_inactive_user();

ALTER TABLE lms.browser_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON lms.browser_sessions FROM PUBLIC;
REVOKE ALL ON FUNCTION lms.revoke_sessions_for_inactive_user() FROM PUBLIC;

INSERT INTO lms.schema_version(version) VALUES (3);
COMMIT;
