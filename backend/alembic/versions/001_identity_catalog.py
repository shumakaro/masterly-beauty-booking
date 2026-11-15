"""identity_catalog: frozen PostgreSQL DDL, independent of current ORM models."""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE TABLE users (
	email VARCHAR(254) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(10) NOT NULL,
	display_name VARCHAR(100) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_users PRIMARY KEY (id),
	CONSTRAINT ck_users_role CHECK (role IN ('CLIENT','MASTER','ADMIN')),
	CONSTRAINT ck_users_email CHECK (email = lower(trim(email)) AND length(email) > 3),
	CONSTRAINT ck_users_display_name CHECK (length(trim(display_name)) > 0),
	CONSTRAINT uq_users_email UNIQUE (email)
)
""")
    op.execute("""
CREATE TABLE master_profiles (
	user_id UUID NOT NULL,
	bio TEXT NOT NULL,
	timezone VARCHAR(64) NOT NULL,
	address VARCHAR(300) NOT NULL,
	avatar_url VARCHAR(1000),
	is_demo BOOLEAN DEFAULT false NOT NULL,
	is_published BOOLEAN DEFAULT false NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_master_profiles PRIMARY KEY (id),
	CONSTRAINT uq_master_profiles_user_id UNIQUE (user_id),
	CONSTRAINT fk_master_profiles_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)
""")
    op.execute("""
CREATE TABLE categories (
	slug VARCHAR(60) NOT NULL,
	name VARCHAR(100) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_categories PRIMARY KEY (id),
	CONSTRAINT ck_categories_name CHECK (length(trim(name)) > 0),
	CONSTRAINT uq_categories_slug UNIQUE (slug)
)
""")
    op.execute("""
CREATE TABLE services (
	category_id UUID NOT NULL,
	name VARCHAR(150) NOT NULL,
	description TEXT NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_services PRIMARY KEY (id),
	CONSTRAINT ck_services_name CHECK (length(trim(name)) > 0),
	CONSTRAINT fk_services_category_id FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT
)
""")
    op.execute("""
CREATE TABLE master_services (
	master_id UUID NOT NULL,
	service_id UUID NOT NULL,
	price NUMERIC(12, 2) NOT NULL,
	duration_minutes INTEGER NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_master_services PRIMARY KEY (id),
	CONSTRAINT uq_master_services_master_id UNIQUE (master_id, service_id),
	CONSTRAINT uq_master_services_id_master UNIQUE (id, master_id),
	CONSTRAINT ck_master_services_price CHECK (price >= 0),
	CONSTRAINT ck_master_services_duration CHECK (duration_minutes BETWEEN 15 AND 720 AND duration_minutes % 15 = 0),
	CONSTRAINT fk_master_services_master_id FOREIGN KEY(master_id) REFERENCES master_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_master_services_service_id FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE RESTRICT
)
""")
    op.execute("""
CREATE INDEX ix_master_services_search ON master_services (service_id, price)
""")
    op.execute("""
CREATE TABLE refresh_sessions (
	user_id UUID NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	family_id UUID NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_refresh_sessions PRIMARY KEY (id),
	CONSTRAINT ck_refresh_expiry CHECK (expires_at > created_at),
	CONSTRAINT fk_refresh_sessions_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	CONSTRAINT uq_refresh_sessions_token_hash UNIQUE (token_hash)
)
""")
    op.execute("""
CREATE INDEX ix_refresh_sessions_family_id ON refresh_sessions (family_id)
""")


def downgrade():
    op.drop_table("refresh_sessions")
    op.drop_table("master_services")
    op.drop_table("services")
    op.drop_table("categories")
    op.drop_table("master_profiles")
    op.drop_table("users")
