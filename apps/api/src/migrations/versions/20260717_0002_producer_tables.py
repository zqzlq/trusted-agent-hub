"""Create Producer-side persistence tables.

Revision ID: 20260717_0002
Revises: 20260716_0001
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_0002"
down_revision: str | None = "20260716_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    # ── review_records ──
    op.create_table(
        "review_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "version_id",
            sa.String(length=64),
            sa.ForeignKey("package_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column(
            "conclusion",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_review_records_version_id",
        "review_records",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_records_conclusion",
        "review_records",
        ["conclusion"],
        unique=False,
    )

    # ── scan_reports ──
    op.create_table(
        "scan_reports",
        sa.Column(
            "version_id",
            sa.String(length=64),
            sa.ForeignKey("package_versions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("scan_json", sa.JSON(), nullable=False),
        sa.Column("report_path", sa.String(length=512), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── audit_logs ──
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("operator_id", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_target", "audit_logs", ["target_type", "target_id"], unique=False
    )
    op.create_index(
        "ix_audit_logs_timestamp", "audit_logs", ["timestamp"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("scan_reports")
    op.drop_index("ix_review_records_conclusion", table_name="review_records")
    op.drop_index("ix_review_records_version_id", table_name="review_records")
    op.drop_table("review_records")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
