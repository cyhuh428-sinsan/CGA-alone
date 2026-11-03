"""봇 한도를 사용자별 라이선스로 제어하며 기존 자료는 보존한다."""
from alembic import op
import sqlalchemy as sa
revision = "20261103_0033"
down_revision = "20261102_0032"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("uq_bots_live_creator", table_name="bots")
    op.create_index("idx_bots_live_creator", "bots", ["created_by"], postgresql_where=sa.text("created_by IS NOT NULL AND deleted_at IS NULL"))


def downgrade():
    duplicate = op.get_bind().execute(sa.text("SELECT created_by FROM bots WHERE created_by IS NOT NULL AND deleted_at IS NULL GROUP BY created_by HAVING count(*) > 1 LIMIT 1")).first()
    if duplicate is not None:
        raise RuntimeError("여러 봇을 보유한 제작자가 있어 고유 제약을 복원할 수 없습니다. 기존 자료를 보존합니다.")
    op.drop_index("idx_bots_live_creator", table_name="bots")
    op.create_index("uq_bots_live_creator", "bots", ["created_by"], unique=True, postgresql_where=sa.text("created_by IS NOT NULL AND deleted_at IS NULL"))
