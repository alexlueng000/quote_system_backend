"""Legacy advanced IP-system maintenance router.

The lightweight query page uses app.api.v1.ip_system_query instead.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query
from pymysql.err import IntegrityError

from app.core.security import decode_token
from app.db import mysql
from app.schemas.ip_system import (
    IpSystem,
    IpSystemAdvancedWorkbenchResponse,
    IpSystemBusinessDashboardResponse,
    IpSystemBusinessDetailResponse,
    IpSystemBusinessDomain,
    IpSystemBusinessDomainCreate,
    IpSystemBusinessDomainUpdate,
    IpSystemChangeReview,
    IpSystemChangeReviewUpdate,
    IpSystemCheckResponse,
    IpSystemCreate,
    IpSystemEnablementCheckResponse,
    IpSystemImportRequest,
    IpSystemImportResponse,
    IpSystemJurisdictionProfileResponse,
    IpSystemJurisdictionReferenceCheck,
    IpSystemManualRelationReviewCreate,
    IpSystemMatchException,
    IpSystemMatchExceptionResolveRequest,
    IpSystemMatchExceptionUpdate,
    IpSystemOverview,
    IpSystemPublishBatchRequest,
    IpSystemPublishBatchResponse,
    IpSystemReferenceCandidateCreate,
    IpSystemReferenceCandidateResponse,
    IpSystemReferenceCoverageResponse,
    IpSystemReferenceReviewCreate,
    IpSystemReferenceReviewResponse,
    IpSystemReprocessBatchResponse,
    IpSystemRelation,
    IpSystemRelationCandidate,
    IpSystemRelationType,
    IpSystemRelationTypeCreate,
    IpSystemRelationTypeUpdate,
    IpSystemSourceConfig,
    IpSystemSourceConfigCreate,
    IpSystemSourceConfigUpdate,
    IpSystemSyncBatchDetail,
    IpSystemSyncPrepareRequest,
    IpSystemSyncPrepareResponse,
    IpSystemTag,
    IpSystemUpdate,
    QuoteIpTag,
)
from app.services import ip_system_service
from app.services import ip_system_sync_service

router = APIRouter(tags=["ip-systems"])


@router.get("/ip-systems", response_model=list[IpSystem])
async def list_systems(
    include_inactive: bool = Query(default=False),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystem]:
    require_any_user(authorization, x_user_email)
    return ip_system_service.list_ip_systems(include_inactive=include_inactive)


@router.get("/ip-system-relation-types", response_model=list[IpSystemRelationType])
async def list_system_relation_types(
    include_inactive: bool = Query(default=False),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemRelationType]:
    require_any_user(authorization, x_user_email)
    return ip_system_service.list_relation_types(include_inactive=include_inactive)


@router.get("/ip-systems/review-due", response_model=list[IpSystem])
async def review_due_systems(
    days_ahead: int = Query(default=30, ge=0, le=365),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystem]:
    require_any_user(authorization, x_user_email)
    return ip_system_service.get_review_due_systems(days_ahead=days_ahead)


@router.get("/ip-systems/business-dashboard", response_model=IpSystemBusinessDashboardResponse)
async def business_dashboard(
    include_reserved: bool = Query(default=False),
    include_inactive: bool = Query(default=False),
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemBusinessDashboardResponse:
    require_any_user(authorization, x_user_email)
    return ip_system_service.get_business_dashboard(
        include_reserved=include_reserved,
        include_inactive=include_inactive,
        as_of=as_of,
    )


@router.get("/ip-systems/advanced-workbench", response_model=IpSystemAdvancedWorkbenchResponse)
async def advanced_workbench(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemAdvancedWorkbenchResponse:
    require_admin_or_approver(authorization, x_user_email)
    return ip_system_service.get_advanced_workbench()


@router.get("/ip-systems/jurisdiction-enablement-check", response_model=IpSystemEnablementCheckResponse)
async def jurisdiction_enablement_check(
    query: str = Query(min_length=1),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemEnablementCheckResponse:
    require_admin_or_approver(authorization, x_user_email)
    return ip_system_service.get_jurisdiction_enablement_check(query)


@router.get("/ip-systems/{system_id}/business-detail", response_model=IpSystemBusinessDetailResponse)
async def business_detail(
    system_id: str,
    include_non_phase1_candidates: bool = Query(default=False),
    include_reserved: bool = Query(default=False),
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemBusinessDetailResponse:
    require_any_user(authorization, x_user_email)
    try:
        return ip_system_service.get_business_detail(
            system_id,
            include_non_phase1_candidates=include_non_phase1_candidates,
            include_reserved=include_reserved,
            as_of=as_of,
        )
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.get("/ip-systems/{system_id}/reference-coverage", response_model=IpSystemReferenceCoverageResponse)
async def reference_coverage(
    system_id: str,
    source_config_id: str | None = Query(default=None),
    relation_type_code: str | None = Query(default=None),
    business_domain: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemReferenceCoverageResponse:
    require_any_user(authorization, x_user_email)
    try:
        return ip_system_service.get_reference_coverage(
            system_id,
            source_config_id=source_config_id,
            relation_type_code=relation_type_code,
            business_domain=business_domain,
            as_of=as_of,
        )
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.get("/jurisdictions/{jurisdiction_id}/ip-system-profile", response_model=IpSystemJurisdictionProfileResponse)
async def jurisdiction_profile(
    jurisdiction_id: str,
    include_not_applicable: bool = Query(default=False),
    include_reserved: bool = Query(default=False),
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemJurisdictionProfileResponse:
    require_any_user(authorization, x_user_email)
    try:
        return ip_system_service.get_jurisdiction_profile(
            jurisdiction_id,
            include_not_applicable=include_not_applicable,
            include_reserved=include_reserved,
            as_of=as_of,
        )
    except KeyError as exc:
        raise not_found("JURISDICTION_NOT_FOUND", "Jurisdiction not found") from exc


@router.get("/ip-systems/{system_id}/overview", response_model=IpSystemOverview)
async def system_overview(
    system_id: str,
    business_domain: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemOverview:
    require_any_user(authorization, x_user_email)
    try:
        return ip_system_service.get_ip_system_overview(system_id, business_domain, as_of)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.get("/ip-systems/{system_id}/relations", response_model=list[IpSystemRelation])
async def system_relations(
    system_id: str,
    business_domain: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    current_only: bool = Query(default=True),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemRelation]:
    user = require_any_user(authorization, x_user_email)
    if user["role"] == "consultant":
        current_only = True
    return ip_system_service.get_system_relations(
        system_id,
        business_domain=business_domain,
        as_of=as_of,
        current_only=current_only,
        published_only=True,
    )


@router.get("/ip-systems/{system_id}/source-configs", response_model=list[IpSystemSourceConfig])
async def system_source_configs(
    system_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemSourceConfig]:
    require_any_user(authorization, x_user_email)
    return ip_system_service.get_source_configs(system_id)


@router.get("/jurisdictions/{jurisdiction_id}/ip-system-relations", response_model=list[IpSystemRelation])
async def jurisdiction_relations(
    jurisdiction_id: str,
    as_of: date | None = Query(default=None),
    current_only: bool = Query(default=True),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemRelation]:
    user = require_any_user(authorization, x_user_email)
    if user["role"] == "consultant":
        current_only = True
    return ip_system_service.get_jurisdiction_relations(
        jurisdiction_id,
        as_of=as_of,
        current_only=current_only,
        published_only=True,
    )


@router.get("/jurisdictions/{jurisdiction_id}/ip-system-tags", response_model=list[IpSystemTag])
async def jurisdiction_tags(
    jurisdiction_id: str,
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemTag]:
    require_any_user(authorization, x_user_email)
    return ip_system_service.get_jurisdiction_tags(jurisdiction_id, as_of=as_of)


@router.get("/jurisdictions/{jurisdiction_id}/quote-ip-tags", response_model=list[QuoteIpTag])
async def quote_ip_tags(
    jurisdiction_id: str,
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[QuoteIpTag]:
    require_any_user(authorization, x_user_email)
    return ip_system_service.get_quote_ip_tags(jurisdiction_id, as_of=as_of)


@router.get("/jurisdictions/{jurisdiction_id}/ip-system-reference-check", response_model=IpSystemJurisdictionReferenceCheck)
async def jurisdiction_reference_check(
    jurisdiction_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemJurisdictionReferenceCheck:
    require_admin_or_approver(authorization, x_user_email)
    return ip_system_service.get_jurisdiction_reference_check(jurisdiction_id)


@router.get("/ip-system-relations/check", response_model=IpSystemCheckResponse)
async def check_relation(
    jurisdiction_id: str,
    system_code: str,
    relation_type_code: str,
    business_domain: str,
    as_of: date | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemCheckResponse:
    require_any_user(authorization, x_user_email)
    return ip_system_service.check_ip_system_relation(
        jurisdiction_id,
        system_code,
        relation_type_code,
        business_domain,
        as_of=as_of,
    )


@router.post("/ip-systems", response_model=IpSystem)
async def create_system(
    payload: IpSystemCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystem:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_ip_system(payload)
    except IntegrityError as exc:
        raise conflict("IP_SYSTEM_CONFLICT", "IP system already exists") from exc


@router.patch("/ip-systems/{system_id}", response_model=IpSystem)
async def update_system(
    system_id: str,
    payload: IpSystemUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystem:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.update_ip_system(system_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.post("/ip-systems/{system_id}/business-domains", response_model=IpSystemBusinessDomain)
async def create_system_business_domain(
    system_id: str,
    payload: IpSystemBusinessDomainCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemBusinessDomain:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_business_domain(system_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc
    except IntegrityError as exc:
        raise conflict("IP_SYSTEM_BUSINESS_DOMAIN_CONFLICT", "Business domain conflict") from exc


@router.patch("/ip-system-business-domains/{domain_id}", response_model=IpSystemBusinessDomain)
async def update_system_business_domain(
    domain_id: str,
    payload: IpSystemBusinessDomainUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemBusinessDomain:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.update_business_domain(domain_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_BUSINESS_DOMAIN_NOT_FOUND", "Business domain not found") from exc


@router.post("/ip-system-relation-types", response_model=IpSystemRelationType)
async def create_system_relation_type(
    payload: IpSystemRelationTypeCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemRelationType:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_relation_type(payload)
    except IntegrityError as exc:
        raise conflict("IP_SYSTEM_RELATION_TYPE_CONFLICT", "Relation type conflict") from exc


@router.patch("/ip-system-relation-types/{relation_type_id}", response_model=IpSystemRelationType)
async def update_system_relation_type(
    relation_type_id: str,
    payload: IpSystemRelationTypeUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemRelationType:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.update_relation_type(relation_type_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_RELATION_TYPE_NOT_FOUND", "Relation type not found") from exc


@router.post("/ip-system-relations/manual-review", response_model=IpSystemChangeReview)
async def create_manual_relation_review(
    payload: IpSystemManualRelationReviewCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemChangeReview:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_manual_relation_review(payload, actor=str(user["email"]))
    except KeyError as exc:
        raise not_found(str(exc), str(exc)) from exc
    except ValueError as exc:
        raise conflict(str(exc), str(exc)) from exc


@router.post("/ip-systems/{system_id}/source-configs", response_model=IpSystemSourceConfig)
async def create_system_source_config(
    system_id: str,
    payload: IpSystemSourceConfigCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemSourceConfig:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_source_config(system_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.patch("/ip-system-source-configs/{source_config_id}", response_model=IpSystemSourceConfig)
async def update_system_source_config(
    source_config_id: str,
    payload: IpSystemSourceConfigUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemSourceConfig:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_service.update_source_config(source_config_id, payload)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_SOURCE_CONFIG_NOT_FOUND", "Source config not found") from exc


@router.post("/ip-systems/{system_id}/reference-candidates", response_model=IpSystemReferenceCandidateResponse)
async def create_reference_candidates(
    system_id: str,
    payload: IpSystemReferenceCandidateCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemReferenceCandidateResponse:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_reference_candidates(system_id, payload, actor=str(user["email"]))
    except KeyError as exc:
        raise not_found(str(exc), str(exc)) from exc
    except ValueError as exc:
        raise conflict(str(exc), str(exc)) from exc


@router.get("/ip-system-relation-candidates", response_model=list[IpSystemRelationCandidate])
async def relation_candidates(
    source_config_id: str | None = Query(default=None),
    system_id: str | None = Query(default=None),
    jurisdiction_id: str | None = Query(default=None),
    match_status: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemRelationCandidate]:
    require_admin_or_approver(authorization, x_user_email)
    return ip_system_service.list_relation_candidates(
        source_config_id=source_config_id,
        system_id=system_id,
        jurisdiction_id=jurisdiction_id,
        match_status=match_status,
    )


@router.post("/ip-system-relation-candidates/reviews", response_model=IpSystemReferenceReviewResponse)
async def create_reviews_from_reference_candidates(
    payload: IpSystemReferenceReviewCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemReferenceReviewResponse:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_service.create_reviews_from_reference_candidates(payload, actor=str(user["email"]))
    except KeyError as exc:
        raise not_found(str(exc), str(exc)) from exc
    except ValueError as exc:
        raise conflict(str(exc), str(exc)) from exc


@router.post("/ip-systems/{system_id}/sync-batches", response_model=IpSystemSyncPrepareResponse)
async def prepare_sync_batch(
    system_id: str,
    payload: IpSystemSyncPrepareRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemSyncPrepareResponse:
    user = require_admin(authorization, x_user_email)
    snapshot = None
    if payload.raw_content or payload.raw_snapshot_path:
        snapshot = ip_system_sync_service.create_source_snapshot(
            system_id=system_id,
            source_config_id=payload.source_config_id,
            snapshot_type=payload.snapshot_type,
            raw_snapshot_path=payload.raw_snapshot_path,
            raw_content=payload.raw_content,
            raw_metadata=payload.raw_metadata,
            captured_by=str(user["email"]),
            remark=payload.remark,
        )
    batch = ip_system_sync_service.create_sync_batch(
        system_id=system_id,
        source_config_id=payload.source_config_id,
        source_snapshot_id=str(snapshot["snapshot_id"]) if snapshot else None,
        batch_type=payload.batch_type,
        raw_snapshot_path=payload.raw_snapshot_path,
        created_by=str(user["email"]),
    )
    return IpSystemSyncPrepareResponse(
        batch=batch,
        snapshot_id=str(snapshot["snapshot_id"]) if snapshot else None,
    )


@router.post("/ip-systems/{system_id}/imports", response_model=IpSystemImportResponse)
async def import_system_relations(
    system_id: str,
    payload: IpSystemImportRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemImportResponse:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_sync_service.process_import(
            system_id=system_id,
            payload=payload,
            actor=str(user["email"]),
        )
    except KeyError as exc:
        raise not_found("IP_SYSTEM_NOT_FOUND", "IP system not found") from exc


@router.get("/ip-system-sync-batches/{batch_id}", response_model=IpSystemSyncBatchDetail)
async def sync_batch_detail(
    batch_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemSyncBatchDetail:
    require_admin_or_approver(authorization, x_user_email)
    try:
        return ip_system_sync_service.get_sync_batch(batch_id)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_SYNC_BATCH_NOT_FOUND", "Sync batch not found") from exc


@router.get("/ip-system-sync-batches/{batch_id}/changes", response_model=list[IpSystemChangeReview])
async def sync_batch_changes(
    batch_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemChangeReview]:
    require_admin_or_approver(authorization, x_user_email)
    return ip_system_sync_service.get_batch_changes(batch_id)


@router.get("/ip-system-sync-batches/{batch_id}/exceptions", response_model=list[IpSystemMatchException])
async def sync_batch_exceptions(
    batch_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemMatchException]:
    require_admin(authorization, x_user_email)
    return [
        IpSystemMatchException.model_validate(row)
        for row in ip_system_sync_service.get_batch_exceptions(batch_id)
    ]


@router.post("/ip-system-sync-batches/{batch_id}/reprocess", response_model=IpSystemReprocessBatchResponse)
async def reprocess_sync_batch(
    batch_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemReprocessBatchResponse:
    require_admin(authorization, x_user_email)
    try:
        return ip_system_sync_service.reprocess_batch(batch_id)
    except KeyError as exc:
        raise not_found("IP_SYSTEM_SYNC_BATCH_NOT_FOUND", "Sync batch not found") from exc


@router.get("/ip-system-change-reviews", response_model=list[IpSystemChangeReview])
async def change_reviews(
    batch_id: str | None = Query(default=None),
    system_id: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemChangeReview]:
    require_admin_or_approver(authorization, x_user_email)
    return ip_system_service.list_change_reviews(batch_id, system_id, review_status)


@router.patch("/ip-system-change-reviews/{review_id}", response_model=IpSystemChangeReview)
async def update_review(
    review_id: str,
    payload: IpSystemChangeReviewUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemChangeReview:
    user = require_admin_or_approver(authorization, x_user_email)
    try:
        return ip_system_service.update_change_review(review_id, payload, actor=str(user["email"]))
    except KeyError as exc:
        raise not_found("IP_SYSTEM_REVIEW_NOT_FOUND", "Change review not found") from exc


@router.post("/ip-system-sync-batches/{batch_id}/publish", response_model=IpSystemPublishBatchResponse)
async def publish_sync_batch(
    batch_id: str,
    payload: IpSystemPublishBatchRequest | None = None,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemPublishBatchResponse:
    user = require_admin_or_approver(authorization, x_user_email)
    request = payload or IpSystemPublishBatchRequest()
    try:
        return ip_system_service.publish_batch(
            batch_id,
            request,
            actor=str(user["email"]),
            can_auto_approve=user["role"] in {"admin", "approver"},
        )
    except KeyError as exc:
        raise not_found("IP_SYSTEM_SYNC_BATCH_NOT_FOUND", "Sync batch not found") from exc
    except ValueError as exc:
        raise conflict(str(exc), str(exc)) from exc


@router.get("/ip-system-match-exceptions", response_model=list[IpSystemMatchException])
async def match_exceptions(
    system_id: str | None = Query(default=None),
    source_config_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[IpSystemMatchException]:
    require_admin(authorization, x_user_email)
    return ip_system_service.list_match_exceptions(system_id, source_config_id, status)


@router.patch("/ip-system-match-exceptions/{exception_id}", response_model=IpSystemMatchException)
async def update_match_exception(
    exception_id: str,
    payload: IpSystemMatchExceptionUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemMatchException:
    user = require_admin(authorization, x_user_email)
    try:
        return ip_system_service.update_match_exception(exception_id, payload, actor=str(user["email"]))
    except KeyError as exc:
        raise not_found("IP_SYSTEM_MATCH_EXCEPTION_NOT_FOUND", "Match exception not found") from exc


@router.post("/ip-system-match-exceptions/{exception_id}/resolve", response_model=IpSystemReprocessBatchResponse | IpSystemMatchException)
async def resolve_match_exception(
    exception_id: str,
    payload: IpSystemMatchExceptionResolveRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> IpSystemReprocessBatchResponse | IpSystemMatchException:
    user = require_admin(authorization, x_user_email)
    try:
        updated = ip_system_service.update_match_exception(
            exception_id,
            IpSystemMatchExceptionUpdate(
                status="confirmed",
                resolved_jurisdiction_id=payload.resolved_jurisdiction_id,
                resolution_comment=payload.resolution_comment,
                create_alias_mapping=payload.create_alias_mapping,
            ),
            actor=str(user["email"]),
        )
        if payload.reprocess and updated.batch_id:
            return ip_system_sync_service.reprocess_batch(updated.batch_id)
        return updated
    except KeyError as exc:
        raise not_found("IP_SYSTEM_MATCH_EXCEPTION_NOT_FOUND", "Match exception not found") from exc


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


def require_admin_or_approver(
    authorization: str | None,
    x_user_email: str | None,
) -> dict[str, object]:
    user = require_any_user(authorization, x_user_email)
    if user["role"] not in {"admin", "approver"}:
        raise HTTPException(
            status_code=403,
            detail={"code": "REVIEW_PERMISSION_REQUIRED", "message": "Review permission required"},
        )
    return user


def not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})
