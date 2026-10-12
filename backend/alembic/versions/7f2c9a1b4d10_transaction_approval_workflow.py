"""transaction approval workflow

Ergänzt den Freigabe-Workflow auf ``transactions``, der im Modell vorhanden, aber
noch nie migriert wurde: ``approval_status``, ``approved_by_id``, ``approved_at``
und ``review_note``.

Revision ID: 7f2c9a1b4d10
Revises: 03c525fc6e2f
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f2c9a1b4d10"
down_revision: Union[str, None] = "03c525fc6e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "approval_status",
                sa.Enum(
                    "submitted", "approved", "rejected",
                    name="approvalstatus", native_enum=False, length=40,
                ),
                nullable=False,
                server_default="approved",
            )
        )
        batch_op.add_column(sa.Column("approved_by_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("review_note", sa.String(length=300), nullable=True))
        batch_op.create_foreign_key(
            "fk_transactions_approved_by_id_users", "users", ["approved_by_id"], ["id"]
        )
        batch_op.create_index(batch_op.f("ix_transactions_approval_status"), ["approval_status"])


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_approval_status"))
        batch_op.drop_constraint("fk_transactions_approved_by_id_users", type_="foreignkey")
        batch_op.drop_column("review_note")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approved_by_id")
        batch_op.drop_column("approval_status")
