from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class IpSystemQuerySystem(BaseModel):
    system_code: str
    name_zh: str
    name_en: str = ""
    short_name: str = ""
    category: str = ""
    source_url: str = ""
    source_name: str = ""
    last_checked_at: datetime | None = None
    remark: str = ""
    is_p0: bool = True
    is_reserved: bool = False


class IpSystemMemberStats(BaseModel):
    official_member_count: int = 0
    existing_in_master_count: int = 0
    missing_in_master_count: int = 0
    applicable_relation_count: int = 0
    relation_type_counts: dict[str, int] = Field(default_factory=dict)
    last_checked_at: datetime | None = None
    source_name: str = ""
    source_url: str = ""


class IpSystemQueryMember(BaseModel):
    name_zh: str
    name_en: str = ""
    code: str
    effective_date: date | None = None
    date_label: str = "加入/生效/适用时间"
    member_type: str = "country"
    master_status: str = "missing"
    master_status_label: str = "未录入主档"
    membership_relation_type: str = "member_state"
    membership_relation_type_label: str = "成员国"
    pct_route_type: str = ""
    pct_route_type_label: str = ""
    regional_system_code: str = ""
    regional_system_name: str = ""
    route_remark: str = ""
    is_historical_relation: bool = False
    internal_remark: str = ""
    remark_updated_at: datetime | None = None
    remark_updated_by: str = ""
    remark: str = ""


class IpSystemMembersResponse(BaseModel):
    system: IpSystemQuerySystem
    stats: IpSystemMemberStats
    overall_remark: str = ""
    members: list[IpSystemQueryMember] = Field(default_factory=list)
    historical_members: list[IpSystemQueryMember] = Field(default_factory=list)


class IpSystemJurisdictionOption(BaseModel):
    jurisdiction_id: str | None = None
    code: str
    name_zh: str
    name_en: str = ""
    member_type: str = ""
    master_status: str = "missing"
    master_status_label: str = "未录入主档"
    matched_system_codes: list[str] = Field(default_factory=list)
    has_reference_object: bool = False
    object_type: str = ""
    object_type_label: str = ""
    reference_source_name: str = ""
    reference_profile_url: str = ""
    reference_system_hint: str = ""
    is_pct_contracting_state: bool = False
    is_paris_contracting_party: bool = False
    epc_relation_type_label: str = ""
    is_eu_design_covered: bool = False


class IpSystemJurisdictionMembership(BaseModel):
    system_code: str
    system_name_zh: str
    system_name_en: str = ""
    short_name: str = ""
    effective_date: date | None = None
    membership_relation_type: str = "member_state"
    membership_relation_type_label: str = "成员国"
    pct_route_type: str = ""
    pct_route_type_label: str = ""
    regional_system_code: str = ""
    regional_system_name: str = ""
    route_remark: str = ""
    is_historical_relation: bool = False
    internal_remark: str = ""
    remark: str = ""


class IpSystemJurisdictionMembershipGroup(BaseModel):
    jurisdiction_id: str | None = None
    code: str
    name_zh: str
    name_en: str = ""
    master_status: str = "missing"
    master_status_label: str = "未录入主档"
    has_reference_object: bool = False
    object_type: str = ""
    object_type_label: str = ""
    reference_source_name: str = ""
    reference_profile_url: str = ""
    reference_system_hint: str = ""
    is_pct_contracting_state: bool = False
    is_paris_contracting_party: bool = False
    epc_relation_type_label: str = ""
    is_eu_design_covered: bool = False
    memberships: list[IpSystemJurisdictionMembership] = Field(default_factory=list)


class IpSystemJurisdictionMembershipRequest(BaseModel):
    jurisdiction_ids: list[str] = Field(default_factory=list)
    jurisdiction_codes: list[str] = Field(default_factory=list)


IpSystemUpdateChangeType = Literal[
    "added_member",
    "removed_member",
    "effective_date_changed",
    "name_changed",
    "code_changed",
    "remark_changed",
    "source_changed",
    "route_type_changed",
    "object_type_changed",
    "profile_url_changed",
]


class IpSystemUpdateDiff(BaseModel):
    change_type: IpSystemUpdateChangeType
    code: str
    name_zh: str = ""
    name_en: str = ""
    old_effective_date: date | None = None
    new_effective_date: date | None = None
    old_remark: str = ""
    new_remark: str = ""
    old_source_url: str = ""
    new_source_url: str = ""
    old_value: str | None = None
    new_value: str | None = None


class IpSystemCheckUpdatesResponse(BaseModel):
    system_code: str
    source_id: str = ""
    checked_at: datetime
    source_url: str = ""
    source_name: str = ""
    source_type: str = ""
    apply_target: str = ""
    affects_membership_count: bool = False
    check_status: str = "success"
    expected_count: int | None = None
    expected_scope: str = ""
    parsed_count: int | None = None
    parsed_date_count: int | None = None
    current_baseline_count: int | None = None
    failure_reason: str = ""
    apply_allowed: bool = True
    diff_summary: dict[str, int] = Field(default_factory=dict)
    has_changes: bool = False
    summary_preview: str = ""
    message: str = ""
    diffs: list[IpSystemUpdateDiff] = Field(default_factory=list)


class IpSystemApplyUpdatesRequest(BaseModel):
    diffs: list[IpSystemUpdateDiff] = Field(default_factory=list)


class IpSystemApplyUpdatesResponse(BaseModel):
    system_code: str
    updated_count: int = 0
    parsed_count: int | None = None
    parsed_date_count: int | None = None
    written_date_count: int | None = None
    skipped_count: int = 0
    apply_target: str = ""
    affects_membership_count: bool = False
    summary: str = ""
    message: str = ""


class IpSystemDataSource(BaseModel):
    id: str
    system_code: str
    source_name: str
    source_type: str
    source_url: str = ""
    purpose_note: str = ""
    is_enabled: bool = True
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_check_status: str = ""
    last_check_message: str = ""
    last_check_summary: str = ""
    last_update_summary: str = ""
    admin_update_note: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IpSystemDataSourceCreate(BaseModel):
    system_code: str
    source_name: str
    source_type: str
    source_url: str = ""
    purpose_note: str = ""
    is_enabled: bool = True


class IpSystemDataSourceUpdate(BaseModel):
    system_code: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    purpose_note: str | None = None
    is_enabled: bool | None = None
    last_update_summary: str | None = None
    admin_update_note: str | None = None


class IpSystemUpdateHistoryItem(BaseModel):
    id: int
    source_id: str = ""
    system_code: str
    source_name: str = ""
    source_type: str = ""
    operation: str = ""
    update_type: str = ""
    update_count: int = 0
    parsed_count: int | None = None
    parsed_date_count: int | None = None
    written_date_count: int | None = None
    system_summary: str = ""
    admin_note: str = ""
    actor: str = ""
    status: str = ""
    failure_reason: str = ""
    created_at: datetime | None = None


class IpSystemMemberRemarkUpdate(BaseModel):
    internal_remark: str = ""


class IpSystemReferenceObject(BaseModel):
    sequence_no: int
    name_zh: str
    name_en: str = ""
    code: str
    object_type: str = "country"
    object_type_label: str = "国家"
    master_status: str = "missing"
    master_status_label: str = "未录入主档"
    is_pct_contracting_state: bool = False
    is_paris_contracting_party: bool = False
    epc_relation_type: str = ""
    epc_relation_type_label: str = ""
    is_eu_design_covered: bool = False
    system_hint: str = ""
    profile_url: str = ""
    internal_remark: str = ""


class IpSystemReferenceObjectsResponse(BaseModel):
    source_name: str
    source_type: str = "reference_source"
    source_url: str
    reference_count: int
    objects: list[IpSystemReferenceObject] = Field(default_factory=list)
