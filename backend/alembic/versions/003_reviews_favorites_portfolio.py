"""reviews_favorites_portfolio: frozen PostgreSQL DDL, independent of current ORM models."""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE TABLE reviews (
	booking_id UUID NOT NULL,
	rating INTEGER NOT NULL,
	text TEXT NOT NULL,
	is_visible BOOLEAN DEFAULT true NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_reviews PRIMARY KEY (id),
	CONSTRAINT ck_reviews_rating CHECK (rating BETWEEN 1 AND 5),
	CONSTRAINT uq_reviews_booking_id UNIQUE (booking_id),
	CONSTRAINT fk_reviews_booking_id FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE RESTRICT
)
""")
    op.execute("""
CREATE TABLE favorites (
	client_id UUID NOT NULL,
	master_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_favorites PRIMARY KEY (client_id, master_id),
	CONSTRAINT fk_favorites_client_id FOREIGN KEY(client_id) REFERENCES users (id) ON DELETE CASCADE,
	CONSTRAINT fk_favorites_master_id FOREIGN KEY(master_id) REFERENCES master_profiles (id) ON DELETE CASCADE
)
""")
    op.execute("""
CREATE TABLE portfolio_items (
	master_id UUID NOT NULL,
	url VARCHAR(1000) NOT NULL,
	alt_text VARCHAR(300) NOT NULL,
	source_url VARCHAR(1000),
	license VARCHAR(150) NOT NULL,
	position INTEGER NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_portfolio_items PRIMARY KEY (id),
	CONSTRAINT ck_portfolio_position CHECK (position >= 0),
	CONSTRAINT fk_portfolio_items_master_id FOREIGN KEY(master_id) REFERENCES master_profiles (id) ON DELETE CASCADE
)
""")


def downgrade():
    op.drop_table("portfolio_items")
    op.drop_table("favorites")
    op.drop_table("reviews")
