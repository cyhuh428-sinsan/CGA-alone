from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AdminLicense, Bot, BotVersion, Organization, User

LicenseResource = Literal["users", "bots", "apis"]
_UNSET = object()

LICENSE_RESOURCE_LABELS: dict[LicenseResource, str] = {
    "users": "사용자",
    "bots": "사용자별 봇",
    "apis": "API",
}


def parse_license_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="라이선스 날짜 형식이 올바르지 않습니다.",
        ) from exc


def get_current_license(db: Session, organization_id: UUID) -> AdminLicense | None:
    return db.scalar(
        select(AdminLicense)
        .where(
            AdminLicense.organization_id == organization_id,
            AdminLicense.status == "active",
        )
        .order_by(AdminLicense.updated_at.desc())
    )


def _license_payload(record: AdminLicense | None) -> dict[str, object] | None:
    if record is None:
        return None
    payload = record.payload_json or {}
    return payload if isinstance(payload, dict) else None


def _license_limits(payload: dict[str, object] | None) -> dict[str, int]:
    raw_limits = payload.get("limits") if payload else None
    if not isinstance(raw_limits, dict):
        return {}
    limits: dict[str, int] = {}
    for key in LICENSE_RESOURCE_LABELS:
        value = raw_limits.get(key)
        if isinstance(value, int):
            limits[key] = value
    return limits


def _license_api_asset_key(api_asset: dict[str, object]) -> str | None:
    for key in ("id", "apiId", "name", "baseUrl"):
        value = api_asset.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def iter_api_assets(value: object):
    if isinstance(value, dict):
        for key in ("apis", "api_assets", "apiAssets"):
            assets = value.get(key)
            if isinstance(assets, list):
                for asset in assets:
                    if isinstance(asset, dict):
                        yield asset
        for child in value.values():
            yield from iter_api_assets(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_api_assets(child)


def count_api_assets_in_document(document: object) -> int:
    api_keys: set[str] = set()
    for api_asset in iter_api_assets(document or {}):
        key = _license_api_asset_key(api_asset)
        if key:
            api_keys.add(key)
    return len(api_keys)


def _version_api_snapshots(
    db: Session,
    organization_id: UUID,
) -> list[tuple[UUID, object]]:
    rows = db.execute(
        select(BotVersion.id, BotVersion.apis_json)
        .join(Bot, Bot.id == BotVersion.bot_id)
        .where(
            Bot.organization_id == organization_id,
            Bot.deleted_at.is_(None),
            BotVersion.deleted_at.is_(None),
        )
    ).all()
    missing_version_ids = [version_id for version_id, snapshot in rows if not isinstance(snapshot, list)]
    if not missing_version_ids:
        return rows

    legacy_documents = dict(
        db.execute(
            select(BotVersion.id, BotVersion.version_json).where(BotVersion.id.in_(missing_version_ids))
        ).all()
    )
    return [
        (version_id, snapshot if isinstance(snapshot, list) else legacy_documents.get(version_id, {}))
        for version_id, snapshot in rows
    ]


def _iter_version_api_assets(snapshot: object):
    if isinstance(snapshot, list):
        yield from (asset for asset in snapshot if isinstance(asset, dict))
        return
    yield from iter_api_assets(snapshot or {})


def count_registered_apis(db: Session, organization_id: UUID) -> int:
    api_keys: set[str] = set()
    for _version_id, snapshot in _version_api_snapshots(db, organization_id):
        for api_asset in _iter_version_api_assets(snapshot):
            key = _license_api_asset_key(api_asset)
            if key:
                api_keys.add(key)
    return len(api_keys)

def count_registered_apis_with_version_override(
    db: Session,
    organization_id: UUID,
    version_id: UUID,
    next_document: object,
) -> int:
    api_keys: set[str] = set()
    for current_version_id, snapshot in _version_api_snapshots(db, organization_id):
        source_document = next_document if current_version_id == version_id else snapshot
        for api_asset in _iter_version_api_assets(source_document):
            key = _license_api_asset_key(api_asset)
            if key:
                api_keys.add(key)
    return len(api_keys)

def get_license_usage_counts(db: Session, organization_id: UUID, *, creator_id: UUID | None = None) -> dict[LicenseResource, int]:
    return {
        "users": int(
            db.scalar(
                select(func.count()).select_from(User).where(
                    User.organization_id == organization_id,
                    User.status == "active",
                    User.deleted_at.is_(None),
                )
            )
            or 0
        ),
        "bots": int(
            db.scalar(
                select(func.count()).select_from(Bot).where(
                    Bot.organization_id == organization_id,
                    Bot.deleted_at.is_(None),
                    *([Bot.created_by == creator_id] if creator_id is not None else []),
                )
            )
            or 0
        ),
        "apis": count_registered_apis(db, organization_id),
    }


def get_license_warnings(
    db: Session,
    organization_id: UUID,
    *,
    license_record: AdminLicense | None | object = _UNSET,
    usage_counts: dict[LicenseResource, int] | None = None,
) -> list[str]:
    record = get_current_license(db, organization_id) if license_record is _UNSET else license_record
    payload = _license_payload(record)
    if record is None or payload is None:
        return ["라이선스가 적용되어 있지 않습니다. 신규 생성이 제한됩니다."]

    warnings: list[str] = []
    expires_at = parse_license_date(payload.get("expires_at"))
    if expires_at is not None:
        remaining_days = (expires_at - date.today()).days
        if remaining_days < 0:
            warnings.append("라이선스가 만료되었습니다. 기존 사용은 가능하지만 신규 생성은 제한됩니다.")
        elif remaining_days <= 30:
            warnings.append(f"라이선스 만료가 {remaining_days}일 남았습니다.")

    usage = usage_counts if usage_counts is not None else get_license_usage_counts(db, organization_id)
    limits = _license_limits(payload)
    for key, label in LICENSE_RESOURCE_LABELS.items():
        limit = limits.get(key)
        if limit is None:
            continue
        used = usage[key]
        if used > limit:
            warnings.append(f"{label} 사용량이 라이선스 한도를 초과했습니다. ({used}/{limit})")
        elif used >= limit:
            warnings.append(f"{label} 사용량이 라이선스 한도에 도달했습니다. 신규 생성이 제한됩니다. ({used}/{limit})")
    return warnings


def lock_license_scope(db: Session, organization_id: UUID) -> None:
    """생성과 라이선스 교체가 같은 조직 장벽을 사용한다. commit은 호출자가 담당한다."""
    if db.scalar(select(Organization.id).where(Organization.id == organization_id).with_for_update()) is None:
        raise HTTPException(status_code=404, detail="조직을 찾을 수 없습니다.")


def get_bot_creation_policy(db: Session, organization_id: UUID, creator_id: UUID) -> dict:
    used = int(db.scalar(select(func.count()).select_from(Bot).where(
        Bot.organization_id == organization_id, Bot.created_by == creator_id, Bot.deleted_at.is_(None)
    )) or 0)
    record = get_current_license(db, organization_id)
    payload = _license_payload(record)
    value = (payload.get("limits") or {}).get("bots") if payload and isinstance(payload.get("limits"), dict) else None
    limit = value if type(value) is int and value >= 0 else None
    reason = "available"
    if record is None or payload is None:
        reason = "license_missing"
    else:
        try:
            expires_at = parse_license_date(payload.get("expires_at"))
        except HTTPException:
            reason = "license_invalid"
        else:
            if expires_at is not None and expires_at < date.today():
                reason = "license_expired"
            elif limit is None:
                reason = "bot_limit_invalid"
            elif used >= limit:
                reason = "quota_reached"
    return {"limit": limit, "used": used, "remaining": max(limit-used, 0) if limit is not None else None,
            "allowed": reason == "available", "reason": reason}


def assert_license_allows_creation(
    db: Session,
    organization_id: UUID,
    resource: LicenseResource,
    quantity: int = 1,
    *, creator_id: UUID | None = None,
) -> None:
    if resource == "bots":
        if creator_id is None:
            raise HTTPException(status_code=403, detail="인증된 제작자 정보가 필요합니다.")
        policy = get_bot_creation_policy(db, organization_id, creator_id)
        if not policy["allowed"] or policy["remaining"] < max(quantity, 1):
            messages = {"license_missing": "라이선스를 적용한 후 봇을 생성할 수 있습니다.",
                        "license_expired": "라이선스가 만료되어 신규 봇 생성이 제한됩니다.",
                        "bot_limit_invalid": "사용자별 봇 라이선스 한도를 확인해주세요.",
                        "license_invalid": "라이선스 정보를 확인해주세요."}
            raise HTTPException(status_code=403, detail=messages.get(policy["reason"],
                f"사용자별 봇 라이선스 생성 한도에 도달했습니다. ({policy['used']}/{policy['limit']})"))
        return
    record = get_current_license(db, organization_id)
    payload = _license_payload(record)
    label = LICENSE_RESOURCE_LABELS[resource]
    if record is None or payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"라이선스를 적용한 후 {label}을 생성할 수 있습니다.",
        )

    expires_at = parse_license_date(payload.get("expires_at"))
    if expires_at is not None and expires_at < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"라이선스가 만료되어 신규 {label} 생성이 제한됩니다.",
        )

    limit = _license_limits(payload).get(resource)
    if limit is None:
        return

    used = get_license_usage_counts(db, organization_id)[resource]
    requested_quantity = max(quantity, 1)
    if used + requested_quantity > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"라이선스 {label} 생성 한도에 도달했습니다. ({used}/{limit})",
        )
