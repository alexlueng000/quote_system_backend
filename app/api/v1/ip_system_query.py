from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.core.security import decode_token
from app.db import mysql
from app.schemas.ip_system_query import (
    IpSystemApplyUpdatesRequest,
    IpSystemApplyUpdatesResponse,
    IpSystemCheckUpdatesResponse,
    IpSystemDataSource,
    IpSystemDataSourceCreate,
    IpSystemDataSourceUpdate,
    IpSystemJurisdictionMembershipGroup,
    IpSystemJurisdictionMembershipRequest,
    IpSystemJurisdictionOption,
    IpSystemMemberRemarkUpdate,
    IpSystemQueryMember,
    IpSystemMembersResponse,
    IpSystemQuerySystem,
    IpSystemReferenceObjectsResponse,
    IpSystemUpdateHistoryItem,
)
from app.services import ip_system_query_service


router = APIRouter(prefix="/ip-system-query", tags=["ip-system-query"])


@router.get("/systems", response_model=list[IpSystemQuerySystem])
async def list_query_systems(
    include_reserved: bool = Query(default=False),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemQuerySystem]:
    require_any_user(authorization, x_user_email)
    user = require_any_user(authorization, x_user_email)
    return ip_system_query_service.list_systems(
        include_reserved=include_reserved and user["role"] == "admin",
    )


@router.get("/systems/{system_code}/members", response_model=IpSystemMembersResponse)
async def system_members(
    system_code: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemMembersResponse:
    require_any_user(authorization, x_user_email)
    try:
        return ip_system_query_service.get_system_members(system_code)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.get("/jurisdictions/search", response_model=list[IpSystemJurisdictionOption])
async def search_jurisdictions(
    keyword: str = Query(min_length=1),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemJurisdictionOption]:
    require_any_user(authorization, x_user_email)
    return ip_system_query_service.search_jurisdictions(keyword)


@router.post("/jurisdictions/memberships", response_model=list[IpSystemJurisdictionMembershipGroup])
async def jurisdiction_memberships(
    payload: IpSystemJurisdictionMembershipRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemJurisdictionMembershipGroup]:
    require_any_user(authorization, x_user_email)
    return ip_system_query_service.get_jurisdiction_memberships_by_codes(
        jurisdiction_ids=payload.jurisdiction_ids,
        jurisdiction_codes=payload.jurisdiction_codes,
    )


@router.post("/systems/{system_code}/check-updates", response_model=IpSystemCheckUpdatesResponse)
async def check_system_updates(
    system_code: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemCheckUpdatesResponse:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.check_updates(system_code)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.post("/systems/{system_code}/apply-updates", response_model=IpSystemApplyUpdatesResponse)
async def apply_system_updates(
    system_code: str,
    payload: IpSystemApplyUpdatesRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemApplyUpdatesResponse:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.apply_updates(system_code, payload.diffs, actor=str(user["email"]))
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.get("/data-sources", response_model=list[IpSystemDataSource])
async def list_data_sources(
    system_code: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemDataSource]:
    require_admin(authorization, x_user_email)
    return ip_system_query_service.list_data_sources(system_code)


@router.get("/update-history", response_model=list[IpSystemUpdateHistoryItem])
async def list_update_history(
    source_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemUpdateHistoryItem]:
    require_admin(authorization, x_user_email)
    return ip_system_query_service.list_update_history(source_id=source_id, limit=limit)


@router.get("/reference-objects", response_model=IpSystemReferenceObjectsResponse)
async def list_reference_objects(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemReferenceObjectsResponse:
    require_any_user(authorization, x_user_email)
    return ip_system_query_service.list_reference_objects()


@router.post("/data-sources", response_model=IpSystemDataSource)
async def create_data_source(
    payload: IpSystemDataSourceCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemDataSource:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.create_data_source(payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.patch("/data-sources/{source_id}", response_model=IpSystemDataSource)
async def update_data_source(
    source_id: str,
    payload: IpSystemDataSourceUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemDataSource:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.update_data_source(source_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_DATA_SOURCE_NOT_FOUND", "Data source not found") from exc


@router.post("/data-sources/{source_id}/check-updates", response_model=IpSystemCheckUpdatesResponse)
async def check_data_source_updates(
    source_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemCheckUpdatesResponse:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.check_data_source_updates(source_id)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_DATA_SOURCE_NOT_FOUND", "Data source not found") from exc


@router.post("/data-sources/{source_id}/apply-updates", response_model=IpSystemApplyUpdatesResponse)
async def apply_data_source_updates(
    source_id: str,
    payload: IpSystemApplyUpdatesRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemApplyUpdatesResponse:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.apply_data_source_updates(
            source_id,
            payload.diffs,
            actor=str(user["email"]),
        )
    except KeyError as exc:
        raise not_found("IP_SYSTEM_DATA_SOURCE_NOT_FOUND", "Data source not found") from exc


@router.patch("/systems/{system_code}/members/{jurisdiction_code}/remark", response_model=IpSystemQueryMember)
async def update_member_remark(
    system_code: str,
    jurisdiction_code: str,
    payload: IpSystemMemberRemarkUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemQueryMember:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_query_service.update_member_remark(
            system_code,
            jurisdiction_code,
            payload,
            str(user["email"]),
        )
    except KeyError as exc:
        raise not_found("IP_SYSTEM_MEMBER_NOT_FOUND", "IP system member not found") from exc


def get_current_user(
    authorization: str | None,
    x_user_email: str | None,
) -> dict[str, object] | None:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_token(token)
        if payload:
            user = mysql.fetch_user_by_email(str(payload.get("email", "")))
            if user and user["status"] == "active":
                return user
    if x_user_email:
        user = mysql.fetch_user_by_email(x_user_email)
        if user and user["status"] == "active":
            return user
    return None


def require_any_user(
    authorization: str | None,
    x_user_email: str | None,
) -> dict[str, object]:
    user = get_current_user(authorization, x_user_email)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    return user


def require_admin(
    authorization: str | None,
    x_user_email: str | None,
) -> dict[str, object]:
    user = require_any_user(authorization, x_user_email)
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_REQUIRED", "message": "Admin permission required"},
        )
    return user


def not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})
