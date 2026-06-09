from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


BusinessDomain = Literal["patent", "design", "trademark", "general_ip"]
PublishStatus = Literal["draft", "pending_review", "published", "rejected", "archived"]
ReviewStatus = Literal["pending_review", "approved", "rejected", "ignored", "published"]
ChangeType = Literal[
    "new_relation",
    "update_relation",
    "expire_relation",
    "source_changed",
    "date_changed",
    "remark_changed",
]


def _normalize_flags(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


class IpSystemBusinessDomain(BaseModel):
    id: str
    system_id: str
    business_domain: BusinessDomain
    is_enabled: bool = True
    quote_hint_default_enabled: bool = False
    path_rule_default_dependency: bool = False
    remark: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IpSystemBusinessDomainCreate(BaseModel):
    business_domain: BusinessDomain
    is_enabled: bool = True
    quote_hint_default_enabled: bool = False
    path_rule_default_dependency: bool = False
    remark: str = ""


class IpSystemBusinessDomainUpdate(BaseModel):
    is_enabled: bool | None = None
    quote_hint_default_enabled: bool | None = None
    path_rule_default_dependency: bool | None = None
    remark: str | None = None


class IpSystem(BaseModel):
    system_id: str
    system_code: str
    system_name_cn: str
    system_name_en: str
    system_category: str
    business_domain_scope: str = ""
    is_active: bool = True
    display_order: int = 100
    default_update_frequency: str = ""
    source_priority: str = ""
    source_url: str = ""
    official_source_name: str = ""
    last_verified_at: datetime | None = None
    next_review_due_at: datetime | None = None
    remark: str = ""
    business_domains: list[IpSystemBusinessDomain] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IpSystemCreate(BaseModel):
    system_code: str = Field(min_length=1)
    system_name_cn: str = Field(min_length=1)
    system_name_en: str = Field(min_length=1)
    system_category: str = Field(min_length=1)
    business_domain_scope: str = ""
    is_active: bool = True
    display_order: int = 100
    default_update_frequency: str = ""
    source_priority: str = ""
    source_url: str = ""
    official_source_name: str = ""
    last_verified_at: datetime | None = None
    next_review_due_at: datetime | None = None
    remark: str = ""


class IpSystemUpdate(BaseModel):
    system_name_cn: str | None = None
    system_name_en: str | None = None
    system_category: str | None = None
    business_domain_scope: str | None = None
    is_active: bool | None = None
    display_order: int | None = None
    default_update_frequency: str | None = None
    source_priority: str | None = None
    source_url: str | None = None
    official_source_name: str | None = None
    last_verified_at: datetime | None = None
    next_review_due_at: datetime | None = None
    remark: str | None = None


class IpSystemRelationType(BaseModel):
    relation_type_id: str
    relation_type_code: str
    relation_type_name_cn: str
    relation_type_name_en: str
    applicable_system_category: str = ""
    is_active: bool = True
    display_order: int = 100
    remark: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IpSystemRelationTypeCreate(BaseModel):
    relation_type_code: str = Field(min_length=1)
    relation_type_name_cn: str = Field(min_length=1)
    relation_type_name_en: str = Field(min_length=1)
    applicable_system_category: str = ""
    is_active: bool = True
    display_order: int = 100
    remark: str = ""


class IpSystemRelationTypeUpdate(BaseModel):
    relation_type_name_cn: str | None = None
    relation_type_name_en: str | None = None
    applicable_system_category: str | None = None
    is_active: bool | None = None
    display_order: int | None = None
    remark: str | None = None


class IpSystemSourceConfig(BaseModel):
    source_config_id: str
    system_id: str
    source_name: str
    source_type: str
    source_url: str = ""
    source_scope: str = "reference_only"
    official_source_name: str = ""
    parser_key: str = ""
    parse_mode: str = "manual_reference"
    update_frequency: str = ""
    auto_check_enabled: bool = False
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failed_at: datetime | None = None
    failure_reason: str = ""
    is_active: bool = True
    remark: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IpSystemSourceConfigCreate(BaseModel):
    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_url: str = ""
    source_scope: str = "reference_only"
    official_source_name: str = ""
    parser_key: str = ""
    parse_mode: str = "manual_reference"
    update_frequency: str = ""
    auto_check_enabled: bool = False
    next_check_at: datetime | None = None
    is_active: bool = True
    remark: str = ""


class IpSystemSourceConfigUpdate(BaseModel):
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_scope: str | None = None
    official_source_name: str | None = None
    parser_key: str | None = None
    parse_mode: str | None = None
    update_frequency: str | None = None
    auto_check_enabled: bool | None = None
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failed_at: datetime | None = None
    failure_reason: str | None = None
    is_active: bool | None = None
    remark: str | None = None


class IpSystemRelation(BaseModel):
    relation_id: str
    jurisdiction_id: str
    jurisdiction_code: str = ""
    jurisdiction_name_cn: str = ""
    jurisdiction_name_en: str = ""
    system_id: str
    system_code: str = ""
    system_name_cn: str = ""
    relation_type_id: str
    relation_type_code: str = ""
    relation_type_name_cn: str = ""
    business_domain: BusinessDomain
    is_active: bool = True
    effective_date: date | None = None
    expiry_date: date | None = None
    publish_status: PublishStatus = "published"
    published_at: datetime | None = None
    published_by: str | None = None
    source_reference: str = ""
    source_snapshot_id: str | None = None
    source_official_name: str = ""
    source_official_code: str = ""
    verification_status: str = ""
    verified_at: datetime | None = None
    verified_by: str | None = None
    quote_hint_enabled: bool = False
    path_rule_dependency: bool = False
    quote_hint_text: str = ""
    special_statement: str | None = None
    data_quality_flags: list[str] = Field(default_factory=list)
    admin_remark: str = ""
    is_current_effective: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def validate_flags(cls, value: object) -> list[str]:
        return _normalize_flags(value)


class IpSystemManualRelationReviewCreate(BaseModel):
    jurisdiction_id: str = Field(min_length=1)
    system_id: str = Field(min_length=1)
    relation_type_code: str = Field(min_length=1)
    business_domain: BusinessDomain
    effective_date: date | None = None
    expiry_date: date | None = None
    is_active: bool = True
    quote_hint_enabled: bool = False
    path_rule_dependency: bool = False
    quote_hint_text: str = ""
    special_statement: str = ""
    source_reference: str = ""
    data_quality_flags: list[str] = Field(default_factory=list)
    admin_remark: str = ""
    review_comment: str = "manual_single_relation"


class IpSystemRelationCandidate(BaseModel):
    candidate_id: str
    source_config_id: str | None = None
    snapshot_id: str | None = None
    batch_id: str | None = None
    system_id: str
    system_code: str = ""
    system_name_cn: str = ""
    business_domain: str
    relation_type_id: str | None = None
    relation_type_code: str = ""
    relation_type_name_cn: str = ""
    official_name: str = ""
    official_code: str = ""
    raw_text: str = ""
    source_url: str = ""
    source_reference: str = ""
    evidence_text: str = ""
    matched_jurisdiction_id: str | None = None
    matched_jurisdiction_code: str = ""
    matched_jurisdiction_name_cn: str = ""
    match_status: str = "unmatched"
    match_confidence: float | None = None
    data_quality_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def validate_flags(cls, value: object) -> list[str]:
        return _normalize_flags(value)


class IpSystemReferenceCandidateCreate(BaseModel):
    business_domain: BusinessDomain
    relation_type_code: str = Field(min_length=1)
    source_config_id: str | None = None
    source_name: str = ""
    source_url: str = ""
    source_type: str = "official_url"
    source_scope: Literal["full_snapshot", "partial_update", "reference_only"] = "reference_only"
    official_source_name: str = ""
    parser_key: str = "manual_reference"
    parse_mode: Literal["manual_reference", "pasted_text", "html_table", "csv_content", "xlsx_base64"] = "manual_reference"
    pasted_text: str = ""
    official_name: str = ""
    official_code: str = ""
    raw_text: str = ""
    evidence_text: str = ""
    matched_jurisdiction_id: str | None = None
    data_quality_flags: list[str] = Field(default_factory=list)
    remark: str = ""

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def validate_flags(cls, value: object) -> list[str]:
        return _normalize_flags(value)


class IpSystemReferenceCandidateResponse(BaseModel):
    batch: IpSystemSyncBatch
    snapshot_id: str | None = None
    source_config: IpSystemSourceConfig
    total_candidates: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)


class IpSystemReferenceReviewCreate(BaseModel):
    candidate_ids: list[str] = Field(default_factory=list)
    jurisdiction_id: str | None = None
    review_comment: str = "reference_candidate_confirmed"


class IpSystemReferenceReviewResponse(BaseModel):
    batch_id: str
    created_count: int = 0
    skipped_count: int = 0
    reviews: list[IpSystemChangeReview] = Field(default_factory=list)


class IpSystemJurisdictionReferenceCheck(BaseModel):
    jurisdiction_id: str
    published_relations: list[IpSystemRelation] = Field(default_factory=list)
    pending_reviews: list[IpSystemChangeReview] = Field(default_factory=list)
    reference_candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)
    match_exceptions: list[IpSystemMatchException] = Field(default_factory=list)


class IpSystemEnablementMatchedJurisdiction(BaseModel):
    jurisdiction_id: str | None = None
    jurisdiction_code: str = ""
    jurisdiction_name_cn: str = ""
    jurisdiction_name_en: str = ""
    jurisdiction_type: str = ""
    is_enabled: bool | None = None
    is_deleted: bool | None = None


class IpSystemEnablementSystemStatus(BaseModel):
    system_id: str
    system_code: str
    system_name: str = ""
    status: Literal[
        "published",
        "reference_hit_unpublished",
        "candidate_exists",
        "pending_review_exists",
        "match_exception",
        "no_hit",
        "not_applicable",
        "reserved_hidden",
    ] = "no_hit"
    relation_types: list[str] = Field(default_factory=list)
    visibility: Literal["default", "reserved_hidden", "hidden"] = "default"
    reason: str = ""
    published_relations: list[IpSystemRelation] = Field(default_factory=list)
    reference_candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)
    pending_reviews: list[IpSystemChangeReview] = Field(default_factory=list)
    match_exceptions: list[IpSystemMatchException] = Field(default_factory=list)


class IpSystemTag(BaseModel):
    system_id: str
    system_code: str
    system_name_cn: str
    system_name_en: str
    system_category: str
    business_domain: BusinessDomain
    relation_type_code: str
    relation_type_name_cn: str
    effective_date: date | None = None
    expiry_date: date | None = None
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def validate_flags(cls, value: object) -> list[str]:
        return _normalize_flags(value)


class QuoteIpTag(IpSystemTag):
    quote_hint_enabled: bool = False
    path_rule_dependency: bool = False
    quote_hint_text: str = ""
    special_statement: str | None = None


class IpSystemOverview(BaseModel):
    system_id: str
    system_code: str
    system_name_cn: str
    system_name_en: str
    system_category: str
    business_domain: str | None = None
    current_jurisdiction_count: int = 0
    relation_type_counts: dict[str, int] = Field(default_factory=dict)
    pending_review_count: int = 0
    last_sync_at: datetime | None = None
    last_verified_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: str = "not_due"


class IpSystemV1PhaseScope(BaseModel):
    phase1_system_codes: list[str] = Field(default_factory=list)
    reserved_system_codes: list[str] = Field(default_factory=list)
    phase1_jurisdiction_codes: list[str] = Field(default_factory=list)


class IpSystemBusinessTodoSummary(BaseModel):
    pending_review_count: int = 0
    match_exception_count: int = 0
    candidate_count: int = 0
    non_phase1_candidate_count: int = 0
    has_overdue_review: bool = False


class IpSystemBusinessReferenceSummary(BaseModel):
    source_config_count: int = 0
    candidate_count: int = 0
    phase1_candidate_count: int = 0
    non_phase1_candidate_count: int = 0
    unmatched_candidate_count: int = 0
    latest_snapshot_at: datetime | None = None
    latest_sync_at: datetime | None = None


class IpSystemBusinessDashboardItem(BaseModel):
    system_id: str
    system_code: str
    system_name_cn: str
    system_name_en: str
    system_category: str
    business_domain_scope: str = ""
    business_domains: list[IpSystemBusinessDomain] = Field(default_factory=list)
    management_agency: str = ""
    is_active: bool = True
    is_phase1_default: bool = False
    is_reserved: bool = False
    current_relation_count: int = 0
    relation_type_counts: dict[str, int] = Field(default_factory=dict)
    todo_summary: IpSystemBusinessTodoSummary = Field(default_factory=IpSystemBusinessTodoSummary)
    reference_summary: IpSystemBusinessReferenceSummary = Field(default_factory=IpSystemBusinessReferenceSummary)
    data_status: str = "not_configured"
    last_verified_at: datetime | None = None
    next_review_due_at: datetime | None = None
    remark: str = ""


class IpSystemBusinessDashboardResponse(BaseModel):
    items: list[IpSystemBusinessDashboardItem] = Field(default_factory=list)
    phase_scope: IpSystemV1PhaseScope


class IpSystemBusinessRelationSummary(BaseModel):
    current_relation_count: int = 0
    relation_type_counts: dict[str, int] = Field(default_factory=dict)


class IpSystemBusinessRelationSummaryBucket(BaseModel):
    key: str
    label: str
    count: int = 0
    examples: list[str] = Field(default_factory=list)
    relation_type_codes: list[str] = Field(default_factory=list)


class IpSystemBusinessActionItem(BaseModel):
    action_key: str
    title: str
    description: str = ""
    priority: int = 100


class IpSystemBusinessTodoItem(BaseModel):
    item_type: str
    title: str
    count: int = 0
    description: str = ""
    action_key: str = ""
    priority: int = 100


class IpSystemBusinessRelationItem(IpSystemRelation):
    effective_status: str = "current"


class IpSystemBusinessDetailResponse(BaseModel):
    system: IpSystemBusinessDashboardItem
    relation_summary: IpSystemBusinessRelationSummary
    current_relation_summary: list[IpSystemBusinessRelationSummaryBucket] = Field(default_factory=list)
    todo_items: list[IpSystemBusinessTodoItem] = Field(default_factory=list)
    recommended_next_actions: list[IpSystemBusinessActionItem] = Field(default_factory=list)
    boundary_notes: list[str] = Field(default_factory=list)
    relations: list[IpSystemBusinessRelationItem] = Field(default_factory=list)
    source_configs: list[IpSystemSourceConfig] = Field(default_factory=list)
    reference_summary: IpSystemBusinessReferenceSummary = Field(default_factory=IpSystemBusinessReferenceSummary)
    pending_reviews: list[IpSystemChangeReview] = Field(default_factory=list)
    match_exceptions: list[IpSystemMatchException] = Field(default_factory=list)
    candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)


class IpSystemJurisdictionProfileCard(BaseModel):
    jurisdiction_id: str
    jurisdiction_code: str = ""
    jurisdiction_name_cn: str = ""
    jurisdiction_name_en: str = ""
    jurisdiction_type: str = ""
    current_relation_count: int = 0
    pending_item_count: int = 0
    latest_verified_at: datetime | None = None
    data_status: str = "not_configured"


class IpSystemJurisdictionTodoItem(BaseModel):
    item_type: str
    system_id: str | None = None
    system_code: str = ""
    relation_type_code: str = ""
    title: str = ""
    status: str = ""
    source_reference: str = ""


class IpSystemJurisdictionSystemCard(BaseModel):
    system_id: str
    system_code: str
    system_name_cn: str = ""
    system_category: str = ""
    status: str = "current"
    relations: list[IpSystemBusinessRelationItem] = Field(default_factory=list)
    pending_reviews: list[IpSystemChangeReview] = Field(default_factory=list)
    candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)
    match_exceptions: list[IpSystemMatchException] = Field(default_factory=list)
    risk_tips: list[str] = Field(default_factory=list)


class IpSystemJurisdictionProfileResponse(BaseModel):
    profile: IpSystemJurisdictionProfileCard
    system_cards: list[IpSystemJurisdictionSystemCard] = Field(default_factory=list)
    todo_items: list[IpSystemJurisdictionTodoItem] = Field(default_factory=list)
    hidden_not_applicable_count: int = 0
    phase_scope: IpSystemV1PhaseScope


class IpSystemReferenceCoverageStats(BaseModel):
    official_reference_total: int = 0
    parsed_candidate_count: int = 0
    phase1_published_count: int = 0
    phase1_missing_count: int = 0
    non_phase1_candidate_count: int = 0
    pending_review_count: int = 0
    match_exception_count: int = 0


class IpSystemReferenceCoverageResponse(BaseModel):
    system_id: str
    system_code: str = ""
    source_config_id: str | None = None
    relation_type_code: str | None = None
    business_domain: str | None = None
    stats: IpSystemReferenceCoverageStats
    phase_scope: IpSystemV1PhaseScope


class IpSystemAdvancedWorkbenchResponse(BaseModel):
    phase_scope: IpSystemV1PhaseScope
    systems: list[IpSystem] = Field(default_factory=list)
    relation_types: list[IpSystemRelationType] = Field(default_factory=list)
    source_configs: list[IpSystemSourceConfig] = Field(default_factory=list)
    recent_batches: list[IpSystemSyncBatch] = Field(default_factory=list)
    pending_reviews: list[IpSystemChangeReview] = Field(default_factory=list)
    match_exceptions: list[IpSystemMatchException] = Field(default_factory=list)
    non_phase1_candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)


class IpSystemEnablementCheckResponse(BaseModel):
    query: str
    matched_jurisdiction: IpSystemEnablementMatchedJurisdiction | None = None
    master_status: str = "not_exists"
    phase_scope_status: str = "not_in_scope"
    system_statuses: list[IpSystemEnablementSystemStatus] = Field(default_factory=list)
    published_relations: list[IpSystemRelation] = Field(default_factory=list)
    reference_candidates: list[IpSystemRelationCandidate] = Field(default_factory=list)
    pending_reviews: list[IpSystemChangeReview] = Field(default_factory=list)
    match_exceptions: list[IpSystemMatchException] = Field(default_factory=list)
    alias_mappings: list[dict[str, object]] = Field(default_factory=list)
    recommended_next_actions: list[IpSystemBusinessActionItem] = Field(default_factory=list)
    boundary_notes: list[str] = Field(default_factory=list)


class IpSystemCheckResponse(BaseModel):
    matched: bool
    relation_count: int = 0
    relations: list[IpSystemRelation] = Field(default_factory=list)


class IpSystemSourceSnapshot(BaseModel):
    snapshot_id: str
    system_id: str
    source_config_id: str | None = None
    snapshot_type: str = "manual_import"
    raw_snapshot_path: str = ""
    raw_content_hash: str = ""
    raw_metadata: dict[str, object] = Field(default_factory=dict)
    captured_at: datetime | None = None
    captured_by: str | None = None
    remark: str = ""


class IpSystemSyncBatch(BaseModel):
    batch_id: str
    system_id: str
    source_config_id: str | None = None
    source_snapshot_id: str | None = None
    batch_type: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    total_records_found: int = 0
    new_records_count: int = 0
    changed_records_count: int = 0
    removed_records_count: int = 0
    unchanged_records_count: int = 0
    exception_records_count: int = 0
    error_message: str = ""
    raw_snapshot_path: str = ""
    created_by: str | None = None
    created_at: datetime | None = None


class IpSystemSyncPrepareRequest(BaseModel):
    source_config_id: str | None = None
    batch_type: str = "manual_sync"
    snapshot_type: str = "manual_import"
    raw_snapshot_path: str = ""
    raw_content: str = ""
    raw_metadata: dict[str, object] = Field(default_factory=dict)
    remark: str = ""


class IpSystemSyncPrepareResponse(BaseModel):
    batch: IpSystemSyncBatch
    snapshot_id: str | None = None
    status: str = "prepared"
    message: str = "Sync/import preparation created. Parsing and diff publishing are handled by later workflow steps."


class IpSystemImportRow(BaseModel):
    system_code: str = ""
    business_domain: str = ""
    relation_type_code: str = ""
    jurisdiction_name: str = ""
    official_name: str = ""
    official_code: str = ""
    effective_date: date | str | None = None
    expiry_date: date | str | None = None
    is_active: bool | str | int | None = True
    quote_hint_enabled: bool | str | int | None = False
    path_rule_dependency: bool | str | int | None = False
    quote_hint_text: str = ""
    special_statement: str = ""
    source_reference: str = ""
    data_quality_flags: list[str] | str = Field(default_factory=list)
    admin_remark: str = ""


class IpSystemImportRequest(BaseModel):
    source_config_id: str | None = None
    import_mode: Literal["partial_update", "full_snapshot"] = "partial_update"
    file_format: Literal["rows", "csv", "xlsx"] = "rows"
    rows: list[IpSystemImportRow] = Field(default_factory=list)
    csv_content: str = ""
    xlsx_base64: str = ""
    raw_snapshot_path: str = ""
    source_reference: str = ""
    remark: str = ""


class IpSystemImportParseError(BaseModel):
    row_number: int
    reason: str
    raw: dict[str, object] = Field(default_factory=dict)


class IpSystemImportResponse(BaseModel):
    batch: IpSystemSyncBatch
    snapshot_id: str | None = None
    total_rows: int = 0
    parsed_count: int = 0
    new_records_count: int = 0
    changed_records_count: int = 0
    removed_records_count: int = 0
    unchanged_records_count: int = 0
    exception_records_count: int = 0
    parse_errors: list[IpSystemImportParseError] = Field(default_factory=list)


class IpSystemSyncBatchDetail(IpSystemSyncBatch):
    change_review_count: int = 0
    match_exception_count: int = 0


class IpSystemChangeReview(BaseModel):
    review_id: str
    batch_id: str
    system_id: str
    system_code: str = ""
    jurisdiction_id: str | None = None
    jurisdiction_code: str = ""
    jurisdiction_name_cn: str = ""
    relation_type_id: str | None = None
    relation_type_code: str = ""
    business_domain: str = ""
    change_type: str
    old_relation_id: str | None = None
    old_value: dict[str, object] | None = None
    new_value: dict[str, object] | None = None
    source_official_name: str = ""
    source_official_code: str = ""
    data_quality_flags: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = "pending_review"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    review_comment: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("data_quality_flags", mode="before")
    @classmethod
    def validate_flags(cls, value: object) -> list[str]:
        return _normalize_flags(value)


class IpSystemChangeReviewUpdate(BaseModel):
    review_status: ReviewStatus
    review_comment: str = ""


class IpSystemPublishBatchRequest(BaseModel):
    review_ids: list[str] = Field(default_factory=list)
    auto_approve_pending: bool = False
    review_comment: str = ""


class IpSystemPublishBatchResponse(BaseModel):
    batch_id: str
    published_count: int = 0
    skipped_count: int = 0
    published_review_ids: list[str] = Field(default_factory=list)


class IpSystemMatchException(BaseModel):
    exception_id: str
    batch_id: str | None = None
    system_id: str
    system_code: str = ""
    source_config_id: str | None = None
    official_name: str = ""
    official_code: str = ""
    raw_record: dict[str, object] | None = None
    suggested_jurisdiction_id: str | None = None
    confidence_score: Decimal | None = None
    status: str = "pending"
    resolved_jurisdiction_id: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_comment: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IpSystemMatchExceptionUpdate(BaseModel):
    status: Literal["confirmed", "ignored", "rejected"]
    resolved_jurisdiction_id: str | None = None
    resolution_comment: str = ""
    create_alias_mapping: bool = True

    @model_validator(mode="after")
    def validate_confirmed_jurisdiction(self) -> "IpSystemMatchExceptionUpdate":
        if self.status == "confirmed" and not self.resolved_jurisdiction_id:
            raise ValueError("resolved_jurisdiction_id is required when confirmed")
        return self


class IpSystemMatchExceptionResolveRequest(BaseModel):
    resolved_jurisdiction_id: str = Field(min_length=1)
    resolution_comment: str = ""
    create_alias_mapping: bool = True
    reprocess: bool = True


class IpSystemReprocessBatchResponse(BaseModel):
    batch_id: str
    reprocessed_count: int = 0
    new_change_count: int = 0
    remaining_exception_count: int = 0
