-- Add an explicit processing state so concurrent HTTP requests can claim work atomically.
BEGIN;
SELECT pg_advisory_xact_lock(1279873875, 2);

ALTER TABLE lms.idempotency_records
    ALTER COLUMN response DROP NOT NULL,
    ALTER COLUMN response_status DROP NOT NULL,
    ADD COLUMN state text NOT NULL DEFAULT 'completed'
        CHECK (state IN ('processing', 'completed')),
    ADD COLUMN owner_token text;

ALTER TABLE lms.idempotency_records
    ADD CONSTRAINT idempotency_state_payload_ck CHECK (
        (state = 'processing' AND owner_token IS NOT NULL
            AND response IS NULL AND response_status IS NULL)
        OR
        (state = 'completed' AND owner_token IS NULL
            AND response IS NOT NULL AND response_status IS NOT NULL)
    );

INSERT INTO lms.schema_version(version) VALUES (2);
COMMIT;
