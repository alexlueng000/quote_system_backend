"""Legacy advanced IP-system maintenance service.

The lightweight query page uses app.services.ip_system_query_service instead.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.db import mysql
from app.schemas.ip_system import (
    IpSystem,
    IpSystemAdvancedWorkbenchResponse,
    IpSystemBusinessActionItem,
    IpSystemBusinessDashboardItem,
    IpSystemBusinessDashboardResponse,
    IpSystemBusinessDomain,
    IpSystemBusinessDomainCreate,
    IpSystemBusinessDomainUpdate,
    IpSystemBusinessDetailResponse,
    IpSystemBusinessReferenceSummary,
    IpSystemBusinessRelationItem,
    IpSystemBusinessRelationSummary,
    IpSystemBusinessRelationSummaryBucket,
    IpSystemBusinessTodoItem,
    IpSystemBusinessTodoSummary,
    IpSystemChangeReview,
    IpSystemChangeReviewUpdate,
    IpSystemCheckResponse,
    IpSystemCreate,
    IpSystemEnablementCheckResponse,
    IpSystemEnablementMatchedJurisdiction,
    IpSystemEnablementSystemStatus,
    IpSystemJurisdictionProfileCard,
    IpSystemJurisdictionProfileResponse,
    IpSystemJurisdictionReferenceCheck,
    IpSystemJurisdictionSystemCard,
    IpSystemJurisdictionTodoItem,
    IpSystemManualRelationReviewCreate,
    IpSystemMatchException,
    IpSystemMatchExceptionUpdate,
    IpSystemOverview,
    IpSystemPublishBatchRequest,
    IpSystemPublishBatchResponse,
    IpSystemReferenceCoverageResponse,
    IpSystemReferenceCoverageStats,
    IpSystemRelation,
    IpSystemReferenceCandidateCreate,
    IpSystemReferenceCandidateResponse,
    IpSystemReferenceReviewCreate,
    IpSystemReferenceReviewResponse,
    IpSystemRelationCandidate,
    IpSystemRelationType,
    IpSystemRelationTypeCreate,
    IpSystemRelationTypeUpdate,
    IpSystemSourceConfig,
    IpSystemSourceConfigCreate,
    IpSystemSourceConfigUpdate,
    IpSystemSyncBatch,
    IpSystemTag,
    IpSystemUpdate,
    IpSystemV1PhaseScope,
    QuoteIpTag,
)
from app.services import ip_system_sync_service


PHASE1_SYSTEM_CODES = ("PCT", "PARIS", "EPC", "EUIPO")
RESERVED_SYSTEM_CODES = ("HAGUE", "MADRID", "UPC_UP", "OAPI", "ARIPO")
PHASE1_JURISDICTION_CODES = ("US", "JP", "KR", "EP", "EPO", "EM", "EUIPO")
BUSINESS_RELATION_SUMMARY_BUCKETS = (
    ("contracting_members", "缔约国 / 成员国", ("CONTRACTING_STATE", "MEMBER_STATE")),
    ("regional_phase_offices", "区域阶段局", ("REGIONAL_PHASE_OFFICE",)),
    ("granting_authorities", "授权机构", ("GRANTING_AUTHORITY",)),
    ("priority_routes", "优先权路径", ("PRIORITY_ROUTE_AVAILABLE",)),
)
IP_SYSTEM_BOUNDARY_NOTES = (
    "国家主档负责稳定基础信息，本模块负责条约、组织、区域体系关系。",
    "国家主档中的 PCT / Paris / EPC 标签只能读取本模块已发布关系自动生成，不在国家主档中手工维护。",
    "新增国家/地区先确保 jurisdiction_id 存在，再确认是否纳入当前维护范围，再从 Reference candidate / review / publish 维护关系。",
    "当前第一期范围由后端配置控制；管理员直接配置 phase scope 属于 V1-B，不在 V1-A-Repair 中启用。",
)


def list_ip_systems(include_inactive: bool = True) -> list[IpSystem]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        where = "" if include_inactive else "WHERE is_active = 1"
        cursor.execute(f"SELECT * FROM ip_system_master {where} ORDER BY display_order, system_code")
        systems = [_normalize_record(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM ip_system_business_domain ORDER BY system_id, business_domain")
        domains = [_normalize_record(row) for row in cursor.fetchall()]
    domains_by_system: dict[str, list[dict[str, object]]] = {}
    for domain in domains:
        domains_by_system.setdefault(str(domain["system_id"]), []).append(domain)
    for system in systems:
        system["business_domains"] = domains_by_system.get(str(system["system_id"]), [])
    return [IpSystem.model_validate(system) for system in systems]


def list_relation_types(include_inactive: bool = False) -> list[IpSystemRelationType]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        where = "" if include_inactive else "WHERE is_active = 1"
        cursor.execute(f"SELECT * FROM ip_system_relation_type {where} ORDER BY display_order, relation_type_code")
        return [IpSystemRelationType.model_validate(_normalize_record(row)) for row in cursor.fetchall()]


def get_review_due_systems(days_ahead: int = 30) -> list[IpSystem]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM ip_system_master
            WHERE is_active = 1
              AND next_review_due_at IS NOT NULL
              AND next_review_due_at <= DATE_ADD(NOW(), INTERVAL %s DAY)
            ORDER BY next_review_due_at, display_order, system_code
            """,
            (days_ahead,),
        )
        systems = [_normalize_record(row) for row in cursor.fetchall()]
        cursor.execute(
            "SELECT * FROM ip_system_business_domain WHERE is_enabled = 1 ORDER BY system_id, business_domain"
        )
        domains = [_normalize_record(row) for row in cursor.fetchall()]
    domains_by_system: dict[str, list[dict[str, object]]] = {}
    for domain in domains:
        domains_by_system.setdefault(str(domain["system_id"]), []).append(domain)
    for system in systems:
        system["business_domains"] = domains_by_system.get(str(system["system_id"]), [])
    return [IpSystem.model_validate(system) for system in systems]


def get_ip_system_overview(
    system_id: str,
    business_domain: str | None = None,
    as_of: date | None = None,
) -> IpSystemOverview:
    effective_at = as_of or date.today()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ip_system_master WHERE system_id = %s LIMIT 1", (system_id,))
        system = _normalize_record(cursor.fetchone())
        if not system:
            raise KeyError(system_id)
        domain_sql = "AND r.business_domain = %s" if business_domain else ""
        domain_params: tuple[object, ...] = (business_domain,) if business_domain else ()
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT r.jurisdiction_id) AS count_value
            FROM jurisdiction_ip_system_relation r
            JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            WHERE r.system_id = %s
              AND {_published_current_sql('r')}
              AND j.is_enabled = 1
              AND COALESCE(j.is_deleted, 0) = 0
              {domain_sql}
            """,
            (system_id, effective_at, effective_at, *domain_params),
        )
        current_count = int(cursor.fetchone()["count_value"] or 0)
        cursor.execute(
            f"""
            SELECT rt.relation_type_code, COUNT(DISTINCT r.jurisdiction_id) AS count_value
            FROM jurisdiction_ip_system_relation r
            JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
            WHERE r.system_id = %s
              AND {_published_current_sql('r')}
              AND j.is_enabled = 1
              AND COALESCE(j.is_deleted, 0) = 0
              {domain_sql}
            GROUP BY rt.relation_type_code
            """,
            (system_id, effective_at, effective_at, *domain_params),
        )
        relation_type_counts = {
            str(row["relation_type_code"]): int(row["count_value"] or 0)
            for row in cursor.fetchall()
        }
        cursor.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM ip_system_change_review
            WHERE system_id = %s AND review_status = 'pending_review'
            """,
            (system_id,),
        )
        pending_count = int(cursor.fetchone()["count_value"] or 0)
        cursor.execute(
            """
            SELECT MAX(finished_at) AS last_sync_at
            FROM ip_system_sync_batch
            WHERE system_id = %s AND status IN ('completed', 'published')
            """,
            (system_id,),
        )
        last_sync_at = cursor.fetchone()["last_sync_at"]
    next_due = system.get("next_review_due_at")
    if not next_due:
        review_status = "not_scheduled"
    elif next_due <= datetime.now():
        review_status = "overdue"
    else:
        review_status = "not_due"
    return IpSystemOverview.model_validate(
        {
            **system,
            "business_domain": business_domain,
            "current_jurisdiction_count": current_count,
            "relation_type_counts": relation_type_counts,
            "pending_review_count": pending_count,
            "last_sync_at": last_sync_at,
            "review_status": review_status,
        }
    )


def get_business_dashboard(
    *,
    include_reserved: bool = False,
    include_inactive: bool = False,
    as_of: date | None = None,
) -> IpSystemBusinessDashboardResponse:
    systems = list_ip_systems(include_inactive=True)
    items: list[IpSystemBusinessDashboardItem] = []
    for system in systems:
        if not include_reserved and _is_reserved_system(system.system_code):
            continue
        if not include_inactive and not system.is_active:
            continue
        if not include_reserved and not _is_phase1_system(system.system_code):
            continue
        items.append(_business_dashboard_item(system, as_of or date.today()))
    return IpSystemBusinessDashboardResponse(items=items, phase_scope=_phase_scope())


def get_business_detail(
    system_id: str,
    *,
    include_non_phase1_candidates: bool = False,
    include_reserved: bool = False,
    as_of: date | None = None,
) -> IpSystemBusinessDetailResponse:
    system = _get_system_or_raise(system_id)
    if _is_reserved_system(system.system_code) and not include_reserved:
        raise KeyError(system_id)
    effective_at = as_of or date.today()
    dashboard_item = _business_dashboard_item(system, effective_at)
    relations = [
        IpSystemBusinessRelationItem.model_validate({
            **item.model_dump(),
            "effective_status": _effective_status(item),
        })
        for item in get_system_relations(system_id, as_of=effective_at, current_only=False, published_only=True)
        if item.is_current_effective or include_reserved
    ]
    candidates = list_relation_candidates(system_id=system_id)
    if not include_non_phase1_candidates:
        candidates = [item for item in candidates if _candidate_is_phase1(item)]
    pending_reviews = list_change_reviews(system_id=system_id, review_status="pending_review")
    match_exceptions = list_match_exceptions(system_id=system_id, status="pending")
    relation_type_counts = _relation_type_counts(relations)
    todo_items = _business_todo_items(pending_reviews, candidates, match_exceptions, system.system_code)
    return IpSystemBusinessDetailResponse(
        system=dashboard_item,
        relation_summary=IpSystemBusinessRelationSummary(
            current_relation_count=sum(1 for item in relations if item.is_current_effective),
            relation_type_counts=relation_type_counts,
        ),
        current_relation_summary=_business_relation_summary_buckets(relations),
        todo_items=todo_items,
        recommended_next_actions=_business_recommended_actions(todo_items, bool(relations)),
        boundary_notes=list(IP_SYSTEM_BOUNDARY_NOTES),
        relations=relations,
        source_configs=get_source_configs(system_id),
        reference_summary=_reference_summary(system_id),
        pending_reviews=pending_reviews,
        match_exceptions=match_exceptions,
        candidates=candidates,
    )


def get_jurisdiction_profile(
    jurisdiction_id: str,
    *,
    include_not_applicable: bool = False,
    include_reserved: bool = False,
    as_of: date | None = None,
) -> IpSystemJurisdictionProfileResponse:
    effective_at = as_of or date.today()
    jurisdiction = _get_jurisdiction_or_raise(jurisdiction_id)
    relations = get_jurisdiction_relations(jurisdiction_id, as_of=effective_at, current_only=True, published_only=True)
    pending_reviews = _jurisdiction_reviews(jurisdiction_id)
    candidates = list_relation_candidates(jurisdiction_id=jurisdiction_id, match_status="matched")
    exceptions = _jurisdiction_exceptions(jurisdiction_id)

    system_ids = {item.system_id for item in relations}
    system_ids.update(item.system_id for item in pending_reviews)
    system_ids.update(item.system_id for item in candidates)
    system_ids.update(item.system_id for item in exceptions)
    if include_not_applicable:
        for system in list_ip_systems(include_inactive=include_reserved):
            if include_reserved or not _is_reserved_system(system.system_code):
                if _is_phase1_system(system.system_code) or include_reserved:
                    system_ids.add(system.system_id)

    systems = {item.system_id: item for item in list_ip_systems(include_inactive=True)}
    cards: list[IpSystemJurisdictionSystemCard] = []
    hidden = 0
    for system_id in sorted(system_ids, key=lambda value: systems.get(value).display_order if systems.get(value) else 999):
        system = systems.get(system_id)
        if not system:
            continue
        if _is_reserved_system(system.system_code) and not include_reserved:
            hidden += 1
            continue
        system_relations = [
            IpSystemBusinessRelationItem.model_validate({
                **item.model_dump(),
                "effective_status": _effective_status(item),
            })
            for item in relations
            if item.system_id == system_id
        ]
        system_reviews = [item for item in pending_reviews if item.system_id == system_id]
        system_candidates = [item for item in candidates if item.system_id == system_id and _candidate_is_phase1(item)]
        system_exceptions = [item for item in exceptions if item.system_id == system_id]
        if not include_not_applicable and not (system_relations or system_reviews or system_candidates or system_exceptions):
            hidden += 1
            continue
        cards.append(IpSystemJurisdictionSystemCard(
            system_id=system.system_id,
            system_code=system.system_code,
            system_name_cn=system.system_name_cn,
            system_category=system.system_category,
            status="current" if system_relations else "pending" if system_reviews or system_candidates or system_exceptions else "not_applicable",
            relations=system_relations,
            pending_reviews=system_reviews,
            candidates=system_candidates,
            match_exceptions=system_exceptions,
            risk_tips=_risk_tips(system_relations, system_reviews, system_candidates, system_exceptions),
        ))

    todo_items = _jurisdiction_todo_items(pending_reviews, candidates, exceptions)
    latest_verified_at = max((item.verified_at for item in relations if item.verified_at), default=None)
    return IpSystemJurisdictionProfileResponse(
        profile=IpSystemJurisdictionProfileCard(
            jurisdiction_id=jurisdiction_id,
            jurisdiction_code=str(jurisdiction.get("display_code") or ""),
            jurisdiction_name_cn=str(jurisdiction.get("name_cn") or ""),
            jurisdiction_name_en=str(jurisdiction.get("name_en") or ""),
            jurisdiction_type=str(jurisdiction.get("jurisdiction_type") or ""),
            current_relation_count=len(relations),
            pending_item_count=len(todo_items),
            latest_verified_at=latest_verified_at,
            data_status="published" if relations else "pending_review" if todo_items else "not_configured",
        ),
        system_cards=cards,
        todo_items=todo_items,
        hidden_not_applicable_count=hidden,
        phase_scope=_phase_scope(),
    )


def get_reference_coverage(
    system_id: str,
    *,
    source_config_id: str | None = None,
    relation_type_code: str | None = None,
    business_domain: str | None = None,
    as_of: date | None = None,
) -> IpSystemReferenceCoverageResponse:
    system = _get_system_or_raise(system_id)
    effective_at = as_of or date.today()
    candidates = list_relation_candidates(source_config_id=source_config_id, system_id=system_id)
    if relation_type_code:
        candidates = [item for item in candidates if item.relation_type_code == relation_type_code]
    if business_domain:
        candidates = [item for item in candidates if item.business_domain == business_domain]
    phase1_candidates = [item for item in candidates if _candidate_is_phase1(item)]
    phase1_candidate_ids = {
        str(item.matched_jurisdiction_id)
        for item in phase1_candidates
        if item.matched_jurisdiction_id
    }
    non_phase1_candidates = [
        item for item in candidates
        if item.matched_jurisdiction_id and not _candidate_is_phase1(item)
    ]
    relations = get_system_relations(
        system_id,
        business_domain=business_domain,
        as_of=effective_at,
        current_only=True,
        published_only=True,
    )
    if relation_type_code:
        relations = [item for item in relations if item.relation_type_code == relation_type_code]
    phase1_published_ids = {
        item.jurisdiction_id
        for item in relations
        if _is_phase1_jurisdiction(item.jurisdiction_code, item.jurisdiction_id)
    }
    pending_reviews = list_change_reviews(system_id=system_id, review_status="pending_review")
    if relation_type_code:
        pending_reviews = [item for item in pending_reviews if item.relation_type_code == relation_type_code]
    if business_domain:
        pending_reviews = [item for item in pending_reviews if item.business_domain == business_domain]
    exceptions = list_match_exceptions(system_id=system_id, source_config_id=source_config_id, status="pending")
    return IpSystemReferenceCoverageResponse(
        system_id=system_id,
        system_code=system.system_code,
        source_config_id=source_config_id,
        relation_type_code=relation_type_code,
        business_domain=business_domain,
        stats=IpSystemReferenceCoverageStats(
            official_reference_total=len(candidates),
            parsed_candidate_count=len(candidates),
            phase1_published_count=len(phase1_published_ids),
            phase1_missing_count=len(phase1_candidate_ids - phase1_published_ids),
            non_phase1_candidate_count=len(non_phase1_candidates),
            pending_review_count=len(pending_reviews),
            match_exception_count=len(exceptions),
        ),
        phase_scope=_phase_scope(),
    )


def get_advanced_workbench() -> IpSystemAdvancedWorkbenchResponse:
    systems = list_ip_systems(include_inactive=True)
    source_configs = _all_source_configs()
    return IpSystemAdvancedWorkbenchResponse(
        phase_scope=_phase_scope(),
        systems=systems,
        relation_types=list_relation_types(include_inactive=True),
        source_configs=source_configs,
        recent_batches=_recent_sync_batches(),
        pending_reviews=list_change_reviews(review_status="pending_review"),
        match_exceptions=list_match_exceptions(status="pending"),
        non_phase1_candidates=_non_phase1_candidates(),
    )


def get_system_relations(
    system_id: str,
    business_domain: str | None = None,
    as_of: date | None = None,
    current_only: bool = True,
    published_only: bool = True,
) -> list[IpSystemRelation]:
    return [
        IpSystemRelation.model_validate(row)
        for row in _fetch_relations(
            system_id=system_id,
            business_domain=business_domain,
            as_of=as_of,
            current_only=current_only,
            published_only=published_only,
            active_systems_only=False,
        )
    ]


def get_jurisdiction_relations(
    jurisdiction_id: str,
    as_of: date | None = None,
    current_only: bool = True,
    published_only: bool = True,
) -> list[IpSystemRelation]:
    return [
        IpSystemRelation.model_validate(row)
        for row in _fetch_relations(
            jurisdiction_id=jurisdiction_id,
            as_of=as_of,
            current_only=current_only,
            published_only=published_only,
            active_systems_only=True,
        )
    ]


def get_jurisdiction_tags(jurisdiction_id: str, as_of: date | None = None) -> list[IpSystemTag]:
    rows = _fetch_relations(
        jurisdiction_id=jurisdiction_id,
        as_of=as_of,
        current_only=True,
        published_only=True,
        active_systems_only=True,
    )
    return [IpSystemTag.model_validate(row) for row in rows]


def get_quote_ip_tags(jurisdiction_id: str, as_of: date | None = None) -> list[QuoteIpTag]:
    rows = _fetch_relations(
        jurisdiction_id=jurisdiction_id,
        as_of=as_of,
        current_only=True,
        published_only=True,
        quote_hint_only=True,
        active_systems_only=True,
    )
    return [QuoteIpTag.model_validate(row) for row in rows]


def check_ip_system_relation(
    jurisdiction_id: str,
    system_code: str,
    relation_type_code: str,
    business_domain: str,
    as_of: date | None = None,
) -> IpSystemCheckResponse:
    rows = _fetch_relations(
        jurisdiction_id=jurisdiction_id,
        system_code=system_code,
        relation_type_code=relation_type_code,
        business_domain=business_domain,
        as_of=as_of,
        current_only=True,
        published_only=True,
        path_dependency_only=False,
        active_systems_only=True,
    )
    relations = [IpSystemRelation.model_validate(row) for row in rows]
    return IpSystemCheckResponse(matched=bool(relations), relation_count=len(relations), relations=relations)


def create_ip_system(payload: IpSystemCreate) -> IpSystem:
    record = payload.model_dump()
    record["system_id"] = f"ip-system-{payload.system_code.lower().replace('_', '-')}-{uuid4().hex[:8]}"
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ip_system_master (
              system_id, system_code, system_name_cn, system_name_en, system_category,
              business_domain_scope, is_active, display_order, default_update_frequency,
              source_priority, source_url, official_source_name, last_verified_at,
              next_review_due_at, remark
            )
            VALUES (
              %(system_id)s, %(system_code)s, %(system_name_cn)s, %(system_name_en)s,
              %(system_category)s, %(business_domain_scope)s, %(is_active)s,
              %(display_order)s, %(default_update_frequency)s, %(source_priority)s,
              %(source_url)s, %(official_source_name)s, %(last_verified_at)s,
              %(next_review_due_at)s, %(remark)s
            )
            """,
            record,
        )
    return _get_system_or_raise(str(record["system_id"]))


def update_ip_system(system_id: str, payload: IpSystemUpdate) -> IpSystem:
    values = payload.model_dump(exclude_unset=True)
    _update_record("ip_system_master", "system_id", system_id, values, {
        "system_name_cn",
        "system_name_en",
        "system_category",
        "business_domain_scope",
        "is_active",
        "display_order",
        "default_update_frequency",
        "source_priority",
        "source_url",
        "official_source_name",
        "last_verified_at",
        "next_review_due_at",
        "remark",
    })
    return _get_system_or_raise(system_id)


def create_business_domain(system_id: str, payload: IpSystemBusinessDomainCreate) -> IpSystemBusinessDomain:
    _get_system_or_raise(system_id)
    record = {
        **payload.model_dump(),
        "id": f"ipbd-{system_id.replace('ip-system-', '')}-{payload.business_domain}-{uuid4().hex[:6]}",
        "system_id": system_id,
    }
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ip_system_business_domain (
              id, system_id, business_domain, is_enabled, quote_hint_default_enabled,
              path_rule_default_dependency, remark
            )
            VALUES (
              %(id)s, %(system_id)s, %(business_domain)s, %(is_enabled)s,
              %(quote_hint_default_enabled)s, %(path_rule_default_dependency)s, %(remark)s
            )
            """,
            record,
        )
    return _get_business_domain_or_raise(str(record["id"]))


def update_business_domain(
    domain_id: str,
    payload: IpSystemBusinessDomainUpdate,
) -> IpSystemBusinessDomain:
    _update_record("ip_system_business_domain", "id", domain_id, payload.model_dump(exclude_unset=True), {
        "is_enabled",
        "quote_hint_default_enabled",
        "path_rule_default_dependency",
        "remark",
    })
    return _get_business_domain_or_raise(domain_id)


def create_relation_type(payload: IpSystemRelationTypeCreate) -> IpSystemRelationType:
    record = {
        **payload.model_dump(),
        "relation_type_id": f"iprt-{payload.relation_type_code.lower().replace('_', '-')}-{uuid4().hex[:8]}",
    }
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ip_system_relation_type (
              relation_type_id, relation_type_code, relation_type_name_cn,
              relation_type_name_en, applicable_system_category, is_active,
              display_order, remark
            )
            VALUES (
              %(relation_type_id)s, %(relation_type_code)s, %(relation_type_name_cn)s,
              %(relation_type_name_en)s, %(applicable_system_category)s, %(is_active)s,
              %(display_order)s, %(remark)s
            )
            """,
            record,
        )
    return _get_relation_type_or_raise(str(record["relation_type_id"]))


def update_relation_type(
    relation_type_id: str,
    payload: IpSystemRelationTypeUpdate,
) -> IpSystemRelationType:
    _update_record("ip_system_relation_type", "relation_type_id", relation_type_id, payload.model_dump(exclude_unset=True), {
        "relation_type_name_cn",
        "relation_type_name_en",
        "applicable_system_category",
        "is_active",
        "display_order",
        "remark",
    })
    return _get_relation_type_or_raise(relation_type_id)


def get_source_configs(system_id: str) -> list[IpSystemSourceConfig]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM ip_system_source_config WHERE system_id = %s ORDER BY is_active DESC, source_name",
            (system_id,),
        )
        return [IpSystemSourceConfig.model_validate(_normalize_record(row)) for row in cursor.fetchall()]


def create_source_config(system_id: str, payload: IpSystemSourceConfigCreate) -> IpSystemSourceConfig:
    _get_system_or_raise(system_id)
    record = {
        **payload.model_dump(),
        "source_config_id": f"ipsc-{system_id.replace('ip-system-', '')}-{uuid4().hex[:8]}",
        "system_id": system_id,
    }
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ip_system_source_config (
              source_config_id, system_id, source_name, source_type, source_url,
              source_scope, official_source_name, parser_key, parse_mode,
              update_frequency, auto_check_enabled, next_check_at,
              is_active, remark
            )
            VALUES (
              %(source_config_id)s, %(system_id)s, %(source_name)s, %(source_type)s,
              %(source_url)s, %(source_scope)s, %(official_source_name)s,
              %(parser_key)s, %(parse_mode)s, %(update_frequency)s,
              %(auto_check_enabled)s, %(next_check_at)s, %(is_active)s,
              %(remark)s
            )
            """,
            record,
        )
    return _get_source_config_or_raise(str(record["source_config_id"]))


def update_source_config(
    source_config_id: str,
    payload: IpSystemSourceConfigUpdate,
) -> IpSystemSourceConfig:
    _update_record("ip_system_source_config", "source_config_id", source_config_id, payload.model_dump(exclude_unset=True), {
        "source_name",
        "source_type",
        "source_url",
        "source_scope",
        "official_source_name",
        "parser_key",
        "parse_mode",
        "update_frequency",
        "auto_check_enabled",
        "last_checked_at",
        "next_check_at",
        "last_success_at",
        "last_failed_at",
        "failure_reason",
        "is_active",
        "remark",
    })
    return _get_source_config_or_raise(source_config_id)


def create_reference_candidates(
    system_id: str,
    payload: IpSystemReferenceCandidateCreate,
    actor: str,
) -> IpSystemReferenceCandidateResponse:
    system = _get_system_or_raise(system_id)
    source_config = (
        _get_source_config_or_raise(payload.source_config_id)
        if payload.source_config_id
        else create_source_config(
            system_id,
            IpSystemSourceConfigCreate(
                source_name=payload.source_name or payload.official_source_name or payload.source_url or "官方来源 Reference",
                source_type=payload.source_type,
                source_url=payload.source_url,
                source_scope=payload.source_scope,
                official_source_name=payload.official_source_name,
                parser_key=payload.parser_key,
                parse_mode=payload.parse_mode,
                update_frequency="manual",
                remark=payload.remark,
            ),
        )
    )
    if source_config.system_id != system_id:
        raise ValueError("IP_SYSTEM_SOURCE_CONFIG_MISMATCH")
    if payload.source_config_id and (
        payload.source_url
        or payload.source_name
        or payload.official_source_name
        or payload.source_scope
        or payload.parse_mode
        or payload.remark
    ):
        source_updates: dict[str, object] = {
            "source_scope": payload.source_scope,
            "parse_mode": payload.parse_mode,
            "last_checked_at": datetime.now(),
        }
        if payload.source_name:
            source_updates["source_name"] = payload.source_name
        if payload.source_url:
            source_updates["source_url"] = payload.source_url
        if payload.official_source_name:
            source_updates["official_source_name"] = payload.official_source_name
        if payload.parser_key:
            source_updates["parser_key"] = payload.parser_key
        if payload.remark:
            source_updates["remark"] = payload.remark
        source_config = update_source_config(
            source_config.source_config_id,
            IpSystemSourceConfigUpdate(**source_updates),
        )

    raw_content = _reference_raw_content(payload)
    snapshot = ip_system_sync_service.create_source_snapshot(
        system_id=system_id,
        source_config_id=source_config.source_config_id,
        snapshot_type=payload.parse_mode,
        raw_snapshot_path=source_config.source_url,
        raw_content=raw_content,
        raw_metadata={
            "parse_mode": payload.parse_mode,
            "business_domain": payload.business_domain,
            "relation_type_code": payload.relation_type_code,
        },
        captured_by=actor,
        remark=payload.remark,
    )
    batch = ip_system_sync_service.create_sync_batch(
        system_id=system_id,
        source_config_id=source_config.source_config_id,
        source_snapshot_id=str(snapshot["snapshot_id"]),
        batch_type="reference_candidate",
        raw_snapshot_path=source_config.source_url,
        created_by=actor,
    )
    relation_type = _relation_type_by_code(payload.relation_type_code)
    if relation_type is None:
        raise KeyError("IP_SYSTEM_RELATION_TYPE_NOT_FOUND")
    _ensure_business_domain_enabled(system_id, payload.business_domain)

    rows = _reference_candidate_rows(payload)
    candidates: list[IpSystemRelationCandidate] = []
    matched_count = 0
    unmatched_count = 0
    for row in rows:
        official_name = str(row["official_name"])
        official_code = str(row["official_code"])
        jurisdiction = _resolve_reference_candidate_jurisdiction(
            system_id=system_id,
            source_config_id=source_config.source_config_id,
            official_name=official_name,
            official_code=official_code,
            jurisdiction_name=official_name,
            matched_jurisdiction_id=row.get("matched_jurisdiction_id"),
        )
        match_status = "matched" if jurisdiction else "unmatched"
        confidence = Decimal("1.0000") if jurisdiction else None
        flags = list(row.get("data_quality_flags") or [])
        if not jurisdiction and "jurisdiction_unmatched" not in flags:
            flags.append("jurisdiction_unmatched")
        if jurisdiction:
            matched_count += 1
        else:
            unmatched_count += 1
            ip_system_sync_service.record_match_exception(
                batch_id=str(batch.batch_id),
                system_id=system_id,
                source_config_id=source_config.source_config_id,
                official_name=official_name,
                official_code=official_code,
                raw_record={
                    "official_name": official_name,
                    "official_code": official_code,
                    "raw_text": str(row["raw_text"]),
                    "business_domain": payload.business_domain,
                    "relation_type_code": payload.relation_type_code,
                    "source_reference": source_config.source_url,
                },
            )
        candidate_id = f"ipcand-{uuid4().hex[:16]}"
        with mysql.connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ip_system_relation_candidate (
                  candidate_id, source_config_id, snapshot_id, batch_id, system_id,
                  business_domain, relation_type_id, official_name, official_code,
                  raw_text, source_url, source_reference, evidence_text,
                  matched_jurisdiction_id, match_status, match_confidence,
                  data_quality_flags_json
                )
                VALUES (
                  %(candidate_id)s, %(source_config_id)s, %(snapshot_id)s,
                  %(batch_id)s, %(system_id)s, %(business_domain)s,
                  %(relation_type_id)s, %(official_name)s, %(official_code)s,
                  %(raw_text)s, %(source_url)s, %(source_reference)s,
                  %(evidence_text)s, %(matched_jurisdiction_id)s,
                  %(match_status)s, %(match_confidence)s,
                  %(data_quality_flags_json)s
                )
                """,
                {
                    "candidate_id": candidate_id,
                    "source_config_id": source_config.source_config_id,
                    "snapshot_id": snapshot["snapshot_id"],
                    "batch_id": batch.batch_id,
                    "system_id": system_id,
                    "business_domain": payload.business_domain,
                    "relation_type_id": relation_type["relation_type_id"],
                    "official_name": official_name,
                    "official_code": official_code,
                    "raw_text": str(row["raw_text"]),
                    "source_url": source_config.source_url,
                    "source_reference": source_config.source_url,
                    "evidence_text": str(row.get("evidence_text") or row["raw_text"]),
                    "matched_jurisdiction_id": jurisdiction.get("jurisdiction_id") if jurisdiction else None,
                    "match_status": match_status,
                    "match_confidence": confidence,
                    "data_quality_flags_json": json.dumps(flags, ensure_ascii=False),
                },
            )
        candidates.extend(list_relation_candidates(candidate_id=candidate_id))

    _finish_reference_batch(batch.batch_id, len(rows), matched_count, unmatched_count)
    refreshed_batch = ip_system_sync_service.get_sync_batch(batch.batch_id)
    return IpSystemReferenceCandidateResponse(
        batch=refreshed_batch,
        snapshot_id=str(snapshot["snapshot_id"]),
        source_config=_get_source_config_or_raise(source_config.source_config_id),
        total_candidates=len(rows),
        matched_count=matched_count,
        unmatched_count=unmatched_count,
        candidates=candidates,
    )


def list_relation_candidates(
    *,
    candidate_id: str | None = None,
    source_config_id: str | None = None,
    system_id: str | None = None,
    jurisdiction_id: str | None = None,
    match_status: str | None = None,
) -> list[IpSystemRelationCandidate]:
    where_parts: list[str] = []
    params: list[object] = []
    if candidate_id:
        where_parts.append("c.candidate_id = %s")
        params.append(candidate_id)
    if source_config_id:
        where_parts.append("c.source_config_id = %s")
        params.append(source_config_id)
    if system_id:
        where_parts.append("c.system_id = %s")
        params.append(system_id)
    if jurisdiction_id:
        where_parts.append("c.matched_jurisdiction_id = %s")
        params.append(jurisdiction_id)
    if match_status:
        where_parts.append("c.match_status = %s")
        params.append(match_status)
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT c.*, s.system_code, s.system_name_cn,
                   COALESCE(rt.relation_type_code, '') AS relation_type_code,
                   COALESCE(rt.relation_type_name_cn, '') AS relation_type_name_cn,
                   COALESCE(j.display_code, '') AS matched_jurisdiction_code,
                   COALESCE(j.name_cn, '') AS matched_jurisdiction_name_cn
            FROM ip_system_relation_candidate c
            JOIN ip_system_master s ON s.system_id = c.system_id
            LEFT JOIN ip_system_relation_type rt ON rt.relation_type_id = c.relation_type_id
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = c.matched_jurisdiction_id
            {where}
            ORDER BY c.created_at DESC
            LIMIT 500
            """,
            tuple(params),
        )
        rows = [_candidate_row(row) for row in cursor.fetchall()]
    return [IpSystemRelationCandidate.model_validate(row) for row in rows]


def get_jurisdiction_reference_check(jurisdiction_id: str) -> IpSystemJurisdictionReferenceCheck:
    published = get_jurisdiction_relations(jurisdiction_id, current_only=True, published_only=True)
    candidates = list_relation_candidates(jurisdiction_id=jurisdiction_id, match_status="matched")
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT cr.*, s.system_code, COALESCE(j.display_code, '') AS jurisdiction_code,
                   COALESCE(j.name_cn, '') AS jurisdiction_name_cn,
                   COALESCE(rt.relation_type_code, '') AS relation_type_code
            FROM ip_system_change_review cr
            JOIN ip_system_master s ON s.system_id = cr.system_id
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = cr.jurisdiction_id
            LEFT JOIN ip_system_relation_type rt ON rt.relation_type_id = cr.relation_type_id
            WHERE cr.jurisdiction_id = %s
              AND cr.review_status IN ('pending_review', 'approved')
            ORDER BY cr.created_at DESC
            LIMIT 200
            """,
            (jurisdiction_id,),
        )
        pending = [IpSystemChangeReview.model_validate(_review_row(row)) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT e.*, s.system_code
            FROM ip_system_match_exception e
            JOIN ip_system_master s ON s.system_id = e.system_id
            WHERE e.status = 'pending'
              AND (e.suggested_jurisdiction_id = %s OR e.resolved_jurisdiction_id = %s)
            ORDER BY e.created_at DESC
            LIMIT 200
            """,
            (jurisdiction_id, jurisdiction_id),
        )
        exceptions = [IpSystemMatchException.model_validate(_match_exception_row(row)) for row in cursor.fetchall()]
    return IpSystemJurisdictionReferenceCheck(
        jurisdiction_id=jurisdiction_id,
        published_relations=published,
        pending_reviews=pending,
        reference_candidates=candidates,
        match_exceptions=exceptions,
    )


def get_jurisdiction_enablement_check(query: str) -> IpSystemEnablementCheckResponse:
    normalized_query = query.strip()
    if not normalized_query:
        return IpSystemEnablementCheckResponse(
            query=query,
            system_statuses=_enablement_system_statuses([], [], [], []),
            recommended_next_actions=[
                IpSystemBusinessActionItem(
                    action_key="input_required",
                    title="请输入国家/地区名称或代码",
                    description="可输入 Germany、DE、德国、WIPO ST.3 或 ISO 代码。",
                    priority=1,
                )
            ],
            boundary_notes=list(IP_SYSTEM_BOUNDARY_NOTES),
        )
    jurisdiction = _find_jurisdiction_for_enablement(normalized_query)
    candidate_hits = _query_relation_candidates(normalized_query, jurisdiction.get("jurisdiction_id") if jurisdiction else None)
    exception_hits = _query_match_exceptions(normalized_query, jurisdiction.get("jurisdiction_id") if jurisdiction else None)
    alias_hits = _query_alias_mappings(normalized_query, jurisdiction.get("jurisdiction_id") if jurisdiction else None)

    published: list[IpSystemRelation] = []
    pending_reviews: list[IpSystemChangeReview] = []
    matched_payload: IpSystemEnablementMatchedJurisdiction | None = None
    master_status = "not_exists"
    phase_scope_status = "not_in_scope"
    if jurisdiction:
        jurisdiction_id = str(jurisdiction["jurisdiction_id"])
        published = get_jurisdiction_relations(jurisdiction_id, current_only=True, published_only=True)
        pending_reviews = _jurisdiction_reviews(jurisdiction_id)
        matched_payload = _enablement_matched_jurisdiction(jurisdiction)
        master_status = _jurisdiction_master_status(jurisdiction)
        phase_scope_status = "in_scope" if _is_phase1_jurisdiction(
            str(jurisdiction.get("display_code") or jurisdiction.get("internal_code") or ""),
            jurisdiction_id,
        ) else "not_in_scope"

    return IpSystemEnablementCheckResponse(
        query=normalized_query,
        matched_jurisdiction=matched_payload,
        master_status=master_status,
        phase_scope_status=phase_scope_status,
        system_statuses=_enablement_system_statuses(
            published,
            candidate_hits,
            pending_reviews,
            exception_hits,
        ),
        published_relations=published,
        reference_candidates=candidate_hits,
        pending_reviews=pending_reviews,
        match_exceptions=exception_hits,
        alias_mappings=alias_hits,
        recommended_next_actions=_enablement_recommended_actions(
            master_status=master_status,
            phase_scope_status=phase_scope_status,
            published=published,
            candidates=candidate_hits,
            pending_reviews=pending_reviews,
            exceptions=exception_hits,
        ),
        boundary_notes=list(IP_SYSTEM_BOUNDARY_NOTES),
    )


def _enablement_system_statuses(
    published: list[IpSystemRelation],
    candidates: list[IpSystemRelationCandidate],
    pending_reviews: list[IpSystemChangeReview],
    exceptions: list[IpSystemMatchException],
) -> list[IpSystemEnablementSystemStatus]:
    systems = [
        system for system in list_ip_systems(include_inactive=True)
        if _is_phase1_system(system.system_code) or _is_reserved_system(system.system_code)
    ]
    published_by_system = _group_by_system_code(published)
    candidates_by_system = _group_by_system_code(candidates)
    reviews_by_system = _group_by_system_code(pending_reviews)
    exceptions_by_system = _group_by_system_code(exceptions)

    statuses: list[IpSystemEnablementSystemStatus] = []
    for system in systems:
        system_published = published_by_system.get(system.system_code, [])
        system_candidates = candidates_by_system.get(system.system_code, [])
        system_reviews = reviews_by_system.get(system.system_code, [])
        system_exceptions = exceptions_by_system.get(system.system_code, [])
        relation_types = _enablement_relation_types(
            system_published,
            system_candidates,
            system_reviews,
        )
        visibility = "default"
        status = "no_hit"
        reason = "当前没有已发布关系、Reference 候选、待审核差异或匹配异常。"

        if _is_reserved_system(system.system_code):
            visibility = "reserved_hidden"
            status = "reserved_hidden"
            reason = "预留体系默认隐藏；不进入第一期默认展示、报价调用或自动发布。"
        elif system_published:
            status = "published"
            reason = "已存在 published/current 正式关系。"
        elif system_reviews:
            status = "pending_review_exists"
            reason = "已有 pending_review 待审核差异；审核后仍需 publish。"
        elif system_exceptions:
            status = "match_exception"
            reason = "存在 match_exception，需要先确认国家/地区主档映射。"
        elif system_candidates:
            if any(item.match_status == "matched" for item in system_candidates):
                status = "reference_hit_unpublished"
                reason = "官方 Reference 已命中但尚未发布；需生成差异审核并发布。"
            else:
                status = "candidate_exists"
                reason = "已有 candidate，但尚未形成可发布的正式关系。"

        statuses.append(IpSystemEnablementSystemStatus(
            system_id=system.system_id,
            system_code=system.system_code,
            system_name=system.system_name_cn,
            status=status,
            relation_types=relation_types,
            visibility=visibility,
            reason=reason,
            published_relations=[item for item in system_published if isinstance(item, IpSystemRelation)],
            reference_candidates=[item for item in system_candidates if isinstance(item, IpSystemRelationCandidate)],
            pending_reviews=[item for item in system_reviews if isinstance(item, IpSystemChangeReview)],
            match_exceptions=[item for item in system_exceptions if isinstance(item, IpSystemMatchException)],
        ))
    return statuses


def _group_by_system_code(items: list[object]) -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = {}
    for item in items:
        system_code = str(getattr(item, "system_code", "") or "")
        if not system_code:
            continue
        grouped.setdefault(system_code, []).append(item)
    return grouped


def _enablement_relation_types(*groups: list[object]) -> list[str]:
    relation_types: set[str] = set()
    for group in groups:
        for item in group:
            relation_type = str(getattr(item, "relation_type_code", "") or "")
            if relation_type:
                relation_types.add(relation_type)
    return sorted(relation_types)


def create_reviews_from_reference_candidates(
    payload: IpSystemReferenceReviewCreate,
    actor: str,
) -> IpSystemReferenceReviewResponse:
    candidate_ids = [item for item in payload.candidate_ids if item.strip()]
    if not candidate_ids:
        return IpSystemReferenceReviewResponse(batch_id="", created_count=0, skipped_count=0, reviews=[])
    placeholders = ", ".join(["%s"] * len(candidate_ids))
    batch_id = f"ipsync-ref-review-{uuid4().hex[:10]}"
    now = datetime.now()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT c.*, s.system_code
            FROM ip_system_relation_candidate c
            JOIN ip_system_master s ON s.system_id = c.system_id
            WHERE c.candidate_id IN ({placeholders})
            FOR UPDATE
            """,
            tuple(candidate_ids),
        )
        rows = [_candidate_row(row) for row in cursor.fetchall()]
        if not rows:
            raise KeyError("IP_SYSTEM_RELATION_CANDIDATE_NOT_FOUND")
        system_ids = {str(row["system_id"]) for row in rows}
        if len(system_ids) != 1:
            raise ValueError("REFERENCE_CANDIDATES_MUST_SHARE_SYSTEM")
        cursor.execute(
            """
            INSERT INTO ip_system_sync_batch (
              batch_id, system_id, source_config_id, batch_type, started_at,
              finished_at, status, total_records_found, created_by
            )
            VALUES (%s, %s, %s, 'reference_candidate_review', %s, %s, 'completed', %s, %s)
            """,
            (
                batch_id,
                rows[0]["system_id"],
                rows[0].get("source_config_id"),
                now,
                now,
                len(rows),
                actor,
            ),
        )

    created = 0
    skipped = 0
    for row in rows:
        jurisdiction_id = payload.jurisdiction_id or row.get("matched_jurisdiction_id")
        if not jurisdiction_id:
            skipped += 1
            continue
        candidate = {
            "system_id": row["system_id"],
            "jurisdiction_id": jurisdiction_id,
            "relation_type_id": row.get("relation_type_id"),
            "business_domain": row.get("business_domain"),
            "source_official_name": row.get("official_name") or "",
            "source_official_code": row.get("official_code") or "",
            "source_reference": row.get("source_reference") or row.get("source_url") or "",
            "source_snapshot_id": row.get("snapshot_id"),
            "data_quality_flags": row.get("data_quality_flags") or [],
            "is_active": True,
            "verification_status": "pending_review",
        }
        change = ip_system_sync_service._build_change_for_candidate(batch_id, candidate)
        if change is None or ip_system_sync_service._pending_review_exists(change):
            skipped += 1
            continue
        change["review_comment"] = payload.review_comment
        ip_system_sync_service.record_change_review(**change)
        created += 1
    reviews = list_change_reviews(batch_id=batch_id)
    _finish_review_batch(batch_id, len(rows), created, skipped)
    return IpSystemReferenceReviewResponse(
        batch_id=batch_id,
        created_count=created,
        skipped_count=skipped,
        reviews=reviews,
    )


def create_manual_relation_review(
    payload: IpSystemManualRelationReviewCreate,
    actor: str,
) -> IpSystemChangeReview:
    now = datetime.now()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ip_system_master WHERE system_id = %s LIMIT 1", (payload.system_id,))
        system = _normalize_record(cursor.fetchone())
        if not system:
            raise KeyError("IP_SYSTEM_NOT_FOUND")
        cursor.execute(
            """
            SELECT relation_type_id
            FROM ip_system_relation_type
            WHERE relation_type_code = %s AND is_active = 1
            LIMIT 1
            """,
            (payload.relation_type_code,),
        )
        relation_type = _normalize_record(cursor.fetchone())
        if not relation_type:
            raise KeyError("IP_SYSTEM_RELATION_TYPE_NOT_FOUND")
        cursor.execute("SELECT jurisdiction_id, display_code, name_cn FROM jurisdictions WHERE jurisdiction_id = %s LIMIT 1", (payload.jurisdiction_id,))
        jurisdiction = _normalize_record(cursor.fetchone())
        if not jurisdiction:
            raise KeyError("JURISDICTION_NOT_FOUND")
        cursor.execute(
            """
            SELECT 1
            FROM ip_system_business_domain
            WHERE system_id = %s AND business_domain = %s AND is_enabled = 1
            LIMIT 1
            """,
            (payload.system_id, payload.business_domain),
        )
        if cursor.fetchone() is None:
            raise ValueError("IP_SYSTEM_BUSINESS_DOMAIN_DISABLED")
        if payload.effective_date and payload.expiry_date and payload.expiry_date < payload.effective_date:
            raise ValueError("INVALID_RELATION_DATE_RANGE")

        batch_id = f"ipsb-manual-{uuid4().hex[:12]}"
        review_id = f"ipcr-manual-{uuid4().hex[:12]}"
        new_value = {
            "jurisdiction_id": payload.jurisdiction_id,
            "system_id": payload.system_id,
            "relation_type_id": relation_type["relation_type_id"],
            "business_domain": payload.business_domain,
            "is_active": payload.is_active,
            "effective_date": payload.effective_date.isoformat() if payload.effective_date else None,
            "expiry_date": payload.expiry_date.isoformat() if payload.expiry_date else None,
            "quote_hint_enabled": payload.quote_hint_enabled,
            "path_rule_dependency": payload.path_rule_dependency,
            "quote_hint_text": payload.quote_hint_text,
            "special_statement": payload.special_statement,
            "source_reference": payload.source_reference,
            "source_official_name": jurisdiction.get("name_cn") or "",
            "source_official_code": jurisdiction.get("display_code") or "",
            "data_quality_flags": payload.data_quality_flags,
            "admin_remark": payload.admin_remark,
        }
        cursor.execute(
            """
            INSERT INTO ip_system_sync_batch (
              batch_id, system_id, batch_type, started_at, finished_at, status,
              total_records_found, new_records_count, created_by
            )
            VALUES (%s, %s, 'manual_single_relation', %s, %s, 'completed', 1, 1, %s)
            """,
            (batch_id, payload.system_id, now, now, actor),
        )
        cursor.execute(
            """
            INSERT INTO ip_system_change_review (
              review_id, batch_id, system_id, jurisdiction_id, relation_type_id,
              business_domain, change_type, old_relation_id, old_value_json,
              new_value_json, source_official_name, source_official_code,
              data_quality_flags_json, review_status, review_comment, created_at
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, 'new_relation', NULL, NULL,
              %s, %s, %s, %s, 'pending_review', %s, %s
            )
            """,
            (
                review_id,
                batch_id,
                payload.system_id,
                payload.jurisdiction_id,
                relation_type["relation_type_id"],
                payload.business_domain,
                json.dumps(new_value, ensure_ascii=False),
                jurisdiction.get("name_cn") or "",
                jurisdiction.get("display_code") or "",
                json.dumps(payload.data_quality_flags, ensure_ascii=False),
                payload.review_comment,
                now,
            ),
        )
    reviews = list_change_reviews(batch_id=batch_id)
    if not reviews:
        raise KeyError(review_id)
    return reviews[0]


def list_change_reviews(
    batch_id: str | None = None,
    system_id: str | None = None,
    review_status: str | None = None,
) -> list[IpSystemChangeReview]:
    where_parts: list[str] = []
    params: list[object] = []
    if batch_id:
        where_parts.append("cr.batch_id = %s")
        params.append(batch_id)
    if system_id:
        where_parts.append("cr.system_id = %s")
        params.append(system_id)
    if review_status:
        where_parts.append("cr.review_status = %s")
        params.append(review_status)
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT cr.*, s.system_code, COALESCE(j.display_code, '') AS jurisdiction_code,
                   COALESCE(j.name_cn, '') AS jurisdiction_name_cn,
                   COALESCE(rt.relation_type_code, '') AS relation_type_code
            FROM ip_system_change_review cr
            JOIN ip_system_master s ON s.system_id = cr.system_id
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = cr.jurisdiction_id
            LEFT JOIN ip_system_relation_type rt ON rt.relation_type_id = cr.relation_type_id
            {where}
            ORDER BY cr.created_at DESC
            LIMIT 300
            """,
            tuple(params),
        )
        rows = [_review_row(row) for row in cursor.fetchall()]
    return [IpSystemChangeReview.model_validate(row) for row in rows]


def update_change_review(
    review_id: str,
    payload: IpSystemChangeReviewUpdate,
    actor: str,
) -> IpSystemChangeReview:
    now = datetime.now()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ip_system_change_review
            SET review_status = %s, reviewed_by = %s, reviewed_at = %s, review_comment = %s
            WHERE review_id = %s
            """,
            (payload.review_status, actor, now, payload.review_comment, review_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(review_id)
    rows = list_change_reviews()
    for row in rows:
        if row.review_id == review_id:
            return row
    raise KeyError(review_id)


def publish_batch(
    batch_id: str,
    payload: IpSystemPublishBatchRequest,
    actor: str,
    can_auto_approve: bool,
) -> IpSystemPublishBatchResponse:
    now = datetime.now()
    review_ids = set(payload.review_ids)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ip_system_sync_batch WHERE batch_id = %s LIMIT 1", (batch_id,))
        if cursor.fetchone() is None:
            raise KeyError(batch_id)
        where_ids = ""
        params: list[object] = [batch_id]
        if review_ids:
            placeholders = ", ".join(["%s"] * len(review_ids))
            where_ids = f"AND review_id IN ({placeholders})"
            params.extend(sorted(review_ids))
        cursor.execute(
            f"""
            SELECT *
            FROM ip_system_change_review
            WHERE batch_id = %s
              AND review_status IN ('approved', 'pending_review')
              {where_ids}
            ORDER BY created_at
            FOR UPDATE
            """,
            tuple(params),
        )
        reviews = [_review_row(row) for row in cursor.fetchall()]
        published_ids: list[str] = []
        skipped = 0
        for review in reviews:
            if review["review_status"] == "pending_review":
                if not (payload.auto_approve_pending and can_auto_approve):
                    skipped += 1
                    continue
                cursor.execute(
                    """
                    UPDATE ip_system_change_review
                    SET review_status = 'approved',
                        reviewed_by = %s,
                        reviewed_at = %s,
                        review_comment = %s
                    WHERE review_id = %s
                    """,
                    (actor, now, payload.review_comment, review["review_id"]),
                )
            relation_id = _publish_review_with_cursor(cursor, review, actor, now)
            cursor.execute(
                """
                UPDATE ip_system_change_review
                SET review_status = 'published',
                    published_by = %s,
                    published_at = %s,
                    reviewed_by = COALESCE(reviewed_by, %s),
                    reviewed_at = COALESCE(reviewed_at, %s)
                WHERE review_id = %s
                """,
                (actor, now, actor, now, review["review_id"]),
            )
            published_ids.append(str(review["review_id"]))
        cursor.execute(
            """
            UPDATE ip_system_sync_batch
            SET status = 'published',
                finished_at = COALESCE(finished_at, %s)
            WHERE batch_id = %s
            """,
            (now, batch_id),
        )
    return IpSystemPublishBatchResponse(
        batch_id=batch_id,
        published_count=len(published_ids),
        skipped_count=skipped,
        published_review_ids=published_ids,
    )


def list_match_exceptions(
    system_id: str | None = None,
    source_config_id: str | None = None,
    status: str | None = None,
) -> list[IpSystemMatchException]:
    where_parts: list[str] = []
    params: list[object] = []
    if system_id:
        where_parts.append("e.system_id = %s")
        params.append(system_id)
    if source_config_id:
        where_parts.append("e.source_config_id = %s")
        params.append(source_config_id)
    if status:
        where_parts.append("e.status = %s")
        params.append(status)
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT e.*, s.system_code
            FROM ip_system_match_exception e
            JOIN ip_system_master s ON s.system_id = e.system_id
            {where}
            ORDER BY e.created_at DESC
            LIMIT 300
            """,
            tuple(params),
        )
        rows = [_match_exception_row(row) for row in cursor.fetchall()]
    return [IpSystemMatchException.model_validate(row) for row in rows]


def update_match_exception(
    exception_id: str,
    payload: IpSystemMatchExceptionUpdate,
    actor: str,
) -> IpSystemMatchException:
    now = datetime.now()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM ip_system_match_exception WHERE exception_id = %s LIMIT 1 FOR UPDATE",
            (exception_id,),
        )
        exception = _normalize_record(cursor.fetchone())
        if not exception:
            raise KeyError(exception_id)
        cursor.execute(
            """
            UPDATE ip_system_match_exception
            SET status = %s,
                resolved_jurisdiction_id = %s,
                resolved_by = %s,
                resolved_at = %s,
                resolution_comment = %s
            WHERE exception_id = %s
            """,
            (
                payload.status,
                payload.resolved_jurisdiction_id,
                actor,
                now,
                payload.resolution_comment,
                exception_id,
            ),
        )
        if payload.status == "confirmed" and payload.create_alias_mapping:
            cursor.execute(
                """
                INSERT INTO ip_system_jurisdiction_alias_mapping (
                  mapping_id, source_config_id, system_id, official_name, official_code,
                  jurisdiction_id, match_method, confidence_score, is_confirmed,
                  confirmed_by, confirmed_at, remark
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'manual_confirmed', %s, 1, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  jurisdiction_id = VALUES(jurisdiction_id),
                  match_method = VALUES(match_method),
                  confidence_score = VALUES(confidence_score),
                  is_confirmed = VALUES(is_confirmed),
                  confirmed_by = VALUES(confirmed_by),
                  confirmed_at = VALUES(confirmed_at),
                  remark = VALUES(remark)
                """,
                (
                    f"ipalias-{uuid4().hex[:16]}",
                    exception.get("source_config_id"),
                    exception["system_id"],
                    exception.get("official_name") or "",
                    exception.get("official_code") or "",
                    payload.resolved_jurisdiction_id,
                    exception.get("confidence_score"),
                    actor,
                    now,
                    payload.resolution_comment,
                ),
            )
    rows = list_match_exceptions()
    for row in rows:
        if row.exception_id == exception_id:
            return row
    raise KeyError(exception_id)


def _fetch_relations(
    *,
    system_id: str | None = None,
    system_code: str | None = None,
    jurisdiction_id: str | None = None,
    relation_type_code: str | None = None,
    business_domain: str | None = None,
    as_of: date | None = None,
    current_only: bool = True,
    published_only: bool = True,
    quote_hint_only: bool = False,
    path_dependency_only: bool = False,
    active_systems_only: bool = True,
) -> list[dict[str, object]]:
    where_parts: list[str] = []
    params: list[object] = []
    if system_id:
        where_parts.append("r.system_id = %s")
        params.append(system_id)
    if system_code:
        where_parts.append("s.system_code = %s")
        params.append(system_code)
    if jurisdiction_id:
        where_parts.append("r.jurisdiction_id = %s")
        params.append(jurisdiction_id)
    if relation_type_code:
        where_parts.append("rt.relation_type_code = %s")
        params.append(relation_type_code)
    if business_domain:
        where_parts.append("r.business_domain = %s")
        params.append(business_domain)
    if published_only:
        where_parts.append("r.publish_status = 'published'")
    if quote_hint_only:
        where_parts.append("r.quote_hint_enabled = 1")
    if path_dependency_only:
        where_parts.append("r.path_rule_dependency = 1")
    if active_systems_only:
        where_parts.append("s.is_active = 1")
    if current_only:
        effective_at = as_of or date.today()
        where_parts.append("r.is_active = 1")
        where_parts.append("(r.effective_date IS NULL OR r.effective_date <= %s)")
        where_parts.append("(r.expiry_date IS NULL OR r.expiry_date >= %s)")
        where_parts.append("j.is_enabled = 1")
        where_parts.append("COALESCE(j.is_deleted, 0) = 0")
        params.extend([effective_at, effective_at])
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT r.*, j.display_code AS jurisdiction_code,
                   j.name_cn AS jurisdiction_name_cn,
                   j.name_en AS jurisdiction_name_en,
                   s.system_code, s.system_name_cn, s.system_name_en, s.system_category,
                   rt.relation_type_code, rt.relation_type_name_cn
            FROM jurisdiction_ip_system_relation r
            JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            JOIN ip_system_master s ON s.system_id = r.system_id
            JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
            {where}
            ORDER BY s.display_order, r.business_domain, j.display_order, j.display_code,
                     rt.display_order, r.effective_date
            LIMIT 1000
            """,
            tuple(params),
        )
        rows = [_relation_row(row, as_of or date.today()) for row in cursor.fetchall()]
    return rows


def _phase_scope() -> IpSystemV1PhaseScope:
    return IpSystemV1PhaseScope(
        phase1_system_codes=list(PHASE1_SYSTEM_CODES),
        reserved_system_codes=list(RESERVED_SYSTEM_CODES),
        phase1_jurisdiction_codes=list(PHASE1_JURISDICTION_CODES),
    )


def _is_phase1_system(system_code: str) -> bool:
    return system_code.upper() in PHASE1_SYSTEM_CODES


def _is_reserved_system(system_code: str) -> bool:
    return system_code.upper() in RESERVED_SYSTEM_CODES


def _is_phase1_jurisdiction(display_code: str | None, jurisdiction_id: str | None = None) -> bool:
    code = (display_code or "").upper()
    normalized_id = (jurisdiction_id or "").replace("jur-", "").upper()
    return code in PHASE1_JURISDICTION_CODES or normalized_id in PHASE1_JURISDICTION_CODES


def _business_dashboard_item(system: IpSystem, as_of: date) -> IpSystemBusinessDashboardItem:
    relations = get_system_relations(system.system_id, as_of=as_of, current_only=True, published_only=True)
    pending_reviews = list_change_reviews(system_id=system.system_id, review_status="pending_review")
    exceptions = list_match_exceptions(system_id=system.system_id, status="pending")
    reference_summary = _reference_summary(system.system_id)
    todo = IpSystemBusinessTodoSummary(
        pending_review_count=len(pending_reviews),
        match_exception_count=len(exceptions),
        candidate_count=reference_summary.candidate_count,
        non_phase1_candidate_count=reference_summary.non_phase1_candidate_count,
        has_overdue_review=bool(system.next_review_due_at and system.next_review_due_at <= datetime.now()),
    )
    return IpSystemBusinessDashboardItem(
        system_id=system.system_id,
        system_code=system.system_code,
        system_name_cn=system.system_name_cn,
        system_name_en=system.system_name_en,
        system_category=system.system_category,
        business_domain_scope=system.business_domain_scope,
        business_domains=system.business_domains,
        management_agency=system.official_source_name or _first_source_agency(system.system_id),
        is_active=system.is_active,
        is_phase1_default=_is_phase1_system(system.system_code),
        is_reserved=_is_reserved_system(system.system_code),
        current_relation_count=len(relations),
        relation_type_counts=_relation_type_counts(relations),
        todo_summary=todo,
        reference_summary=reference_summary,
        data_status=_business_data_status(len(relations), todo, reference_summary),
        last_verified_at=system.last_verified_at,
        next_review_due_at=system.next_review_due_at,
        remark=system.remark,
    )


def _business_data_status(
    current_relation_count: int,
    todo: IpSystemBusinessTodoSummary,
    reference: IpSystemBusinessReferenceSummary,
) -> str:
    if current_relation_count:
        return "published"
    if todo.pending_review_count or todo.match_exception_count:
        return "pending_review"
    if reference.candidate_count:
        return "candidate_only"
    return "not_configured"


def _reference_summary(system_id: str) -> IpSystemBusinessReferenceSummary:
    candidates = list_relation_candidates(system_id=system_id)
    phase1_candidates = [item for item in candidates if _candidate_is_phase1(item)]
    non_phase1_candidates = [
        item for item in candidates
        if item.matched_jurisdiction_id and not _candidate_is_phase1(item)
    ]
    unmatched_candidates = [item for item in candidates if item.match_status != "matched"]
    source_count, latest_snapshot_at, latest_sync_at = _source_stats(system_id)
    return IpSystemBusinessReferenceSummary(
        source_config_count=source_count,
        candidate_count=len(candidates),
        phase1_candidate_count=len(phase1_candidates),
        non_phase1_candidate_count=len(non_phase1_candidates),
        unmatched_candidate_count=len(unmatched_candidates),
        latest_snapshot_at=latest_snapshot_at,
        latest_sync_at=latest_sync_at,
    )


def _candidate_is_phase1(candidate: IpSystemRelationCandidate) -> bool:
    return _is_phase1_jurisdiction(candidate.matched_jurisdiction_code or candidate.official_code, candidate.matched_jurisdiction_id)


def _business_relation_summary_buckets(
    relations: list[IpSystemBusinessRelationItem],
) -> list[IpSystemBusinessRelationSummaryBucket]:
    current = [item for item in relations if item.is_current_effective]
    used_codes: set[str] = set()
    buckets: list[IpSystemBusinessRelationSummaryBucket] = []
    for key, label, codes in BUSINESS_RELATION_SUMMARY_BUCKETS:
        code_set = set(codes)
        used_codes.update(code_set)
        bucket_relations = [item for item in current if item.relation_type_code in code_set]
        buckets.append(IpSystemBusinessRelationSummaryBucket(
            key=key,
            label=label,
            count=_unique_jurisdiction_count(bucket_relations),
            examples=_relation_examples(bucket_relations),
            relation_type_codes=list(codes),
        ))
    other_relations = [item for item in current if item.relation_type_code not in used_codes]
    buckets.append(IpSystemBusinessRelationSummaryBucket(
        key="other_published_relations",
        label="其他已发布关系",
        count=_unique_jurisdiction_count(other_relations),
        examples=_relation_examples(other_relations),
        relation_type_codes=sorted({item.relation_type_code for item in other_relations if item.relation_type_code}),
    ))
    return buckets


def _business_todo_items(
    reviews: list[IpSystemChangeReview],
    candidates: list[IpSystemRelationCandidate],
    exceptions: list[IpSystemMatchException],
    system_code: str,
) -> list[IpSystemBusinessTodoItem]:
    items: list[IpSystemBusinessTodoItem] = []
    if exceptions:
        items.append(IpSystemBusinessTodoItem(
            item_type="match_exception",
            title="匹配异常",
            count=len(exceptions),
            description="先确认官方名称/代码与 jurisdiction_id 的映射，再生成或重跑候选差异。",
            action_key="resolve_match_exception",
            priority=1,
        ))
    if reviews:
        items.append(IpSystemBusinessTodoItem(
            item_type="pending_review",
            title="待审核差异",
            count=len(reviews),
            description="审核通过后仍需 publish，发布后才进入正式 published/current 关系。",
            action_key="review_publish",
            priority=2,
        ))
    phase1_candidates = [item for item in candidates if _candidate_is_phase1(item)]
    if phase1_candidates:
        items.append(IpSystemBusinessTodoItem(
            item_type="candidate",
            title="官方 Reference 候选",
            count=len(phase1_candidates),
            description="候选不能视为正式关系，请先生成待审核差异。",
            action_key="generate_review",
            priority=3,
        ))
    non_phase1_count = len([item for item in candidates if item.matched_jurisdiction_id and not _candidate_is_phase1(item)])
    if non_phase1_count:
        items.append(IpSystemBusinessTodoItem(
            item_type="non_phase1_candidate",
            title="非第一期对象候选",
            count=non_phase1_count,
            description=f"{system_code} 命中了非第一期对象；当前默认维护范围由后端配置控制。",
            action_key="scope_required",
            priority=4,
        ))
    return sorted(items, key=lambda item: item.priority)


def _business_recommended_actions(
    todo_items: list[IpSystemBusinessTodoItem],
    has_published_relations: bool,
) -> list[IpSystemBusinessActionItem]:
    action_by_todo = {
        "match_exception": IpSystemBusinessActionItem(
            action_key="resolve_match_exception",
            title="先处理匹配异常",
            description="无法匹配 jurisdiction_id 或名称/代码冲突时，先确认映射再继续审核发布。",
            priority=1,
        ),
        "pending_review": IpSystemBusinessActionItem(
            action_key="review_publish",
            title="审核并发布已确认差异",
            description="approve 后继续 publish，不能绕过 candidate / review / publish 闭环。",
            priority=2,
        ),
        "candidate": IpSystemBusinessActionItem(
            action_key="generate_review",
            title="将官方 Reference 候选生成待审核差异",
            description="候选命中不等于正式关系，需进入 manual review / pending_review。",
            priority=3,
        ),
        "non_phase1_candidate": IpSystemBusinessActionItem(
            action_key="scope_required",
            title="确认非第一期对象的维护范围",
            description="V1-A-Repair 仅提示范围状态，不提供管理员配置 phase scope。",
            priority=4,
        ),
    }
    actions = [action_by_todo[item.item_type] for item in todo_items if item.item_type in action_by_todo]
    if not actions and not has_published_relations:
        actions.append(IpSystemBusinessActionItem(
            action_key="add_reference",
            title="补充官方 Reference",
            description="从官方来源生成候选，再进入审核发布。",
            priority=5,
        ))
    if not actions:
        actions.append(IpSystemBusinessActionItem(
            action_key="published",
            title="当前正式关系已发布",
            description="如需变更，仍从官方 Reference 生成候选并走审核发布。",
            priority=10,
        ))
    return sorted(actions, key=lambda item: item.priority)


def _unique_jurisdiction_count(relations: list[IpSystemBusinessRelationItem]) -> int:
    return len({item.jurisdiction_id for item in relations})


def _relation_examples(relations: list[IpSystemBusinessRelationItem], limit: int = 5) -> list[str]:
    examples: list[str] = []
    seen: set[str] = set()
    for relation in relations:
        label = relation.jurisdiction_code or relation.jurisdiction_name_cn or relation.jurisdiction_id
        if label in seen:
            continue
        seen.add(label)
        examples.append(label)
        if len(examples) >= limit:
            break
    return examples


def _relation_type_counts(relations: list[IpSystemRelation] | list[IpSystemBusinessRelationItem]) -> dict[str, int]:
    counts: dict[str, set[str]] = {}
    for relation in relations:
        if not relation.is_current_effective:
            continue
        counts.setdefault(relation.relation_type_code, set()).add(relation.jurisdiction_id)
    return {key: len(value) for key, value in sorted(counts.items())}


def _effective_status(relation: IpSystemRelation) -> str:
    today = date.today()
    if relation.is_current_effective:
        return "current"
    if relation.effective_date and relation.effective_date > today:
        return "future"
    return "expired"


def _risk_tips(
    relations: list[IpSystemBusinessRelationItem],
    reviews: list[IpSystemChangeReview],
    candidates: list[IpSystemRelationCandidate],
    exceptions: list[IpSystemMatchException],
) -> list[str]:
    tips: list[str] = []
    if any(item.verification_status == "pending_review" for item in relations):
        tips.append("存在待复核正式关系")
    if reviews:
        tips.append("存在待审核差异")
    if candidates:
        tips.append("存在官方来源候选，尚未发布")
    if exceptions:
        tips.append("存在匹配异常")
    return tips


def _jurisdiction_todo_items(
    reviews: list[IpSystemChangeReview],
    candidates: list[IpSystemRelationCandidate],
    exceptions: list[IpSystemMatchException],
) -> list[IpSystemJurisdictionTodoItem]:
    items: list[IpSystemJurisdictionTodoItem] = []
    for review in reviews:
        items.append(IpSystemJurisdictionTodoItem(
            item_type="pending_review",
            system_id=review.system_id,
            system_code=review.system_code,
            relation_type_code=review.relation_type_code,
            title="待审核差异",
            status=review.review_status,
        ))
    for candidate in candidates:
        if not _candidate_is_phase1(candidate):
            continue
        items.append(IpSystemJurisdictionTodoItem(
            item_type="candidate",
            system_id=candidate.system_id,
            system_code=candidate.system_code,
            relation_type_code=candidate.relation_type_code,
            title="官方来源候选",
            status=candidate.match_status,
            source_reference=candidate.source_reference,
        ))
    for exception in exceptions:
        items.append(IpSystemJurisdictionTodoItem(
            item_type="match_exception",
            system_id=exception.system_id,
            system_code=exception.system_code,
            title="匹配异常",
            status=exception.status,
        ))
    return items


def _jurisdiction_reviews(jurisdiction_id: str) -> list[IpSystemChangeReview]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT cr.*, s.system_code, COALESCE(j.display_code, '') AS jurisdiction_code,
                   COALESCE(j.name_cn, '') AS jurisdiction_name_cn,
                   COALESCE(rt.relation_type_code, '') AS relation_type_code
            FROM ip_system_change_review cr
            JOIN ip_system_master s ON s.system_id = cr.system_id
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = cr.jurisdiction_id
            LEFT JOIN ip_system_relation_type rt ON rt.relation_type_id = cr.relation_type_id
            WHERE cr.jurisdiction_id = %s
              AND cr.review_status = 'pending_review'
            ORDER BY cr.created_at DESC
            LIMIT 200
            """,
            (jurisdiction_id,),
        )
        return [IpSystemChangeReview.model_validate(_review_row(row)) for row in cursor.fetchall()]


def _jurisdiction_exceptions(jurisdiction_id: str) -> list[IpSystemMatchException]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT e.*, s.system_code
            FROM ip_system_match_exception e
            JOIN ip_system_master s ON s.system_id = e.system_id
            WHERE e.status = 'pending'
              AND (e.suggested_jurisdiction_id = %s OR e.resolved_jurisdiction_id = %s)
            ORDER BY e.created_at DESC
            LIMIT 200
            """,
            (jurisdiction_id, jurisdiction_id),
        )
        return [IpSystemMatchException.model_validate(_match_exception_row(row)) for row in cursor.fetchall()]


def _find_jurisdiction_for_enablement(query: str) -> dict[str, object] | None:
    code = query.strip().upper()
    normalized_name = _normalize_enablement_text(query)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM jurisdictions
            WHERE UPPER(jurisdiction_id) = %s
               OR UPPER(display_code) = %s
               OR UPPER(internal_code) = %s
               OR UPPER(COALESCE(wipo_st3_code, '')) = %s
               OR UPPER(COALESCE(iso_alpha2, '')) = %s
               OR UPPER(COALESCE(iso_alpha3, '')) = %s
               OR name_cn = %s
               OR name_en = %s
            ORDER BY COALESCE(is_deleted, 0), is_enabled DESC, display_order
            LIMIT 1
            """,
            (code, code, code, code, code, code, query, query),
        )
        row = cursor.fetchone()
        if row:
            return _normalize_record(row)
        cursor.execute("SELECT * FROM jurisdictions ORDER BY COALESCE(is_deleted, 0), is_enabled DESC, display_order")
        for candidate in cursor.fetchall():
            if _normalize_enablement_text(str(candidate.get("name_cn") or "")) == normalized_name:
                return _normalize_record(candidate)
            if _normalize_enablement_text(str(candidate.get("name_en") or "")) == normalized_name:
                return _normalize_record(candidate)
            if _normalize_enablement_text(str(candidate.get("display_code") or "")) == normalized_name:
                return _normalize_record(candidate)
    return None


def _query_relation_candidates(query: str, jurisdiction_id: object | None) -> list[IpSystemRelationCandidate]:
    where_parts = [
        "(UPPER(c.official_code) = %s OR c.official_name = %s OR c.raw_text LIKE %s OR c.evidence_text LIKE %s)"
    ]
    params: list[object] = [query.upper(), query, f"%{query}%", f"%{query}%"]
    if jurisdiction_id:
        where_parts.append("c.matched_jurisdiction_id = %s")
        params.append(str(jurisdiction_id))
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT c.*, s.system_code, s.system_name_cn,
                   COALESCE(rt.relation_type_code, '') AS relation_type_code,
                   COALESCE(rt.relation_type_name_cn, '') AS relation_type_name_cn,
                   COALESCE(j.display_code, '') AS matched_jurisdiction_code,
                   COALESCE(j.name_cn, '') AS matched_jurisdiction_name_cn
            FROM ip_system_relation_candidate c
            JOIN ip_system_master s ON s.system_id = c.system_id
            LEFT JOIN ip_system_relation_type rt ON rt.relation_type_id = c.relation_type_id
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = c.matched_jurisdiction_id
            WHERE {' OR '.join(where_parts)}
            ORDER BY c.created_at DESC
            LIMIT 200
            """,
            tuple(params),
        )
        rows = [_candidate_row(row) for row in cursor.fetchall()]
    unique: dict[str, IpSystemRelationCandidate] = {}
    for row in rows:
        item = IpSystemRelationCandidate.model_validate(row)
        unique[item.candidate_id] = item
    return list(unique.values())


def _query_match_exceptions(query: str, jurisdiction_id: object | None) -> list[IpSystemMatchException]:
    where_parts = ["(UPPER(e.official_code) = %s OR e.official_name = %s)"]
    params: list[object] = [query.upper(), query]
    if jurisdiction_id:
        where_parts.append("(e.suggested_jurisdiction_id = %s OR e.resolved_jurisdiction_id = %s)")
        params.extend([str(jurisdiction_id), str(jurisdiction_id)])
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT e.*, s.system_code
            FROM ip_system_match_exception e
            JOIN ip_system_master s ON s.system_id = e.system_id
            WHERE e.status = 'pending'
              AND ({' OR '.join(where_parts)})
            ORDER BY e.created_at DESC
            LIMIT 200
            """,
            tuple(params),
        )
        rows = [_match_exception_row(row) for row in cursor.fetchall()]
    unique: dict[str, IpSystemMatchException] = {}
    for row in rows:
        item = IpSystemMatchException.model_validate(row)
        unique[item.exception_id] = item
    return list(unique.values())


def _query_alias_mappings(query: str, jurisdiction_id: object | None) -> list[dict[str, object]]:
    if not _table_exists("ip_system_jurisdiction_alias_mapping"):
        return []
    where_parts = ["(UPPER(m.official_code) = %s OR m.official_name = %s)"]
    params: list[object] = [query.upper(), query]
    if jurisdiction_id:
        where_parts.append("m.jurisdiction_id = %s")
        params.append(str(jurisdiction_id))
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT m.*, s.system_code, COALESCE(j.display_code, '') AS jurisdiction_code,
                   COALESCE(j.name_cn, '') AS jurisdiction_name_cn
            FROM ip_system_jurisdiction_alias_mapping m
            JOIN ip_system_master s ON s.system_id = m.system_id
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = m.jurisdiction_id
            WHERE {' OR '.join(where_parts)}
            ORDER BY m.confirmed_at DESC, m.created_at DESC
            LIMIT 100
            """,
            tuple(params),
        )
        return [_json_ready_record(row) for row in cursor.fetchall()]


def _enablement_matched_jurisdiction(row: dict[str, object]) -> IpSystemEnablementMatchedJurisdiction:
    return IpSystemEnablementMatchedJurisdiction(
        jurisdiction_id=str(row.get("jurisdiction_id") or ""),
        jurisdiction_code=str(row.get("display_code") or row.get("internal_code") or ""),
        jurisdiction_name_cn=str(row.get("name_cn") or ""),
        jurisdiction_name_en=str(row.get("name_en") or ""),
        jurisdiction_type=str(row.get("jurisdiction_type") or ""),
        is_enabled=bool(row.get("is_enabled")) if row.get("is_enabled") is not None else None,
        is_deleted=bool(row.get("is_deleted")) if row.get("is_deleted") is not None else False,
    )


def _jurisdiction_master_status(row: dict[str, object]) -> str:
    if bool(row.get("is_deleted")):
        return "deleted"
    if not bool(row.get("is_enabled")):
        return "inactive"
    return "active"


def _enablement_recommended_actions(
    *,
    master_status: str,
    phase_scope_status: str,
    published: list[IpSystemRelation],
    candidates: list[IpSystemRelationCandidate],
    pending_reviews: list[IpSystemChangeReview],
    exceptions: list[IpSystemMatchException],
) -> list[IpSystemBusinessActionItem]:
    actions: list[IpSystemBusinessActionItem] = []
    if master_status == "not_exists":
        actions.append(IpSystemBusinessActionItem(
            action_key="create_master_required",
            title="请先创建国家主档，或生成国家主档补录任务说明",
            description="本模块不创建国家主档；需要先取得稳定 jurisdiction_id。",
            priority=1,
        ))
        if candidates:
            actions.append(IpSystemBusinessActionItem(
                action_key="reference_candidate_found",
                title="已命中 Reference 候选，但缺少国家主档",
                description="先处理国家主档，再从候选生成待审核差异。",
                priority=2,
            ))
        if not candidates and not exceptions:
            actions.append(IpSystemBusinessActionItem(
                action_key="supplement_reference_required",
                title="补充官方 Reference 或粘贴官方名单",
                description="当前输入未命中国家主档，也未命中已维护 Reference。",
                priority=3,
            ))
        return actions
    if master_status == "deleted":
        actions.append(IpSystemBusinessActionItem(
            action_key="restore_master_required",
            title="国家主档已删除，请先恢复或重建主档",
            description="V1-A-Repair 不跨模块恢复国家主档。",
            priority=1,
        ))
    elif master_status == "inactive":
        actions.append(IpSystemBusinessActionItem(
            action_key="activate_master_required",
            title="国家主档未启用，请先处理主档状态",
            description="关系维护前需确认对象处于可维护状态。",
            priority=1,
        ))
    if phase_scope_status != "in_scope":
        actions.append(IpSystemBusinessActionItem(
            action_key="scope_required",
            title="请加入维护范围后继续处理关系",
            description="V1-A-Repair 只提示当前第一期范围；管理员可配置 phase scope 属于 V1-B。",
            priority=2,
        ))
    if exceptions:
        actions.append(IpSystemBusinessActionItem(
            action_key="resolve_match_exception_required",
            title="先处理匹配异常",
            description="确认 jurisdiction_id 映射后再生成审核差异。",
            priority=3,
        ))
    if pending_reviews:
        actions.append(IpSystemBusinessActionItem(
            action_key="review_publish_required",
            title="进入审核发布",
            description="存在 pending_review；approve 后还需 publish 才会成为正式关系。",
            priority=4,
        ))
    unpublished_candidates = _unpublished_candidates(candidates, published, pending_reviews)
    if unpublished_candidates:
        actions.append(IpSystemBusinessActionItem(
            action_key="generate_review_or_publish",
            title="生成差异审核",
            description="Reference 候选存在但尚未发布，请生成 pending_review 并走审核发布。",
            priority=5,
        ))
    if published:
        actions.append(IpSystemBusinessActionItem(
            action_key="published",
            title="已有 published/current 正式关系",
            description="国家主档标签将从已发布关系自动带出。",
            priority=6,
        ))
    if not published and not candidates and not pending_reviews and not exceptions:
        actions.append(IpSystemBusinessActionItem(
            action_key="supplement_reference_required",
            title="补充官方 Reference 或粘贴官方名单",
            description="当前无 Reference 命中，不能绕过候选/审核/发布直接写正式关系。",
            priority=7,
        ))
    return sorted(actions, key=lambda item: item.priority)


def _unpublished_candidates(
    candidates: list[IpSystemRelationCandidate],
    published: list[IpSystemRelation],
    pending_reviews: list[IpSystemChangeReview],
) -> list[IpSystemRelationCandidate]:
    published_keys = {
        (item.system_id, item.business_domain, item.relation_type_id)
        for item in published
    }
    pending_keys = {
        (item.system_id, item.business_domain, item.relation_type_id)
        for item in pending_reviews
    }
    return [
        item for item in candidates
        if (item.system_id, item.business_domain, item.relation_type_id) not in published_keys
        and (item.system_id, item.business_domain, item.relation_type_id) not in pending_keys
    ]


def _normalize_enablement_text(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _table_exists(table_name: str) -> bool:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return cursor.fetchone() is not None


def _json_ready_record(row: dict[str, object]) -> dict[str, object]:
    normalized = _normalize_record(row)
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in normalized.items()
    }


def _get_jurisdiction_or_raise(jurisdiction_id: str) -> dict[str, object]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM jurisdictions WHERE jurisdiction_id = %s LIMIT 1", (jurisdiction_id,))
        row = _normalize_record(cursor.fetchone())
    if not row:
        raise KeyError(jurisdiction_id)
    return row


def _first_source_agency(system_id: str) -> str:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT official_source_name
            FROM ip_system_source_config
            WHERE system_id = %s AND is_active = 1
            ORDER BY source_name
            LIMIT 1
            """,
            (system_id,),
        )
        row = cursor.fetchone()
    return str(row["official_source_name"]) if row and row.get("official_source_name") else ""


def _source_stats(system_id: str) -> tuple[int, datetime | None, datetime | None]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count_value FROM ip_system_source_config WHERE system_id = %s AND is_active = 1",
            (system_id,),
        )
        source_count = int(cursor.fetchone()["count_value"] or 0)
        cursor.execute(
            "SELECT MAX(captured_at) AS latest_snapshot_at FROM ip_system_source_snapshot WHERE system_id = %s",
            (system_id,),
        )
        latest_snapshot_at = cursor.fetchone()["latest_snapshot_at"]
        cursor.execute(
            "SELECT MAX(finished_at) AS latest_sync_at FROM ip_system_sync_batch WHERE system_id = %s",
            (system_id,),
        )
        latest_sync_at = cursor.fetchone()["latest_sync_at"]
    return source_count, latest_snapshot_at, latest_sync_at


def _all_source_configs() -> list[IpSystemSourceConfig]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ip_system_source_config ORDER BY system_id, is_active DESC, source_name LIMIT 500")
        return [IpSystemSourceConfig.model_validate(_normalize_record(row)) for row in cursor.fetchall()]


def _recent_sync_batches() -> list[IpSystemSyncBatch]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM ip_system_sync_batch
            ORDER BY started_at DESC
            LIMIT 100
            """
        )
        return [IpSystemSyncBatch.model_validate(_normalize_record(row)) for row in cursor.fetchall()]


def _non_phase1_candidates() -> list[IpSystemRelationCandidate]:
    return [
        item for item in list_relation_candidates()
        if item.matched_jurisdiction_id and not _candidate_is_phase1(item)
    ]


def _publish_review_with_cursor(cursor, review: dict[str, object], actor: str, now: datetime) -> str:
    new_value = review.get("new_value") or {}
    if not isinstance(new_value, dict):
        raise ValueError("INVALID_REVIEW_NEW_VALUE")
    system_id = str(new_value.get("system_id") or review.get("system_id") or "")
    business_domain = str(new_value.get("business_domain") or review.get("business_domain") or "")
    cursor.execute(
        """
        SELECT 1
        FROM ip_system_business_domain
        WHERE system_id = %s AND business_domain = %s AND is_enabled = 1
        LIMIT 1
        """,
        (system_id, business_domain),
    )
    if cursor.fetchone() is None:
        raise ValueError("IP_SYSTEM_BUSINESS_DOMAIN_DISABLED")
    relation_id = str(new_value.get("relation_id") or f"iprel-{uuid4().hex[:16]}")
    jurisdiction_id = str(new_value.get("jurisdiction_id") or review.get("jurisdiction_id") or "")
    relation_type_id = str(new_value.get("relation_type_id") or review.get("relation_type_id") or "")
    effective_date = new_value.get("effective_date")
    expiry_date = new_value.get("expiry_date")
    if effective_date and expiry_date and str(expiry_date) < str(effective_date):
        raise ValueError("INVALID_RELATION_DATE_RANGE")
    cursor.execute(
        """
        SELECT relation_id
        FROM jurisdiction_ip_system_relation
        WHERE jurisdiction_id = %s
          AND system_id = %s
          AND relation_type_id = %s
          AND business_domain = %s
          AND publish_status = 'published'
          AND is_active = 1
          AND relation_id <> %s
          AND COALESCE(effective_date, DATE('1000-01-01')) <= COALESCE(%s, DATE('9999-12-31'))
          AND COALESCE(expiry_date, DATE('9999-12-31')) >= COALESCE(%s, DATE('1000-01-01'))
        LIMIT 1
        """,
        (
            jurisdiction_id,
            system_id,
            relation_type_id,
            business_domain,
            relation_id,
            expiry_date,
            effective_date,
        ),
    )
    if cursor.fetchone() is not None:
        raise ValueError("IP_SYSTEM_RELATION_PERIOD_OVERLAP")
    if review.get("change_type") == "expire_relation" and review.get("old_relation_id"):
        cursor.execute(
            """
            UPDATE jurisdiction_ip_system_relation
            SET expiry_date = %s,
                is_active = %s,
                updated_at = %s
            WHERE relation_id = %s
            """,
            (
                expiry_date,
                bool(new_value.get("is_active", False)),
                now,
                review["old_relation_id"],
            ),
        )
        return str(review["old_relation_id"])
    cursor.execute(
        """
        INSERT INTO jurisdiction_ip_system_relation (
          relation_id, jurisdiction_id, system_id, relation_type_id, business_domain,
          is_active, effective_date, expiry_date, publish_status, published_at,
          published_by, source_reference, source_snapshot_id, source_official_name,
          source_official_code, verification_status, verified_at, verified_by,
          quote_hint_enabled, path_rule_dependency, quote_hint_text, special_statement,
          data_quality_flags_json, admin_remark
        )
        VALUES (
          %(relation_id)s, %(jurisdiction_id)s, %(system_id)s, %(relation_type_id)s,
          %(business_domain)s, %(is_active)s, %(effective_date)s, %(expiry_date)s,
          'published', %(published_at)s, %(published_by)s, %(source_reference)s,
          %(source_snapshot_id)s, %(source_official_name)s, %(source_official_code)s,
          %(verification_status)s, %(verified_at)s, %(verified_by)s,
          %(quote_hint_enabled)s, %(path_rule_dependency)s, %(quote_hint_text)s,
          %(special_statement)s, %(data_quality_flags_json)s, %(admin_remark)s
        )
        ON DUPLICATE KEY UPDATE
          is_active = VALUES(is_active),
          effective_date = VALUES(effective_date),
          expiry_date = VALUES(expiry_date),
          publish_status = 'published',
          published_at = VALUES(published_at),
          published_by = VALUES(published_by),
          source_reference = VALUES(source_reference),
          source_snapshot_id = VALUES(source_snapshot_id),
          source_official_name = VALUES(source_official_name),
          source_official_code = VALUES(source_official_code),
          verification_status = VALUES(verification_status),
          verified_at = VALUES(verified_at),
          verified_by = VALUES(verified_by),
          quote_hint_enabled = VALUES(quote_hint_enabled),
          path_rule_dependency = VALUES(path_rule_dependency),
          quote_hint_text = VALUES(quote_hint_text),
          special_statement = VALUES(special_statement),
          data_quality_flags_json = VALUES(data_quality_flags_json),
          admin_remark = VALUES(admin_remark)
        """,
        {
            "relation_id": relation_id,
            "jurisdiction_id": jurisdiction_id,
            "system_id": system_id,
            "relation_type_id": relation_type_id,
            "business_domain": business_domain,
            "is_active": bool(new_value.get("is_active", True)),
            "effective_date": effective_date,
            "expiry_date": expiry_date,
            "published_at": now,
            "published_by": actor,
            "source_reference": new_value.get("source_reference", ""),
            "source_snapshot_id": new_value.get("source_snapshot_id"),
            "source_official_name": new_value.get("source_official_name") or review.get("source_official_name") or "",
            "source_official_code": new_value.get("source_official_code") or review.get("source_official_code") or "",
            "verification_status": new_value.get("verification_status", "published"),
            "verified_at": new_value.get("verified_at"),
            "verified_by": new_value.get("verified_by"),
            "quote_hint_enabled": bool(new_value.get("quote_hint_enabled", False)),
            "path_rule_dependency": bool(new_value.get("path_rule_dependency", False)),
            "quote_hint_text": new_value.get("quote_hint_text", ""),
            "special_statement": new_value.get("special_statement"),
            "data_quality_flags_json": json.dumps(
                new_value.get("data_quality_flags") or review.get("data_quality_flags") or [],
                ensure_ascii=False,
            ),
            "admin_remark": new_value.get("admin_remark", ""),
        },
    )
    return relation_id


def _get_system_or_raise(system_id: str) -> IpSystem:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ip_system_master WHERE system_id = %s LIMIT 1", (system_id,))
        system = _normalize_record(cursor.fetchone())
        if not system:
            raise KeyError(system_id)
        cursor.execute(
            "SELECT * FROM ip_system_business_domain WHERE system_id = %s ORDER BY business_domain",
            (system_id,),
        )
        system["business_domains"] = [_normalize_record(row) for row in cursor.fetchall()]
    return IpSystem.model_validate(system)


def _get_business_domain_or_raise(domain_id: str) -> IpSystemBusinessDomain:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ip_system_business_domain WHERE id = %s LIMIT 1", (domain_id,))
        row = _normalize_record(cursor.fetchone())
    if not row:
        raise KeyError(domain_id)
    return IpSystemBusinessDomain.model_validate(row)


def _get_relation_type_or_raise(relation_type_id: str) -> IpSystemRelationType:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM ip_system_relation_type WHERE relation_type_id = %s LIMIT 1",
            (relation_type_id,),
        )
        row = _normalize_record(cursor.fetchone())
    if not row:
        raise KeyError(relation_type_id)
    return IpSystemRelationType.model_validate(row)


def _get_source_config_or_raise(source_config_id: str) -> IpSystemSourceConfig:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM ip_system_source_config WHERE source_config_id = %s LIMIT 1",
            (source_config_id,),
        )
        row = _normalize_record(cursor.fetchone())
    if not row:
        raise KeyError(source_config_id)
    return IpSystemSourceConfig.model_validate(row)


def _relation_type_by_code(relation_type_code: str) -> dict[str, object] | None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM ip_system_relation_type
            WHERE relation_type_code = %s AND is_active = 1
            LIMIT 1
            """,
            (relation_type_code.strip().upper(),),
        )
        row = cursor.fetchone()
    return dict(row) if row else None


def _ensure_business_domain_enabled(system_id: str, business_domain: str) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM ip_system_business_domain
            WHERE system_id = %s AND business_domain = %s AND is_enabled = 1
            LIMIT 1
            """,
            (system_id, business_domain),
        )
        if cursor.fetchone() is None:
            raise ValueError("IP_SYSTEM_BUSINESS_DOMAIN_DISABLED")


def _reference_raw_content(payload: IpSystemReferenceCandidateCreate) -> str:
    if payload.parse_mode == "pasted_text":
        return payload.pasted_text
    if payload.parse_mode == "manual_reference":
        return "\n".join(
            item
            for item in [
                payload.raw_text.strip(),
                payload.evidence_text.strip(),
                payload.official_name.strip(),
                payload.official_code.strip(),
                payload.remark.strip(),
            ]
            if item
        )
    return payload.remark


def _reference_candidate_rows(payload: IpSystemReferenceCandidateCreate) -> list[dict[str, object]]:
    if payload.parse_mode == "pasted_text":
        rows = _parse_reference_candidate_lines(payload.pasted_text)
        if payload.data_quality_flags:
            for row in rows:
                row["data_quality_flags"] = list(payload.data_quality_flags)
        return rows
    if payload.parse_mode == "manual_reference":
        official_name = payload.official_name.strip()
        official_code = payload.official_code.strip().upper()
        raw_text = payload.raw_text.strip() or payload.evidence_text.strip() or official_name or official_code
        if not (official_name or official_code or raw_text):
            raise ValueError("REFERENCE_CANDIDATE_IDENTIFIER_REQUIRED")
        return [
            {
                "official_name": official_name or raw_text,
                "official_code": official_code,
                "raw_text": raw_text,
                "evidence_text": payload.evidence_text.strip() or raw_text,
                "matched_jurisdiction_id": payload.matched_jurisdiction_id,
                "data_quality_flags": list(payload.data_quality_flags),
            }
        ]
    return []


def _resolve_reference_candidate_jurisdiction(
    *,
    system_id: str,
    source_config_id: str | None,
    official_name: str,
    official_code: str,
    jurisdiction_name: str = "",
    matched_jurisdiction_id: object | None = None,
) -> dict[str, object] | None:
    if matched_jurisdiction_id:
        with mysql.connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM jurisdictions WHERE jurisdiction_id = %s LIMIT 1",
                (str(matched_jurisdiction_id),),
            )
            jurisdiction = cursor.fetchone()
        if not jurisdiction:
            raise KeyError("JURISDICTION_NOT_FOUND")
        return dict(jurisdiction)
    return ip_system_sync_service.resolve_candidate_jurisdiction(
        system_id=system_id,
        source_config_id=source_config_id,
        official_name=official_name,
        official_code=official_code,
        jurisdiction_name=jurisdiction_name,
    )


def _parse_reference_candidate_lines(text: str) -> list[dict[str, object]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in normalized and ";" in normalized:
        normalized = normalized.replace(";", "\n")
    lines = [line.strip(" \t-•") for line in normalized.split("\n")]
    rows: list[dict[str, object]] = []
    for line in lines:
        if not line:
            continue
        official_code = ""
        official_name = line
        code_match = re.search(r"(?:\(|\[)\s*([A-Z]{2,3})\s*(?:\)|\])\s*$", line, flags=re.IGNORECASE)
        if code_match:
            official_code = code_match.group(1).upper()
            official_name = line[: code_match.start()].strip(" -–—,，")
        else:
            leading_code = re.match(r"^([A-Z]{2,3})\s+[-–—]\s+(.+)$", line, flags=re.IGNORECASE)
            trailing_code = re.match(r"^(.+?)\s+[-–—]\s+([A-Z]{2,3})$", line, flags=re.IGNORECASE)
            if leading_code:
                official_code = leading_code.group(1).upper()
                official_name = leading_code.group(2).strip()
            elif trailing_code:
                official_name = trailing_code.group(1).strip()
                official_code = trailing_code.group(2).upper()
        rows.append({
            "official_name": official_name,
            "official_code": official_code,
            "raw_text": line,
            "evidence_text": line,
            "matched_jurisdiction_id": None,
            "data_quality_flags": [],
        })
    return rows


def _finish_reference_batch(batch_id: str, total: int, matched: int, unmatched: int) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ip_system_sync_batch
            SET finished_at = %s,
                status = 'completed',
                total_records_found = %s,
                new_records_count = %s,
                exception_records_count = %s
            WHERE batch_id = %s
            """,
            (datetime.now(), total, matched, unmatched, batch_id),
        )


def _finish_review_batch(batch_id: str, total: int, created: int, skipped: int) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ip_system_sync_batch
            SET finished_at = %s,
                status = 'completed',
                total_records_found = %s,
                new_records_count = %s,
                unchanged_records_count = %s
            WHERE batch_id = %s
            """,
            (datetime.now(), total, created, skipped, batch_id),
        )


def _update_record(table: str, key_column: str, key_value: str, values: dict[str, object], allowed: set[str]) -> None:
    updates = {key: value for key, value in values.items() if key in allowed}
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        if updates:
            assignments = ", ".join(f"{key} = %s" for key in updates)
            cursor.execute(
                f"UPDATE {table} SET {assignments} WHERE {key_column} = %s",
                tuple(updates.values()) + (key_value,),
            )
            if cursor.rowcount == 0:
                raise KeyError(key_value)
        else:
            cursor.execute(f"SELECT {key_column} FROM {table} WHERE {key_column} = %s LIMIT 1", (key_value,))
            if cursor.fetchone() is None:
                raise KeyError(key_value)


def _relation_row(row: dict[str, object], as_of: date) -> dict[str, object]:
    normalized = _normalize_record(row)
    normalized["data_quality_flags"] = _loads_json_list(normalized.pop("data_quality_flags_json", None))
    normalized["is_current_effective"] = _is_current(normalized, as_of)
    return normalized


def _review_row(row: dict[str, object]) -> dict[str, object]:
    normalized = _normalize_record(row)
    normalized["old_value"] = _loads_json_object(normalized.pop("old_value_json", None))
    normalized["new_value"] = _loads_json_object(normalized.pop("new_value_json", None))
    normalized["data_quality_flags"] = _loads_json_list(normalized.pop("data_quality_flags_json", None))
    return normalized


def _match_exception_row(row: dict[str, object]) -> dict[str, object]:
    normalized = _normalize_record(row)
    normalized["raw_record"] = _loads_json_object(normalized.pop("raw_record_json", None))
    return normalized


def _candidate_row(row: dict[str, object]) -> dict[str, object]:
    normalized = _normalize_record(row)
    normalized["data_quality_flags"] = _loads_json_list(normalized.pop("data_quality_flags_json", None))
    return normalized


def _normalize_record(row: dict[str, object] | None) -> dict[str, object]:
    return dict(row or {})


def _loads_json_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    try:
        loaded = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded if str(item)]


def _loads_json_object(value: object) -> dict[str, object] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    try:
        loaded = json.loads(str(value))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _published_current_sql(alias: str) -> str:
    return (
        f"{alias}.publish_status = 'published' "
        f"AND {alias}.is_active = 1 "
        f"AND ({alias}.effective_date IS NULL OR {alias}.effective_date <= %s) "
        f"AND ({alias}.expiry_date IS NULL OR {alias}.expiry_date >= %s)"
    )


def _is_current(row: dict[str, object], as_of: date) -> bool:
    if row.get("publish_status") != "published" or not bool(row.get("is_active")):
        return False
    effective_date = row.get("effective_date")
    expiry_date = row.get("expiry_date")
    if effective_date and effective_date > as_of:
        return False
    if expiry_date and expiry_date < as_of:
        return False
    return True
