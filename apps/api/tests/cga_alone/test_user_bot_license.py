"""사용자별 서명 라이선스 한도에 대한 실제 PostgreSQL 회귀."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.api.routes import bots
from app.models import AdminLicense, Bot, User
from app.schemas.bot import BotCreateRequest
from app.services import license_policy
from tests.integration.test_bot_persistence_regression import _request, regression_actor, migrated_test_database


def limit(db, actor, value):
    record=db.scalar(select(AdminLicense).where(AdminLicense.organization_id==actor.organization_id,AdminLicense.status=='active'))
    payload=deepcopy(record.payload_json); payload.setdefault('limits',{})['bots']=value; record.payload_json=payload; db.flush(); return record


def create(db, actor, name):
    return bots.create_bot(BotCreateRequest(name=name),_request(),actor,db)


def test_licensed_two_is_per_user_and_not_hardcoded(regression_actor,db_session):
    a=regression_actor;limit(db_session,a,2)
    b=User(organization_id=a.organization_id,group_id=a.group_id,login_id='quota-'+uuid4().hex,password_hash='synthetic',name='두번째',status='active')
    db_session.add(b);db_session.flush()
    for actor in [a,b]:
        create(db_session,actor,'첫째');create(db_session,actor,'둘째')
        with pytest.raises(HTTPException) as denied:create(db_session,actor,'셋째')
        assert denied.value.status_code==403
    result=bots.get_bot_creation_policy(_request(),a,db_session)['data']
    assert result=={'limit':2,'used':2,'remaining':0,'allowed':False,'reason':'quota_reached'}


@pytest.mark.parametrize('value',[0,None,-1,True,'1'])
def test_zero_or_invalid_bot_limit_never_falls_back_to_one(regression_actor,db_session,value):
    limit(db_session,regression_actor,value)
    with pytest.raises(HTTPException) as denied:create(db_session,regression_actor,'거부')
    assert denied.value.status_code==403
    assert license_policy.get_bot_creation_policy(db_session,regression_actor.organization_id,regression_actor.id)['allowed'] is False


def test_deleted_bot_releases_licensed_slot(regression_actor,db_session):
    a=regression_actor;limit(db_session,a,1)
    first=create(db_session,a,'이전')['data']['id']; bot=db_session.get(Bot,UUID(first));bot.deleted_at=datetime.now(timezone.utc);db_session.commit()
    create(db_session,a,'새 봇')
    assert license_policy.get_bot_creation_policy(db_session,a.organization_id,a.id)['used']==1


def test_reduced_quota_keeps_existing_bots(regression_actor,db_session):
    a=regression_actor;limit(db_session,a,2);create(db_session,a,'첫째');create(db_session,a,'둘째');limit(db_session,a,1)
    result=license_policy.get_bot_creation_policy(db_session,a.organization_id,a.id)
    assert result['used']==2 and result['remaining']==0 and not result['allowed']
    with pytest.raises(HTTPException):create(db_session,a,'보존')
    assert len(db_session.scalars(select(Bot).where(Bot.created_by==a.id,Bot.deleted_at.is_(None))).all())==2


def test_missing_or_expired_license_blocks_creation(regression_actor,db_session):
    a=regression_actor;record=limit(db_session,a,1)
    payload=deepcopy(record.payload_json);payload['expires_at']=(date.today()-timedelta(days=1)).isoformat();record.payload_json=payload;db_session.flush()
    assert license_policy.get_bot_creation_policy(db_session,a.organization_id,a.id)['reason']=='license_expired'
    with pytest.raises(HTTPException):create(db_session,a,'만료')
    record.status='replaced';db_session.flush()
    assert license_policy.get_bot_creation_policy(db_session,a.organization_id,a.id)['reason']=='license_missing'



def test_license_display_uses_current_users_bot_count(regression_actor,db_session):
    from app.api.routes.admin import _serialize_license_status
    from app.models import Organization
    a=regression_actor;record=limit(db_session,a,1);create(db_session,a,'본인')
    b=User(organization_id=a.organization_id,group_id=a.group_id,login_id='display-'+uuid4().hex,password_hash='synthetic',name='다른 제작자',status='active')
    db_session.add(b);db_session.flush();create(db_session,b,'타인')
    response=_serialize_license_status(db_session,db_session.get(Organization,a.organization_id),record,creator_id=a.id)
    row=next(item for item in response.usage if item.key=='bots')
    assert (row.label,row.limit,row.used,row.remaining)==('사용자별 봇',1,1,0)


def change_revision(engine,revision):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from app.core.config import settings
    ini=Path(__file__).parents[2]/'alembic.ini';config=Config(str(ini));config.set_main_option('script_location',str(ini.parent/'alembic'));config.config_file_name=None
    previous=settings.database_url
    try:
        settings.database_url=engine.url.update_query_dict({'options':'-c lock_timeout=5000'}).render_as_string(hide_password=False)
        (command.upgrade if revision=='head' else command.downgrade)(config,revision)
    finally:settings.database_url=previous



def _clean_migration_actor(engine, actor_id, org_id, group_id):
    from sqlalchemy.orm import Session
    from sqlalchemy import delete, update
    from app.models import AuditLog, BotVersion, Group, Organization
    with Session(engine) as db:
        org=db.get(Organization,org_id);assert org.code.startswith('reg-')
        ids=db.scalars(select(Bot.id).where(Bot.created_by==actor_id)).all()
        db.execute(delete(AuditLog).where(AuditLog.actor_user_id==actor_id))
        db.execute(update(Bot).where(Bot.id.in_(ids)).values(active_version_id=None))
        db.execute(delete(BotVersion).where(BotVersion.bot_id.in_(ids)))
        db.execute(delete(Bot).where(Bot.id.in_(ids)))
        db.execute(delete(AdminLicense).where(AdminLicense.organization_id==org_id))
        db.execute(delete(User).where(User.id==actor_id))
        db.execute(delete(Group).where(Group.id==group_id))
        db.execute(delete(Organization).where(Organization.id==org_id));db.commit()


@pytest.mark.parametrize('quota',[1,2])
def test_migration_preserves_bots_and_guards_downgrade(test_engine,migrated_test_database,quota):
    from sqlalchemy import inspect,text
    from sqlalchemy.orm import Session
    with Session(test_engine,expire_on_commit=False) as db:
        actor=regression_actor.__wrapped__(db,migrated_test_database)
        actor_id,org_id,group_id=actor.id,actor.organization_id,actor.group_id
        limit(db,actor,quota)
        ids=[create(db,actor,'보존'+str(index))['data']['id'] for index in range(quota)]
        db.commit()
    try:
        if quota==2:
            with pytest.raises(RuntimeError,match='여러 봇'):
                change_revision(test_engine,'20261102_0032')
        else:
            change_revision(test_engine,'20261102_0032')
            assert any(i['name']=='uq_bots_live_creator' and i['unique'] for i in inspect(test_engine).get_indexes('bots'))
        change_revision(test_engine,'head')
        with Session(test_engine) as db:
            assert all(db.get(Bot,UUID(identifier)) is not None for identifier in ids)
        assert any(i['name']=='idx_bots_live_creator' and not i['unique'] for i in inspect(test_engine).get_indexes('bots'))
    finally:
        change_revision(test_engine,'head')
        _clean_migration_actor(test_engine,actor_id,org_id,group_id)



def test_license_replacement_serializes_with_creation(test_engine,migrated_test_database,monkeypatch):
    import json,time,base64
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from cryptography.hazmat.primitives import serialization,hashes
    from cryptography.hazmat.primitives.asymmetric import rsa,padding
    from app.api.routes import admin
    from app.core.config import settings
    from app.models import Organization
    from app.schemas.admin import LicenseApplyRequest
    with Session(test_engine,expire_on_commit=False) as db:
        actor=regression_actor.__wrapped__(db,migrated_test_database)
        actor_id,org_id,group_id=actor.id,actor.organization_id,actor.group_id
        limit(db,actor,2);create(db,actor,'이미 사용');db.commit()
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    payload={'license_id':'quota-race-'+uuid4().hex,'product':'CGA','customer':{'name':'QA'},'issued_at':date.today().isoformat(),'expires_at':'2027-12-31','limits':{'users':20,'bots':1,'apis':20}}
    signature=private.sign(admin._canonical_license_payload(payload),padding.PKCS1v15(),hashes.SHA256())
    document=json.dumps({'format':'cga-license','payload':payload,'signature':{'algorithm':'RS256','value':base64.urlsafe_b64encode(signature).decode().rstrip('=')}})
    monkeypatch.setattr(settings,'cga_license_public_key',public)
    monkeypatch.setattr(admin,'_get_default_organization',lambda db:db.get(Organization,org_id))
    monkeypatch.setattr(admin,'_require_admin_user',lambda db,user:None)
    locked,release=Event(),Event();verify=admin._verify_license_text
    def gated_verify(value):
        locked.set();assert release.wait(5);return verify(value)
    monkeypatch.setattr(admin,'_verify_license_text',gated_verify)
    def apply():
        with Session(test_engine) as db:
            return admin.apply_admin_license(LicenseApplyRequest(license_text=document),_request(),db,db.get(User,actor_id))
    def create_after():
        with Session(test_engine) as db:
            try:create(db,db.get(User,actor_id),'경합');return 200
            except HTTPException as error:db.rollback();return error.status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            applying=pool.submit(apply);assert locked.wait(5)
            creating=pool.submit(create_after)
            try:
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    with test_engine.connect() as connection:
                        waiting=connection.scalar(text("select count(*) from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and query like '%organizations%'"))
                    if waiting:break
                    time.sleep(.02)
                assert waiting,'Creation must wait on the same organization row'
                assert not creating.done()
            finally:release.set()
            assert applying.result(timeout=5)['data']['installed'] is True
            assert creating.result(timeout=5)==403
        with Session(test_engine) as db:
            assert len(db.scalars(select(Bot).where(Bot.created_by==actor_id)).all())==1
    finally:
        release.set();_clean_migration_actor(test_engine,actor_id,org_id,group_id)
