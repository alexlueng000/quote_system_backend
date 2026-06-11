import json
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Role = Literal["consultant", "admin", "approver"]
UserStatus = Literal["active", "inactive"]
CustomerStatus = Literal["active", "inactive"]
CustomerType = Literal["企业", "个人", "律所", "代理机构", "其他"]
CustomerLevel = Literal["普通", "重点", "战略", "暂停"]
FollowupMethod = Literal["邮件", "电话", "微信", "企微", "会议", "其他"]
QuotationStatus = Literal[
    "草稿",
    "已生成报价",
    "已发送客户",
    "待跟进",
    "跟进中",
    "跟进逾期",
    "需价格调整",
    "已确认",
    "部分开卷",
    "已开卷",
    "框架协议",
    "未成交",
    "已作废",
]

JURISDICTION_TYPES = {
    "single_country",
    "special_region",
    "regional_office",
    "international_organization",
    "treaty_entry",
    "internal_business_object",
}
GEO_REGIONS = {
    "Asia",
    "Europe",
    "Africa",
    "Oceania",
    "North America",
    "South America",
    "Latin America and the Caribbean",
    "Middle East",
    "Other",
}
BUSINESS_REGION_TAGS = {
    "EUROPE",
    "NORTH_AMERICA",
    "LATIN_AMERICA",
    "SOUTHEAST_ASIA",
    "NORTHEAST_ASIA_JP_KR",
    "GREATER_CHINA",
    "MIDDLE_EAST",
    "AFRICA",
    "ANZ_OCEANIA",
    "SOUTH_ASIA",
    "BELT_AND_ROAD",
    "OTHER",
}
ECONOMIC_ORG_TAGS = {"APEC", "ASEAN", "BRICS", "EU"}
INTERNAL_ANALYTICS_TAGS = {
    "HIGH_COST_MARKET",
    "HIGH_FREQUENCY_QUOTATION_MARKET",
    "HIGH_CONVERSION_MARKET",
    "LOW_FREQUENCY_HIGH_VALUE_MARKET",
    "KEY_MARKET",
}
MAINTAINABLE_BUSINESS_TAGS = BUSINESS_REGION_TAGS | ECONOMIC_ORG_TAGS
LEGACY_BUSINESS_REGION_ALIASES = {
    "Europe": "EUROPE",
    "North America": "NORTH_AMERICA",
    "Latin America": "LATIN_AMERICA",
    "SOUTH_AMERICA": "LATIN_AMERICA",
    "South America": "LATIN_AMERICA",
    "Southeast Asia": "SOUTHEAST_ASIA",
    "Middle East": "MIDDLE_EAST",
    "Africa": "AFRICA",
    "Japan and Korea": "NORTHEAST_ASIA_JP_KR",
    "Hong Kong Macao Taiwan": "GREATER_CHINA",
    "Other": "OTHER",
}


def _normalize_business_tags(value: object) -> list[str]:
    if value in (None, ""):
        return []
    raw_items: list[object]
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            raw_items = [item.strip() for item in value.replace("，", ",").split(",")]
        else:
            raw_items = loaded if isinstance(loaded, list) else [value]
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    tags: list[str] = []
    for raw_item in raw_items:
        text = str(raw_item).strip()
        if not text:
            continue
        normalized = LEGACY_BUSINESS_REGION_ALIASES.get(text, text).upper()
        if normalized not in MAINTAINABLE_BUSINESS_TAGS:
            raise ValueError("invalid business_region")
        if normalized not in tags:
            tags.append(normalized)
    if len(tags) > 1 and "OTHER" in tags:
        tags = [tag for tag in tags if tag != "OTHER"]
    return tags


class User(BaseModel):
    id: str
    name: str
    email: str
    role: Role
    status: UserStatus


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=6)
    role: Role = "consultant"
    status: UserStatus = "active"


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=1)
    role: Role | None = None
    status: UserStatus | None = None


class UserPasswordUpdate(BaseModel):
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: User


class CustomerContactCreate(BaseModel):
    name: str = Field(min_length=1)
    title: str = ""
    email: str = ""
    phone: str = ""
    wechat: str = ""
    is_primary: bool = False
    remark: str = ""


class CustomerContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    wechat: str | None = None
    is_primary: bool | None = None
    remark: str | None = None


class CustomerContactResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    title: str = ""
    email: str = ""
    phone: str = ""
    wechat: str = ""
    is_primary: bool
    remark: str = ""
    created_at: datetime
    updated_at: datetime


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1)
    customer_type: CustomerType = "企业"
    consultant_email: str | None = None
    department: str = ""
    default_currency: str = "CNY"
    default_quote_terms: str = ""
    customer_level: CustomerLevel = "普通"
    status: CustomerStatus = "active"
    remark: str = ""
    contacts: list[CustomerContactCreate] = Field(default_factory=list)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    customer_type: CustomerType | None = None
    consultant_email: str | None = None
    department: str | None = None
    default_currency: str | None = None
    default_quote_terms: str | None = None
    customer_level: CustomerLevel | None = None
    status: CustomerStatus | None = None
    remark: str | None = None


class CustomerResponse(BaseModel):
    id: str
    customer_no: str
    name: str
    customer_type: CustomerType
    consultant_id: str | None = None
    consultant_email: str
    consultant_name: str
    department: str = ""
    default_currency: str
    default_quote_terms: str = ""
    customer_level: CustomerLevel
    status: CustomerStatus
    remark: str = ""
    created_at: datetime
    updated_at: datetime
    contacts: list[CustomerContactResponse] = Field(default_factory=list)


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int = 1
    page_size: int = 100


class Country(BaseModel):
    code: str
    name_cn: str
    name_en: str
    default_currency: str
    country_type: str = "单一国家"
    enabled: bool
    display_order: int = 0
    international_region: str = ""
    business_region: list[str] = Field(default_factory=list)
    region_remark: str = ""
    jurisdiction_id: str | None = None
    internal_code: str = ""
    display_code: str = ""
    jurisdiction_type: str = ""
    standard_code: str = ""
    is_enabled: bool | None = None
    iso_alpha2: str | None = None
    iso_alpha3: str | None = None
    iso_numeric: str | None = None
    un_m49_code: str | None = None
    wipo_st3_code: str | None = None
    source_name: str = ""
    source_url: str = ""
    source_version: str = ""
    source_note: str = ""
    last_verified_at: datetime | None = None
    source_verified: bool = False
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    review_status: Literal["pending_review", "verified", "needs_update", "deprecated"] = "pending_review"
    manual_override: bool = False
    remarks: str | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    delete_reason: str | None = None
    default_office_jurisdiction_id: str | None = None
    default_office_code: str = ""
    default_office_name_cn: str = ""
    default_office_name_en: str = ""
    default_office_type: str = ""
    default_office_source_note: str = ""

    @field_validator("business_region", mode="before")
    @classmethod
    def normalize_country_business_tags(cls, value: object) -> list[str]:
        return _normalize_business_tags(value)


class CountryUpdate(BaseModel):
    name_cn: str | None = Field(default=None, min_length=1)
    name_en: str | None = Field(default=None, min_length=1)
    default_currency: str | None = None
    country_type: str | None = None
    enabled: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    international_region: str | None = None
    business_region: list[str] | str | None = None
    region_remark: str | None = None
    internal_code: str | None = None
    display_code: str | None = None
    jurisdiction_type: str | None = None
    is_enabled: bool | None = None
    iso_alpha2: str | None = None
    iso_alpha3: str | None = None
    iso_numeric: str | None = None
    un_m49_code: str | None = None
    wipo_st3_code: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_version: str | None = None
    source_note: str | None = None
    last_verified_at: datetime | None = None
    source_verified: bool | None = None
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    manual_override: bool | None = None
    remarks: str | None = None
    default_office_jurisdiction_id: str | None = None
    default_office_code: str | None = None
    default_office_name_cn: str | None = None
    default_office_name_en: str | None = None
    default_office_type: str | None = None
    default_office_source_note: str | None = None

    @field_validator("jurisdiction_type")
    @classmethod
    def validate_jurisdiction_type(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        if value not in JURISDICTION_TYPES:
            raise ValueError("invalid jurisdiction_type")
        return value

    @field_validator("international_region")
    @classmethod
    def validate_geo_region(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        if value not in GEO_REGIONS:
            raise ValueError("invalid international_region")
        return value

    @field_validator("business_region", mode="before")
    @classmethod
    def validate_business_region(cls, value: object) -> list[str] | None:
        if value in (None, ""):
            return None
        return _normalize_business_tags(value)


class CountryCreate(BaseModel):
    reference_id: str = Field(min_length=1)
    code: str = ""
    name_cn: str = ""
    name_en: str = ""
    default_currency: str = "USD"
    country_type: str = "单一国家"
    enabled: bool = True
    display_order: int = Field(default=0, ge=0)
    international_region: str = ""
    business_region: list[str] | str = Field(default_factory=list)
    region_remark: str = ""
    internal_code: str = ""
    display_code: str = ""
    jurisdiction_type: str = "single_country"
    standard_code: str = ""
    is_enabled: bool | None = None
    source_name: str = ""
    source_url: str = ""
    source_version: str = ""
    source_note: str = ""
    source_verified: bool = False
    last_verified_at: datetime | None = None
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    review_status: Literal["pending_review", "verified", "needs_update", "deprecated"] = "pending_review"
    manual_override: bool = False
    remarks: str | None = None
    default_office_jurisdiction_id: str | None = None
    default_office_code: str = ""
    default_office_name_cn: str = ""
    default_office_name_en: str = ""
    default_office_type: str = ""
    default_office_source_note: str = ""

    @field_validator("business_region", mode="before")
    @classmethod
    def validate_create_business_region(cls, value: object) -> list[str]:
        return _normalize_business_tags(value)


class CountryDeleteRequest(BaseModel):
    delete_reason: str = ""


class CountryBulkFromReferenceRequest(BaseModel):
    reference_ids: list[str] = Field(min_length=1)
    staging_items: list["CountryBulkFromReferenceStagingItem"] = Field(default_factory=list)
    source_verified: bool = False
    source_verified_by: str | None = None
    source_verified_at: datetime | None = None
    batch_note: str = ""


class CountryBulkFromReferenceStagingItem(BaseModel):
    reference_id: str = Field(min_length=1)
    name_cn: str = ""
    name_en: str = ""
    display_code: str = ""
    jurisdiction_type: str = ""
    international_region: str = ""
    business_region: list[str] | str = Field(default_factory=list)
    default_office_name_cn: str = ""
    default_office_name_en: str = ""
    default_office_code: str = ""
    default_office_type: str = ""
    remarks: str = ""
    overwrite_existing_fields: bool = False
    review_status: Literal["pending_review", "verified", "needs_update", "deprecated"] = "pending_review"

    @field_validator("international_region")
    @classmethod
    def validate_staging_geo_region(cls, value: str) -> str:
        if value in ("", None):
            return ""
        if value not in GEO_REGIONS:
            raise ValueError("invalid international_region")
        return value

    @field_validator("jurisdiction_type")
    @classmethod
    def validate_staging_jurisdiction_type(cls, value: str) -> str:
        if value in ("", None):
            return ""
        if value not in JURISDICTION_TYPES:
            raise ValueError("invalid jurisdiction_type")
        return value

    @field_validator("business_region", mode="before")
    @classmethod
    def validate_staging_business_region(cls, value: object) -> list[str]:
        return _normalize_business_tags(value)


class CountryBulkFromReferenceResult(BaseModel):
    reference_id: str
    standard_code: str = ""
    display_code: str = ""
    name_cn: str = ""
    name_en: str = ""
    status: str
    existence_status: str = ""
    reason: str = ""
    country: Country | None = None


class CountryBulkFromReferenceResponse(BaseModel):
    created_count: int = 0
    restored_count: int = 0
    added_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    created_items: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    restored_items: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    skipped_items: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    failed_items: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    added: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    restored: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    skipped: list[CountryBulkFromReferenceResult] = Field(default_factory=list)
    failed: list[CountryBulkFromReferenceResult] = Field(default_factory=list)


class JurisdictionReferenceCandidate(BaseModel):
    reference_id: str
    jurisdiction_id: str | None = None
    standard_code: str
    display_code: str
    name_cn: str
    name_en: str
    aliases: list[str] = Field(default_factory=list)
    jurisdiction_type: str
    reference_category: str = "country"
    business_scope: list[str] = Field(default_factory=list)
    visibility_scope: str = "country_master_reference"
    candidate_status: str = "candidate"
    quote_selectable_default: bool = False
    not_selectable_reason: str = "未纳入当前报价范围"
    reserved_reason: str = ""
    geo_region: str = "Other"
    default_business_economic_regions: list[str] = Field(default_factory=list)
    source_id: str | None = None
    source_name: str = ""
    source_url: str = ""
    source_version: str = ""
    source_note: str = ""
    source_verified: bool = False
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    last_reviewed_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: str = "pending_review"
    is_active: bool = True
    default_currency_legacy: str = "USD"
    default_office_code: str = ""
    default_office_name_cn: str = ""
    default_office_name_en: str = ""
    default_office_type: str = ""
    default_office_source_note: str = ""

    @field_validator("default_business_economic_regions", mode="before")
    @classmethod
    def normalize_reference_business_tags(cls, value: object) -> list[str]:
        return _normalize_business_tags(value)


class JurisdictionReferenceListResponse(BaseModel):
    items: list[JurisdictionReferenceCandidate]
    total: int


class JurisdictionDataSource(BaseModel):
    source_id: str
    source_name: str
    source_type: str = "manual_verified"
    source_owner: str = ""
    source_url: str = ""
    source_version: str = ""
    applicable_fields: list[str] = Field(default_factory=list)
    verification_frequency: str = ""
    source_note: str = ""
    source_verified: bool = False
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    last_reviewed_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: str = "pending_review"
    is_active: bool = True


class JurisdictionDataSourceCreate(BaseModel):
    source_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_type: Literal["official", "internal", "third_party", "manual_verified"] = "manual_verified"
    source_owner: str = ""
    source_url: str = ""
    source_version: str = ""
    applicable_fields: list[str] = Field(default_factory=list)
    verification_frequency: str = ""
    source_note: str = ""
    source_verified: bool = False
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    last_reviewed_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: Literal["pending_review", "verified", "needs_update", "deprecated"] = "pending_review"
    is_active: bool = True


class JurisdictionDataSourceUpdate(BaseModel):
    source_name: str | None = Field(default=None, min_length=1)
    source_type: Literal["official", "internal", "third_party", "manual_verified"] | None = None
    source_owner: str | None = None
    source_url: str | None = None
    source_version: str | None = None
    applicable_fields: list[str] | None = None
    verification_frequency: str | None = None
    source_note: str | None = None
    source_verified: bool | None = None
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    last_reviewed_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: Literal["pending_review", "verified", "needs_update", "deprecated"] | None = None
    is_active: bool | None = None


class JurisdictionRegionTag(BaseModel):
    id: str
    jurisdiction_id: str
    jurisdiction_code: str = ""
    jurisdiction_name_cn: str = ""
    jurisdiction_name_en: str = ""
    tag_scheme: str
    tag_code: str
    tag_name_cn: str
    tag_name_en: str = ""
    source_id: str | None = None
    source_type: str = "manual_verified"
    source_name: str = ""
    source_url: str = ""
    source_note: str = ""
    source_verified: bool = False
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    last_reviewed_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: str = "pending_review"
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True
    reason_note: str = ""


class JurisdictionRegionTagCreate(BaseModel):
    jurisdiction_id: str = Field(min_length=1)
    tag_scheme: str = Field(min_length=1)
    tag_code: str = Field(min_length=1)
    tag_name_cn: str = Field(min_length=1)
    tag_name_en: str = ""
    source_id: str | None = None
    source_type: Literal["official", "internal", "third_party", "manual_verified"] = "manual_verified"
    source_name: str = ""
    source_url: str = ""
    source_note: str = ""
    source_verified: bool = False
    source_verified_at: datetime | None = None
    source_verified_by: str | None = None
    last_reviewed_at: datetime | None = None
    next_review_due_at: datetime | None = None
    review_status: Literal["pending_review", "verified", "needs_update", "deprecated"] = "pending_review"
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True
    reason_note: str = ""


class CountryPathRule(BaseModel):
    id: str
    country_code: str
    application_type: str
    filing_route: str
    route_detail: str = ""
    affects_official_fee: bool = False
    affects_local_service_fee: bool = False
    affects_inhouse_service_fee: bool = False
    affects_questions: bool = False
    affects_documents: bool = False
    affects_deadlines: bool = False
    affects_translation: bool = False
    affects_display: bool = False
    enabled: bool = True
    effective_date: date | None = None
    remark: str = ""


class CountryPathRuleUpdate(BaseModel):
    route_detail: str | None = None
    affects_official_fee: bool | None = None
    affects_local_service_fee: bool | None = None
    affects_inhouse_service_fee: bool | None = None
    affects_questions: bool | None = None
    affects_documents: bool | None = None
    affects_deadlines: bool | None = None
    affects_translation: bool | None = None
    affects_display: bool | None = None
    enabled: bool | None = None
    effective_date: date | None = None
    remark: str | None = None


class CountryPathRuleCreate(BaseModel):
    country_code: str = Field(min_length=1)
    application_type: str = Field(min_length=1)
    filing_route: str = Field(min_length=1)
    route_detail: str = ""
    affects_official_fee: bool = False
    affects_local_service_fee: bool = False
    affects_inhouse_service_fee: bool = False
    affects_questions: bool = False
    affects_documents: bool = False
    affects_deadlines: bool = False
    affects_translation: bool = False
    affects_display: bool = True
    enabled: bool = True
    effective_date: date | None = None
    remark: str = ""


class EntityTypeRule(BaseModel):
    id: str
    country_code: str
    application_type: str
    filing_route: str = ""
    enabled: bool = True
    entity_types: list[str] = Field(default_factory=list)
    affects_official_fee: bool = False
    affects_questions: bool = False
    requires_customer_confirmation: bool = False
    requires_supporting_documents: bool = False
    remark: str = ""


class EntityTypeRuleUpdate(BaseModel):
    enabled: bool | None = None
    entity_types: list[str] | None = None
    affects_official_fee: bool | None = None
    affects_questions: bool | None = None
    requires_customer_confirmation: bool | None = None
    requires_supporting_documents: bool | None = None
    remark: str | None = None


class EntityTypeRuleCreate(BaseModel):
    country_code: str = Field(min_length=1)
    application_type: str = Field(min_length=1)
    filing_route: str = ""
    enabled: bool = True
    entity_types: list[str] = Field(default_factory=list)
    affects_official_fee: bool = False
    affects_questions: bool = False
    requires_customer_confirmation: bool = False
    requires_supporting_documents: bool = False
    remark: str = ""


class LanguageRule(BaseModel):
    id: str
    country_code: str
    application_type: str
    accepted_languages: list[str] = Field(default_factory=list)
    source_language: str = ""
    target_language: str = ""
    intermediate_language: str = ""
    needs_second_translation: bool = False
    recommended_scheme_id: str = ""
    default_translation_fee: bool = False
    allow_scheme_switch: bool = True
    enabled: bool = True
    remark: str = ""


class LanguageRuleUpdate(BaseModel):
    accepted_languages: list[str] | None = None
    source_language: str | None = None
    target_language: str | None = None
    intermediate_language: str | None = None
    needs_second_translation: bool | None = None
    recommended_scheme_id: str | None = None
    default_translation_fee: bool | None = None
    allow_scheme_switch: bool | None = None
    enabled: bool | None = None
    remark: str | None = None


class LanguageRuleCreate(BaseModel):
    country_code: str = Field(min_length=1)
    application_type: str = Field(min_length=1)
    accepted_languages: list[str] = Field(default_factory=list)
    source_language: str = ""
    target_language: str = ""
    intermediate_language: str = ""
    needs_second_translation: bool = False
    recommended_scheme_id: str = ""
    default_translation_fee: bool = False
    allow_scheme_switch: bool = True
    enabled: bool = True
    remark: str = ""


class FxTaxRule(BaseModel):
    id: str
    country_code: str
    official_currency: str
    official_quote_currency: str
    local_service_currency: str
    local_service_currency_options: list[str] = Field(default_factory=list)
    quote_currency: str
    fx_rate: Decimal
    tax_rate: Decimal
    tax_included: bool = False
    lock_on_formal_quote: bool = True
    version: str = ""
    enabled: bool = True
    remark: str = ""


class FxTaxRuleUpdate(BaseModel):
    official_currency: str | None = None
    official_quote_currency: str | None = None
    local_service_currency: str | None = None
    local_service_currency_options: list[str] | None = None
    quote_currency: str | None = None
    fx_rate: Decimal | None = Field(default=None, ge=0)
    tax_rate: Decimal | None = Field(default=None, ge=0)
    tax_included: bool | None = None
    lock_on_formal_quote: bool | None = None
    version: str | None = None
    enabled: bool | None = None
    remark: str | None = None


class FxTaxRuleCreate(BaseModel):
    country_code: str = Field(min_length=1)
    official_currency: str = Field(min_length=1)
    official_quote_currency: str = Field(min_length=1)
    local_service_currency: str = Field(min_length=1)
    local_service_currency_options: list[str] = Field(default_factory=list)
    quote_currency: str = Field(min_length=1)
    fx_rate: Decimal = Field(default=Decimal("1"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0)
    tax_included: bool = False
    lock_on_formal_quote: bool = True
    version: str = ""
    enabled: bool = True
    remark: str = ""


class SpecialRule(BaseModel):
    id: str
    country_code: str
    application_type: str = ""
    filing_route: str = ""
    rule_type: str
    enabled: bool = True
    triggers_extra_fee: bool = False
    triggers_risk_warning: bool = False
    requires_customer_confirmation: bool = False
    risk_summary: str = ""
    linked_rule_code: str = ""
    remark: str = ""

class SpecialRuleUpdate(BaseModel):
    enabled: bool | None = None
    triggers_extra_fee: bool | None = None
    triggers_risk_warning: bool | None = None
    requires_customer_confirmation: bool | None = None
    risk_summary: str | None = None
    linked_rule_code: str | None = None
    remark: str | None = None


class SpecialRuleCreate(BaseModel):
    country_code: str = Field(min_length=1)
    application_type: str = ""
    filing_route: str = ""
    rule_type: str = Field(min_length=1)
    enabled: bool = True
    triggers_extra_fee: bool = False
    triggers_risk_warning: bool = False
    requires_customer_confirmation: bool = False
    risk_summary: str = ""
    linked_rule_code: str = ""
    remark: str = ""


class CountryConfigResponse(BaseModel):
    countries: list[Country]
    path_rules: list[CountryPathRule]
    entity_type_rules: list[EntityTypeRule]
    language_rules: list[LanguageRule]
    fx_tax_rules: list[FxTaxRule]
    special_rules: list[SpecialRule]


class FeeRule(BaseModel):
    id: str
    version_id: str | None = None
    country_code: str
    application_type: str
    filing_route: str
    pct_route_detail: str = ""
    entity_type: str = ""
    stage: str
    item_group_key: str = ""
    item_name: str
    fee_type: str
    fee_category: str = ""
    amount: Decimal
    currency: str
    quote_currency: str = ""
    is_multi_currency: bool = False
    tax_included: bool = False
    is_default: bool
    is_active: bool = True
    cost_nature: str
    trigger_condition: str = ""
    price_version: str = ""
    remark: str = ""


class FeeRuleCreate(BaseModel):
    version_id: str | None = None
    country_code: str = Field(min_length=1)
    application_type: str = Field(min_length=1)
    filing_route: str = Field(min_length=1)
    pct_route_detail: str = ""
    entity_type: str = ""
    stage: str = Field(min_length=1)
    item_group_key: str = ""
    item_name: str = Field(min_length=1)
    fee_type: str = Field(min_length=1)
    fee_category: str = "其他"
    amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(min_length=1)
    quote_currency: str = ""
    is_multi_currency: bool = False
    tax_included: bool = False
    is_default: bool = True
    is_active: bool = True
    cost_nature: str = "当前费用"
    trigger_condition: str = ""
    remark: str = ""


class TranslationRule(BaseModel):
    id: str
    item_name: str
    unit: str
    unit_price: Decimal
    currency: str
    min_fee: Decimal
    enabled: bool
    is_default: bool


class FeeRuleUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    quote_currency: str | None = None
    item_group_key: str | None = None
    fee_type: str | None = None
    fee_category: str | None = None
    trigger_condition: str | None = None
    tax_included: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    remark: str | None = None


class TranslationRuleUpdate(BaseModel):
    item_name: str | None = None
    unit: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    min_fee: Decimal | None = Field(default=None, ge=0)
    enabled: bool | None = None
    is_default: bool | None = None


class BootstrapResponse(BaseModel):
    users: list[User]
    countries: list[Country]
    application_types: list[str]
    filing_routes: list[str]
    currencies: list[str]
    statuses: list[str]
    fee_rules: list[FeeRule]
    translation_rules: list[TranslationRule]


class WorkbenchOptionsResponse(BaseModel):
    country_code: str = ""
    application_types: list[str] = Field(default_factory=list)
    filing_routes: list[str] = Field(default_factory=list)
    route_details: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)
    quote_currency: str = ""
    has_path_rules: bool = False


class QuoteJurisdictionOptionPreview(BaseModel):
    jurisdiction_id: str
    standard_code: str = ""
    display_code: str = ""
    quote_display_name: str = ""
    jurisdiction_type: str = ""
    quote_option_group: str = ""
    quote_business_lines: list[str] = Field(default_factory=list)
    legacy_country_code: str | None = None
    is_enabled: bool = False
    quote_selectable: bool = False
    not_selectable_reason: str | None = None
    geo_region: str = ""
    business_economic_regions: list[str] = Field(default_factory=list)


class QuotationGenerateRequest(BaseModel):
    client_name: str = Field(min_length=1)
    client_contact: str = ""
    consultant_email: str
    country_code: str
    application_type: str
    filing_route: str
    pct_route_detail: str = ""
    entity_type: str = ""
    currency: str
    has_case: bool = False
    case_title: str = ""
    applicant_count: int = Field(default=1, ge=0)
    priority_count: int = Field(default=0, ge=0)
    claim_count: int = Field(default=0, ge=0)
    description_pages: int = Field(default=0, ge=0)
    drawing_pages: int = Field(default=0, ge=0)
    needs_translation: bool = True
    translation_quantity_one: Decimal = Field(default=Decimal("0"), ge=0)
    translation_quantity_two: Decimal = Field(default=Decimal("0"), ge=0)
    remark: str = ""


class QuotationItem(BaseModel):
    id: str
    stage: str
    item_name: str
    fee_type: str
    amount: Decimal
    currency: str
    cost_nature: str
    remark: str = ""
    sort_order: int


class GeneratedQuotation(BaseModel):
    items: list[QuotationItem]
    current_stage_total: Decimal
    future_stage_total: Decimal
    total_amount: Decimal
    display_currency: str
    important_notes: list[str]


class QuotationDraftCreate(BaseModel):
    client_name: str = Field(min_length=1)
    client_contact: str = ""
    consultant_email: str | None = None
    country_codes: list[str] = Field(min_length=1)
    application_type: str
    filing_route: str
    pct_route_detail: str = ""
    entity_type: str = ""
    has_case: bool = False
    case_title: str = ""
    applicant_count: int = Field(default=1, ge=0)
    priority_count: int = Field(default=0, ge=0)
    claim_count: int = Field(default=0, ge=0)
    description_pages: int = Field(default=0, ge=0)
    drawing_pages: int = Field(default=0, ge=0)
    needs_translation: bool = True
    translation_quantity_one: Decimal = Field(default=Decimal("0"), ge=0)
    translation_quantity_two: Decimal = Field(default=Decimal("0"), ge=0)
    remark: str = ""


class QuotationDraftUpdate(BaseModel):
    client_name: str | None = Field(default=None, min_length=1)
    client_contact: str | None = None
    has_case: bool | None = None
    case_title: str | None = None
    applicant_count: int | None = Field(default=None, ge=0)
    priority_count: int | None = Field(default=None, ge=0)
    claim_count: int | None = Field(default=None, ge=0)
    description_pages: int | None = Field(default=None, ge=0)
    drawing_pages: int | None = Field(default=None, ge=0)
    needs_translation: bool | None = None
    translation_quantity_one: Decimal | None = Field(default=None, ge=0)
    translation_quantity_two: Decimal | None = Field(default=None, ge=0)
    remark: str | None = None


class QuotationDraftItemResponse(BaseModel):
    id: str
    draft_id: str
    country_code: str
    application_type: str
    filing_route: str
    pct_route_detail: str = ""
    entity_type: str = ""
    case_title: str = ""
    quote_currency: str
    current_stage_total: Decimal
    future_stage_total: Decimal
    total_amount: Decimal
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class QuotationDraftResponse(BaseModel):
    id: str
    draft_no: str
    consultant_id: str | None = None
    consultant_email: str
    consultant_name: str
    client_name: str
    client_contact: str = ""
    has_case: bool
    case_title: str = ""
    applicant_count: int
    priority_count: int
    claim_count: int
    description_pages: int
    drawing_pages: int
    needs_translation: bool
    translation_quantity_one: Decimal
    translation_quantity_two: Decimal
    status: str
    remark: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[QuotationDraftItemResponse]


class QuotationDraftListResponse(BaseModel):
    items: list[QuotationDraftResponse]
    total: int
    page: int = 1
    page_size: int = 100


class QuotationFromDraftsCreate(BaseModel):
    draft_item_ids: list[str] = Field(min_length=1)
    remark: str = ""


class QuotationCreate(QuotationGenerateRequest):
    status: QuotationStatus = "已生成报价"


class QuotationResponse(QuotationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quotation_no: str
    consultant_name: str
    items: list[QuotationItem]
    current_stage_total: Decimal
    future_stage_total: Decimal
    total_amount: Decimal
    next_followup_date: date | None = None
    last_followup_at: datetime | None = None
    is_sent: bool
    is_confirmed: bool
    is_opened: bool
    created_at: datetime
    updated_at: datetime


class QuotationListResponse(BaseModel):
    items: list[QuotationResponse]
    total: int
    page: int = 1
    page_size: int = 100


class QuotationStatusUpdate(BaseModel):
    status: QuotationStatus


class FollowupCreate(BaseModel):
    method: FollowupMethod = "邮件"
    content: str = Field(min_length=1)
    next_followup_date: date | None = None


class FollowupResponse(FollowupCreate):
    id: str
    quotation_id: str
    user_id: str
    user_name: str
    followup_date: datetime
    created_at: datetime


class ApprovalRequestCreate(BaseModel):
    reason: str = Field(min_length=1)


class ApprovalRequestReview(BaseModel):
    status: Literal["已通过", "已拒绝"]
    reviewer_comment: str = ""
    valid_days: int = Field(default=30, ge=1, le=365)


class ApprovalRequestResponse(BaseModel):
    id: str
    consultant_id: str
    consultant_email: str
    request_type: str
    open_unconverted_count: int
    status: str
    reason: str
    reviewer_id: str | None = None
    reviewer_comment: str | None = None
    reviewed_at: datetime | None = None
    valid_until: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StatisticsResponse(BaseModel):
    quote_count: int
    current_stage_total: Decimal
    future_stage_total: Decimal
    total_amount: Decimal
    sent_count: int
    confirmed_count: int
    opened_count: int
    lost_count: int
    open_rate: Decimal
