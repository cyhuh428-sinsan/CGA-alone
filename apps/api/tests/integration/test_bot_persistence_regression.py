"""봇 생성 및 버전 저장의 DB 통합 회귀 테스트.

이 파일은 AIDOT_TEST_DATABASE_URL이 지정된 전용 테스트 DB에서만 실행한다.
운영 기본 DB URL과 동일한 값이면 안전을 위해 실패하도록 한다.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Request
from sqlalchemy import select

from app.api.routes.bots import create_bot, create_version
from app.core.config import settings
from app.models import AdminLicense, Bot, BotVersion, Group, Organization, User
from app.schemas.bot import BotCreateRequest, VersionCreateRequest


def _request() -> Request:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/bots",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 1),
            "root_path": "",
            "http_version": "1.1",
        }
    )
    request.state.request_id = f"regression-{uuid4()}"
    return request


@pytest.fixture(scope="session")
def migrated_test_database(test_engine):
    """전용 테스트 DB에 현재 마이그레이션을 적용한다."""
    test_url = test_engine.url.render_as_string(hide_password=False)
    production_url = str(settings.sqlalchemy_database_url)
    if test_url == production_url:
        raise RuntimeError("AIDOT_TEST_DATABASE_URL은 운영 DB URL과 달라야 합니다.")

    previous_url = settings.database_url
    settings.database_url = test_url
    try:
        alembic_ini = Path(__file__).parents[2] / "alembic.ini"
        config = Config(str(alembic_ini))
        config.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
        config.config_file_name = None
        command.upgrade(config, "head")
    finally:
        settings.database_url = previous_url
    return test_engine


@pytest.fixture
def regression_actor(db_session, migrated_test_database):
    suffix = uuid4().hex[:12]
    organization = Organization(name=f"회귀 조직 {suffix}", code=f"reg-{suffix}")
    db_session.add(organization)
    db_session.flush()

    group = Group(
        organization_id=organization.id,
        code=f"reg-group-{suffix}",
        name="회귀 테스트 그룹",
    )
    db_session.add(group)
    db_session.flush()

    user = User(
        organization_id=organization.id,
        group_id=group.id,
        login_id=f"reg-{suffix}",
        password_hash="regression-test-password-hash",
        name="회귀 테스트 사용자",
        email=f"reg-{suffix}@example.invalid",
        status="active",
    )
    db_session.add(user)
    db_session.flush()

    license_record = AdminLicense(
        organization_id=organization.id,
        license_id=f"license-{suffix}",
        product="Aidot",
        customer_name="회귀 테스트 고객",
        issued_at_text=date.today().isoformat(),
        expires_at_text=(date.today() + timedelta(days=30)).isoformat(),
        status="active",
        license_text="regression-test-license",
        signature_value="regression-test-signature",
        payload_json={"expires_at": (date.today() + timedelta(days=30)).isoformat(), "limits": {"users": 100, "bots": 100, "apis": 100}},
        applied_by=user.id,
    )
    db_session.add(license_record)
    db_session.commit()
    return user


def test_create_bot_persists_initial_version(regression_actor, db_session):
    result = create_bot(
        BotCreateRequest(name="회귀 테스트 봇"),
        _request(),
        regression_actor,
        db_session,
    )

    bot_id = result["data"]["id"]
    bot = db_session.scalar(select(Bot).where(Bot.id == bot_id))
    version = db_session.scalar(select(BotVersion).where(BotVersion.bot_id == bot_id))

    assert bot is not None
    assert bot.name == "회귀 테스트 봇"
    assert version is not None
    assert version.version_no == 1
    assert version.status == "testing"


def test_create_version_persists_next_version(regression_actor, db_session):
    created = create_bot(
        BotCreateRequest(name="버전 회귀 테스트 봇"),
        _request(),
        regression_actor,
        db_session,
    )
    bot_id = created["data"]["id"]

    result = create_version(
        bot_id,
        VersionCreateRequest(name="두 번째 버전", comment="회귀 확인"),
        _request(),
        regression_actor,
        db_session,
    )

    version_id = result["data"]["id"]
    version = db_session.scalar(select(BotVersion).where(BotVersion.id == version_id))
    versions = db_session.scalars(
        select(BotVersion).where(BotVersion.bot_id == bot_id).order_by(BotVersion.version_no)
    ).all()

    assert version is not None
    assert [item.version_no for item in versions] == [1, 2]
    assert version.name == "두 번째 버전"
    assert version.comment == "회귀 확인"
