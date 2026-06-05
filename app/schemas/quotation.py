from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["consultant", "admin", "approver"]
UserStatus = Literal["active", "inactive"]
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


class Country(BaseModel):
    code: str
    name_cn: str
    name_en: str
    default_currency: str
    enabled: bool


class FeeRule(BaseModel):
    id: str
    country_code: str
    application_type: str
    filing_route: str
    stage: str
    item_name: str
    fee_type: str
    amount: Decimal
    currency: str
    is_default: bool
    is_active: bool = True
    cost_nature: str
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


class QuotationGenerateRequest(BaseModel):
    client_name: str = Field(min_length=1)
    client_contact: str = ""
    consultant_email: str
    country_code: str
    application_type: str
    filing_route: str
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
