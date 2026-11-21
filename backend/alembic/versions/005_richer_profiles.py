"""Профили, описание работ и фотографии отзывов без изменения существующих записей."""

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "master_profiles",
        sa.Column("specialization", sa.String(160), nullable=False, server_default=""),
    )
    op.add_column(
        "master_profiles",
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_master_experience", "master_profiles", "experience_years BETWEEN 0 AND 80"
    )
    op.add_column(
        "portfolio_items", sa.Column("title", sa.String(150), nullable=False, server_default="")
    )
    op.add_column(
        "portfolio_items", sa.Column("description", sa.Text(), nullable=False, server_default="")
    )
    op.add_column("portfolio_items", sa.Column("category_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_portfolio_items_category_id",
        "portfolio_items",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("reviews", sa.Column("photo_url", sa.String(1000), nullable=True))
    op.add_column(
        "reviews", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade():
    op.drop_column("reviews", "is_demo")
    op.drop_column("reviews", "photo_url")
    op.drop_constraint("fk_portfolio_items_category_id", "portfolio_items", type_="foreignkey")
    op.drop_column("portfolio_items", "category_id")
    op.drop_column("portfolio_items", "description")
    op.drop_column("portfolio_items", "title")
    op.drop_constraint("ck_master_experience", "master_profiles", type_="check")
    op.drop_column("master_profiles", "experience_years")
    op.drop_column("master_profiles", "specialization")
