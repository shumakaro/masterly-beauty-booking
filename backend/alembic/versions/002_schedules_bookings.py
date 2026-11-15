"""schedules_bookings: frozen PostgreSQL DDL, independent of current ORM models."""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE EXTENSION IF NOT EXISTS btree_gist
""")
    op.execute("""
CREATE TABLE schedules (
	master_id UUID NOT NULL,
	weekday INTEGER NOT NULL,
	starts_local TIME WITHOUT TIME ZONE NOT NULL,
	ends_local TIME WITHOUT TIME ZONE NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_schedules PRIMARY KEY (id),
	CONSTRAINT ck_schedules_weekday CHECK (weekday BETWEEN 0 AND 6),
	CONSTRAINT ck_schedules_interval CHECK (starts_local < ends_local),
	CONSTRAINT ex_schedules_overlap EXCLUDE USING gist (master_id WITH =, weekday WITH =, int4range(EXTRACT(EPOCH FROM starts_local)::int, EXTRACT(EPOCH FROM ends_local)::int, '[)') WITH &&),
	CONSTRAINT fk_schedules_master_id FOREIGN KEY(master_id) REFERENCES master_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE schedule_exceptions (
	master_id UUID NOT NULL,
	local_date DATE NOT NULL,
	is_closed BOOLEAN NOT NULL,
	starts_local TIME WITHOUT TIME ZONE,
	ends_local TIME WITHOUT TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_schedule_exceptions PRIMARY KEY (id),
	CONSTRAINT uq_schedule_exceptions_master_id UNIQUE (master_id, local_date),
	CONSTRAINT ck_schedule_exceptions_interval CHECK ((is_closed AND starts_local IS NULL AND ends_local IS NULL) OR (NOT is_closed AND starts_local IS NOT NULL AND ends_local IS NOT NULL AND starts_local < ends_local)),
	CONSTRAINT fk_schedule_exceptions_master_id FOREIGN KEY(master_id) REFERENCES master_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE bookings (
	client_id UUID NOT NULL,
	master_id UUID NOT NULL,
	master_service_id UUID NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	status VARCHAR(12) NOT NULL,
	price_snapshot NUMERIC(12, 2) NOT NULL,
	duration_snapshot INTEGER NOT NULL,
	service_name_snapshot VARCHAR(150) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	cancelled_by UUID,
	cancellation_reason VARCHAR(500),
	idempotency_key UUID NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_bookings PRIMARY KEY (id),
	CONSTRAINT fk_bookings_offer_owner FOREIGN KEY(master_service_id, master_id) REFERENCES master_services (id, master_id) ON DELETE RESTRICT,
	CONSTRAINT uq_bookings_client_id UNIQUE (client_id, idempotency_key),
	CONSTRAINT ck_bookings_status CHECK (status IN ('CONFIRMED','CANCELLED','COMPLETED')),
	CONSTRAINT ck_bookings_interval CHECK (starts_at < ends_at),
	CONSTRAINT ck_bookings_price CHECK (price_snapshot >= 0),
	CONSTRAINT ck_bookings_duration CHECK (duration_snapshot BETWEEN 15 AND 720 AND duration_snapshot % 15 = 0),
	CONSTRAINT ck_bookings_end CHECK (ends_at = starts_at + duration_snapshot * INTERVAL '1 minute'),
	CONSTRAINT ck_bookings_currency CHECK (currency = 'KZT'),
	CONSTRAINT ck_bookings_cancellation CHECK ((status = 'CANCELLED' AND cancelled_by IS NOT NULL) OR (status <> 'CANCELLED' AND cancelled_by IS NULL AND cancellation_reason IS NULL)),
	CONSTRAINT ex_bookings_overlap EXCLUDE USING gist (master_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status = 'CONFIRMED'),
	CONSTRAINT fk_bookings_client_id FOREIGN KEY(client_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_bookings_master_id FOREIGN KEY(master_id) REFERENCES master_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_bookings_cancelled_by FOREIGN KEY(cancelled_by) REFERENCES users (id) ON DELETE RESTRICT
)
""")
    op.execute("""
CREATE INDEX ix_bookings_client_start ON bookings (client_id, starts_at DESC)
""")
    op.execute("""
CREATE INDEX ix_bookings_master_start ON bookings (master_id, starts_at)
""")


def downgrade():
    op.drop_table("bookings")
    op.drop_table("schedule_exceptions")
    op.drop_table("schedules")
