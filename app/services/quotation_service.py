from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.db import mysql
from app.reference.jurisdictions import JURISDICTION_REFERENCES
from app.schemas.quotation import (
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalRequestReview,
    BootstrapResponse,
    Country,
    CountryBulkFromReferenceRequest,
    CountryBulkFromReferenceResponse,
    CountryBulkFromReferenceResult,
    CountryCreate,
    CountryConfigResponse,
    CountryPathRule,
    CountryPathRuleCreate,
    CountryPathRuleUpdate,
    CountryUpdate,
    EntityTypeRule,
    EntityTypeRuleCreate,
    EntityTypeRuleUpdate,
    FeeRule,
    FeeRuleCreate,
    FeeRuleUpdate,
    FxTaxRule,
    FxTaxRuleCreate,
    FxTaxRuleUpdate,
    GeneratedQuotation,
    JurisdictionDataSource,
    JurisdictionDataSourceCreate,
    JurisdictionDataSourceUpdate,
    JurisdictionReferenceCandidate,
    JurisdictionReferenceListResponse,
    JurisdictionRegionTag,
    JurisdictionRegionTagCreate,
    LanguageRule,
    LanguageRuleCreate,
    LanguageRuleUpdate,
    QuoteJurisdictionOptionPreview,
    QuotationCreate,
    QuotationDraftCreate,
    QuotationDraftListResponse,
    QuotationDraftResponse,
    QuotationDraftUpdate,
    QuotationFromDraftsCreate,
    QuotationGenerateRequest,
    QuotationItem,
    QuotationListResponse,
    QuotationResponse,
    QuotationStatusUpdate,
    StatisticsResponse,
    SpecialRule,
    SpecialRuleCreate,
    SpecialRuleUpdate,
    TranslationRule,
    TranslationRuleUpdate,
    User,
    WorkbenchOptionsResponse,
)

STATUSES = [
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

IMPORTANT_NOTES = [
    "本报价基于正常新申请程序。",
    "加快程序、著录项目变更、后补程序、恢复程序、延期程序、复审、无效、异议及其他非常规事项，如客户另有需求，将另行报价确认。",
    "审查阶段、授权阶段及年费阶段费用为后续预估费用，实际费用将在相关程序发生时另行确认。",
    "如官方费用、外所费用、汇率或案件情况发生变化，最终费用可能相应调整。",
    "本报价在有效期内适用，超过有效期需重新确认。",
]

SENT_STATUSES = {
    "已发送客户",
    "待跟进",
    "跟进中",
    "跟进逾期",
    "需价格调整",
    "已确认",
    "部分开卷",
    "已开卷",
    "框架协议",
}
CONFIRMED_STATUSES = {"已确认", "部分开卷", "已开卷", "框架协议"}
OPENED_STATUSES = {"部分开卷", "已开卷"}
FOLLOWUP_REQUIRED_STATUSES = {"已发送客户", "跟进中"}
FORMAL_QUOTE_OVERDUE_BLOCK_DAYS = 7
FORMAL_QUOTE_UNCONVERTED_LIMIT = 10
APPROVAL_REQUEST_TYPE = "超过10条未转化继续报价"
APPLICATION_TYPES = ["发明", "实用新型", "外观"]
FILING_ROUTES = ["直接申请", "巴黎公约", "PCT进入"]


def get_bootstrap() -> BootstrapResponse:
    return BootstrapResponse(
        users=[User.model_validate(user) for user in mysql.fetch_all_users()],
        countries=[Country.model_validate(country) for country in mysql.fetch_countries()],
        application_types=APPLICATION_TYPES,
        filing_routes=FILING_ROUTES,
        currencies=["CNY", "USD", "EUR", "JPY", "KRW"],
        statuses=STATUSES,
        fee_rules=[FeeRule.model_validate(rule) for rule in mysql.fetch_fee_rules()],
        translation_rules=[TranslationRule.model_validate(rule) for rule in mysql.fetch_translation_rules()],
    )


def get_workbench_options(
    country_code: str | None = None,
    application_type: str | None = None,
    filing_route: str | None = None,
) -> WorkbenchOptionsResponse:
    countries = mysql.fetch_countries()
    country = _resolve_country(countries, country_code)
    if country is None:
        return WorkbenchOptionsResponse()

    config = mysql.fetch_country_config()
    path_rules = [
        rule
        for rule in config["path_rules"]
        if str(rule["country_code"]) == str(country["code"]) and _is_enabled_effective(rule)
    ]
    has_path_rules = bool(path_rules)

    application_types = _unique_strings(rule["application_type"] for rule in path_rules)
    if not application_types:
        application_types = APPLICATION_TYPES
    selected_application_type = (
        application_type if application_type in application_types else application_types[0]
    )

    route_rule_pool = [
        rule
        for rule in path_rules
        if str(rule["application_type"]) == selected_application_type
    ]
    filing_routes = _unique_strings(rule["filing_route"] for rule in route_rule_pool)
    if not filing_routes:
        filing_routes = FILING_ROUTES
    selected_filing_route = filing_route if filing_route in filing_routes else filing_routes[0]

    route_details = _unique_strings(
        rule["route_detail"]
        for rule in route_rule_pool
        if str(rule["filing_route"]) == selected_filing_route and str(rule.get("route_detail") or "")
    )
    entity_types = _entity_type_options(
        config["entity_type_rules"],
        str(country["code"]),
        selected_application_type,
        selected_filing_route,
    )

    return WorkbenchOptionsResponse(
        country_code=str(country["code"]),
        application_types=application_types,
        filing_routes=filing_routes,
        route_details=route_details,
        entity_types=entity_types,
        quote_currency=str(country["default_currency"]),
        has_path_rules=has_path_rules,
    )


def fetch_quote_jurisdiction_options_preview(
    selectable_only: bool = False,
    business_line: str | None = None,
    option_group: str | None = None,
) -> list[QuoteJurisdictionOptionPreview]:
    return [
        QuoteJurisdictionOptionPreview.model_validate(row)
        for row in mysql.fetch_quote_jurisdiction_options_preview(
            selectable_only=selectable_only,
            business_line=business_line,
            option_group=option_group,
        )
    ]


def list_jurisdiction_references(
    keyword: str = "",
    include_hidden: bool = False,
) -> JurisdictionReferenceListResponse:
    rows = mysql.fetch_jurisdiction_reference_registry(keyword=keyword, include_hidden=include_hidden)
    items = [JurisdictionReferenceCandidate.model_validate(row) for row in rows]
    return JurisdictionReferenceListResponse(items=items, total=len(items))


def get_jurisdiction_reference_candidate(reference_id: str) -> JurisdictionReferenceCandidate | None:
    row = mysql.fetch_jurisdiction_reference_registry_item(reference_id)
    return JurisdictionReferenceCandidate.model_validate(row) if row else None


def _reference_hidden_or_trademark_only(reference: JurisdictionReferenceCandidate) -> bool:
    business_scope = {item.lower() for item in reference.business_scope}
    return (
        reference.visibility_scope == "reserved_hidden"
        or reference.reserved_reason == "trademark_reserved"
        or (business_scope and business_scope <= {"trademark"})
    )


def list_jurisdiction_data_sources() -> list[JurisdictionDataSource]:
    return [JurisdictionDataSource.model_validate(row) for row in mysql.fetch_jurisdiction_data_sources()]


def create_jurisdiction_data_source(payload: JurisdictionDataSourceCreate) -> JurisdictionDataSource:
    row = mysql.upsert_jurisdiction_data_source(payload.model_dump())
    return JurisdictionDataSource.model_validate(row)


def update_jurisdiction_data_source(source_id: str, payload: JurisdictionDataSourceUpdate) -> JurisdictionDataSource:
    row = mysql.update_jurisdiction_data_source(source_id, payload.model_dump(exclude_unset=True))
    return JurisdictionDataSource.model_validate(row)


def list_jurisdiction_region_tags(
    jurisdiction_id: str | None = None,
    tag_code: str | None = None,
) -> list[JurisdictionRegionTag]:
    return [
        JurisdictionRegionTag.model_validate(row)
        for row in mysql.fetch_jurisdiction_region_tags(jurisdiction_id=jurisdiction_id, tag_code=tag_code)
    ]


def create_jurisdiction_region_tag(
    payload: JurisdictionRegionTagCreate,
    current_user: dict[str, object],
) -> JurisdictionRegionTag:
    actor = str(current_user.get("email") or current_user.get("id") or "local_admin")
    row = mysql.insert_jurisdiction_region_tag(payload.model_dump(), actor=actor)
    return JurisdictionRegionTag.model_validate(row)


def generate_quotation(payload: QuotationGenerateRequest) -> GeneratedQuotation:
    matched_rules = [
        rule
        for rule in [FeeRule.model_validate(item) for item in mysql.fetch_fee_rules()]
        if rule.country_code == payload.country_code
        and rule.application_type == payload.application_type
        and rule.filing_route == payload.filing_route
        and rule.is_default
        and rule.is_active
    ]

    items: list[QuotationItem] = []
    sort_order = 1
    for rule in matched_rules:
        items.append(
            QuotationItem(
                id=rule.id,
                stage=rule.stage,
                item_name=rule.item_name,
                fee_type=rule.fee_type,
                amount=rule.amount,
                currency=rule.currency,
                cost_nature=rule.cost_nature,
                remark=rule.remark,
                sort_order=sort_order,
            )
        )
        sort_order += 1

    if payload.needs_translation:
        quantities = [payload.translation_quantity_one, payload.translation_quantity_two]
        translation_rules = [
            TranslationRule.model_validate(item) for item in mysql.fetch_translation_rules()
        ]
        for index, rule in enumerate(translation_rules):
            if not rule.enabled or not rule.is_default:
                continue
            quantity = quantities[index] if index < len(quantities) else Decimal("0")
            amount = max(quantity * rule.unit_price, rule.min_fee) if quantity > 0 else rule.min_fee
            items.append(
                QuotationItem(
                    id=rule.id,
                    stage="申请阶段",
                    item_name=rule.item_name,
                    fee_type="翻译费",
                    amount=amount,
                    currency=rule.currency,
                    cost_nature="当前费用",
                    remark=f"{quantity.normalize()} {rule.unit}",
                    sort_order=sort_order,
                )
            )
            sort_order += 1

    if not any(item.stage == "年费阶段" for item in items):
        items.append(
            QuotationItem(
                id="annuity-note",
                stage="年费阶段",
                item_name="后续年费",
                fee_type="年费",
                amount=Decimal("0"),
                currency=payload.currency,
                cost_nature="后续预估",
                remark="后续年费将在届期前另行报价确认",
                sort_order=sort_order,
            )
        )

    current_total = sum(
        item.amount for item in items if item.cost_nature == "当前费用" and item.currency == payload.currency
    )
    future_total = sum(
        item.amount for item in items if item.cost_nature == "后续预估" and item.currency == payload.currency
    )
    total_amount = current_total + future_total

    return GeneratedQuotation(
        items=items,
        current_stage_total=current_total,
        future_stage_total=future_total,
        total_amount=total_amount,
        display_currency=payload.currency,
        important_notes=IMPORTANT_NOTES,
    )


def create_quotation_draft(
    payload: QuotationDraftCreate,
    current_user: dict[str, object],
) -> QuotationDraftResponse:
    now = datetime.now(timezone.utc)
    draft_id = str(uuid4())
    consultant = _resolve_draft_consultant(payload, current_user)
    draft_no = f"D{now:%Y%m%d}-ZYIP-{uuid4().hex[:5].upper()}"
    countries = {country["code"]: country for country in mysql.fetch_countries()}

    record: dict[str, object] = {
        "id": draft_id,
        "draft_no": draft_no,
        "consultant_id": consultant["id"],
        "consultant_email": consultant["email"],
        "consultant_name": consultant["name"],
        "client_name": payload.client_name,
        "client_contact": payload.client_contact,
        "has_case": payload.has_case,
        "case_title": payload.case_title,
        "applicant_count": payload.applicant_count,
        "priority_count": payload.priority_count,
        "claim_count": payload.claim_count,
        "description_pages": payload.description_pages,
        "drawing_pages": payload.drawing_pages,
        "needs_translation": payload.needs_translation,
        "translation_quantity_one": payload.translation_quantity_one,
        "translation_quantity_two": payload.translation_quantity_two,
        "status": "草稿",
        "remark": payload.remark,
        "created_at": now,
        "updated_at": now,
    }

    items: list[dict[str, object]] = []
    for sort_order, country_code in enumerate(payload.country_codes, start=1):
        country = countries.get(country_code)
        if country is None:
            raise KeyError(f"COUNTRY_NOT_FOUND:{country_code}")
        _validate_workbench_selection(
            country_code=country_code,
            application_type=payload.application_type,
            filing_route=payload.filing_route,
            pct_route_detail=payload.pct_route_detail,
            entity_type=payload.entity_type,
        )
        quote_currency = str(country["default_currency"])
        generated = generate_quotation(
            QuotationGenerateRequest(
                client_name=payload.client_name,
                client_contact=payload.client_contact,
                consultant_email=str(consultant["email"]),
                country_code=country_code,
                application_type=payload.application_type,
                filing_route=payload.filing_route,
                pct_route_detail=payload.pct_route_detail,
                entity_type=payload.entity_type,
                currency=quote_currency,
                has_case=payload.has_case,
                case_title=payload.case_title,
                applicant_count=payload.applicant_count,
                priority_count=payload.priority_count,
                claim_count=payload.claim_count,
                description_pages=payload.description_pages,
                drawing_pages=payload.drawing_pages,
                needs_translation=payload.needs_translation,
                translation_quantity_one=payload.translation_quantity_one,
                translation_quantity_two=payload.translation_quantity_two,
                remark=payload.remark,
            )
        )
        items.append(
            {
                "id": f"{draft_id}-{sort_order:03d}",
                "draft_id": draft_id,
                "country_code": country_code,
                "application_type": payload.application_type,
                "filing_route": payload.filing_route,
                "pct_route_detail": payload.pct_route_detail,
                "entity_type": payload.entity_type,
                "case_title": payload.case_title,
                "quote_currency": quote_currency,
                "current_stage_total": generated.current_stage_total,
                "future_stage_total": generated.future_stage_total,
                "total_amount": generated.total_amount,
                "status": "草稿",
                "sort_order": sort_order,
                "created_at": now,
                "updated_at": now,
            }
        )

    mysql.insert_quotation_draft(record, items)
    saved = mysql.fetch_quotation_draft(draft_id)
    if saved is None:
        raise KeyError(draft_id)
    return QuotationDraftResponse.model_validate(saved)


def get_quotation_drafts(user_email: str | None) -> QuotationDraftListResponse:
    drafts = [QuotationDraftResponse.model_validate(row) for row in mysql.fetch_quotation_drafts(user_email)]
    return QuotationDraftListResponse(items=drafts, total=len(drafts))


def get_quotation_draft(draft_id: str) -> QuotationDraftResponse:
    draft = mysql.fetch_quotation_draft(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    return QuotationDraftResponse.model_validate(draft)


def update_quotation_draft(
    draft_id: str,
    payload: QuotationDraftUpdate,
) -> QuotationDraftResponse:
    values = payload.model_dump(exclude_unset=True)
    draft = mysql.update_quotation_draft(draft_id, values)
    return QuotationDraftResponse.model_validate(draft)


def delete_quotation_draft_item(draft_id: str, item_id: str) -> QuotationDraftResponse:
    draft = mysql.delete_quotation_draft_item(draft_id, item_id)
    return QuotationDraftResponse.model_validate(draft)


def create_quotation_from_drafts(
    payload: QuotationFromDraftsCreate,
    current_user: dict[str, object],
) -> QuotationResponse:
    draft_items = mysql.fetch_draft_items_for_formal_quote(payload.draft_item_ids)
    if len(draft_items) != len(set(payload.draft_item_ids)):
        raise KeyError("DRAFT_ITEM_NOT_FOUND")
    if not draft_items:
        raise KeyError("DRAFT_ITEM_NOT_FOUND")

    consultant_emails = {str(item["consultant_email"]) for item in draft_items}
    client_names = {str(item["client_name"]) for item in draft_items}
    if len(consultant_emails) != 1:
        raise ValueError("DRAFT_ITEMS_MIXED_CONSULTANTS")
    if len(client_names) != 1:
        raise ValueError("DRAFT_ITEMS_MIXED_CLIENTS")
    if current_user["role"] != "admin" and str(current_user["email"]) not in consultant_emails:
        raise PermissionError("DRAFT_FORBIDDEN")
    consultant_email = next(iter(consultant_emails))
    _ensure_formal_quote_allowed(consultant_email)

    now = datetime.now(timezone.utc)
    quotation_id = str(uuid4())
    quotation_no = f"{now:%Y%m%d}-ZYIP-{uuid4().hex[:5].upper()}"
    first = draft_items[0]
    primary_currency = str(first["quote_currency"])
    country_codes = _unique_strings(item["country_code"] for item in draft_items)
    draft_ids = _unique_strings(item["draft_id"] for item in draft_items)
    current_total = sum(
        Decimal(item["current_stage_total"])
        for item in draft_items
        if str(item["quote_currency"]) == primary_currency
    )
    future_total = sum(
        Decimal(item["future_stage_total"])
        for item in draft_items
        if str(item["quote_currency"]) == primary_currency
    )
    total_amount = current_total + future_total

    record: dict[str, object] = {
        "id": quotation_id,
        "quotation_no": quotation_no,
        "source_draft_ids_json": json.dumps(draft_ids, ensure_ascii=False),
        "consultant_id": first["consultant_id"],
        "consultant_email": first["consultant_email"],
        "consultant_name": first["consultant_name"],
        "client_name": first["client_name"],
        "client_contact": first["client_contact"],
        "country_code": country_codes[0],
        "country_codes_json": json.dumps(country_codes, ensure_ascii=False),
        "application_type": first["application_type"],
        "filing_route": first["filing_route"],
        "currency": primary_currency,
        "has_case": first["has_case"],
        "case_title": first["case_title"],
        "applicant_count": first["applicant_count"],
        "priority_count": first["priority_count"],
        "claim_count": first["claim_count"],
        "description_pages": first["description_pages"],
        "drawing_pages": first["drawing_pages"],
        "needs_translation": first["needs_translation"],
        "translation_quantity_one": first["translation_quantity_one"],
        "translation_quantity_two": first["translation_quantity_two"],
        "current_stage_total": current_total,
        "future_stage_total": future_total,
        "total_amount": total_amount,
        "status": "已生成报价",
        "is_sent": False,
        "is_confirmed": False,
        "is_opened": False,
        "opened_reference": "",
        "remark": payload.remark,
        "created_at": now,
        "updated_at": now,
    }
    quotation_items = [
        _build_formal_item(quotation_id, item, sort_order)
        for sort_order, item in enumerate(draft_items, start=1)
    ]
    mysql.insert_quotation_from_drafts(
        record,
        quotation_items,
        draft_ids,
        list(dict.fromkeys(payload.draft_item_ids)),
    )
    saved = mysql.fetch_quotation(quotation_id)
    if saved is None:
        raise KeyError(quotation_id)
    return QuotationResponse.model_validate(saved)


def create_quotation(payload: QuotationCreate) -> QuotationResponse:
    generated = generate_quotation(payload)
    now = datetime.now(timezone.utc)
    quotation_id = str(uuid4())
    consultant = _find_user(payload.consultant_email)
    quotation_no = f"{now:%Y%m%d}-ZYIP-{uuid4().hex[:5].upper()}"
    saved_items = [
        item.model_copy(update={"id": f"{quotation_id}-{item.sort_order:03d}"})
        for item in generated.items
    ]

    record: dict[str, object] = {
        **payload.model_dump(),
        "id": quotation_id,
        "quotation_no": quotation_no,
        "consultant_id": consultant.id if consultant else None,
        "consultant_name": consultant.name if consultant else payload.consultant_email,
        "items": [item.model_dump() for item in saved_items],
        "current_stage_total": generated.current_stage_total,
        "future_stage_total": generated.future_stage_total,
        "total_amount": generated.total_amount,
        "is_sent": payload.status in SENT_STATUSES,
        "is_confirmed": payload.status in CONFIRMED_STATUSES,
        "is_opened": payload.status in OPENED_STATUSES,
        "opened_reference": "",
        "created_at": now,
        "updated_at": now,
    }
    mysql.insert_quotation(record, saved_items)
    return QuotationResponse.model_validate(record)


def get_quotations(user_email: str | None) -> QuotationListResponse:
    records = mysql.fetch_quotations(user_email)
    items = [QuotationResponse.model_validate(record) for record in records]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return QuotationListResponse(items=items, total=len(items))


def get_quotation(quotation_id: str) -> QuotationResponse:
    record = mysql.fetch_quotation(quotation_id)
    if record is None:
        raise KeyError(quotation_id)
    return QuotationResponse.model_validate(record)


def update_quotation_status(quotation_id: str, payload: QuotationStatusUpdate) -> QuotationResponse:
    quotation = get_quotation(quotation_id)
    if payload.status in FOLLOWUP_REQUIRED_STATUSES and quotation.next_followup_date is None:
        raise ValueError("FOLLOWUP_DATE_REQUIRED")
    mysql.update_quotation_status(quotation_id, payload.status)
    return get_quotation(quotation_id)


def create_followup(
    quotation_id: str,
    payload,
    current_user: dict[str, object],
):
    followup = mysql.insert_followup(
        {
            "quotation_id": quotation_id,
            "user_id": current_user["id"],
            "consultant_email": current_user["email"],
            "method": payload.method,
            "content": payload.content,
            "next_followup_date": payload.next_followup_date,
        }
    )
    return followup


def get_approval_requests(current_user: dict[str, object]) -> list[ApprovalRequestResponse]:
    if current_user["role"] in {"admin", "approver"}:
        requests = mysql.fetch_approval_requests()
    else:
        requests = mysql.fetch_approval_requests(str(current_user["email"]))
    return [ApprovalRequestResponse.model_validate(row) for row in requests]


def create_approval_request(
    payload: ApprovalRequestCreate,
    current_user: dict[str, object],
) -> ApprovalRequestResponse:
    open_unconverted_count = mysql.count_open_unconverted_quotations(str(current_user["email"]))
    request = mysql.insert_approval_request(
        {
            "consultant_id": current_user["id"],
            "consultant_email": current_user["email"],
            "request_type": APPROVAL_REQUEST_TYPE,
            "open_unconverted_count": open_unconverted_count,
            "reason": payload.reason,
        }
    )
    return ApprovalRequestResponse.model_validate(request)


def review_approval_request(
    request_id: str,
    payload: ApprovalRequestReview,
    current_user: dict[str, object],
) -> ApprovalRequestResponse:
    request = mysql.review_approval_request(
        request_id,
        str(current_user["id"]),
        payload.status,
        payload.reviewer_comment,
        payload.valid_days,
    )
    return ApprovalRequestResponse.model_validate(request)


def get_statistics(user_email: str | None = None) -> StatisticsResponse:
    return StatisticsResponse.model_validate(mysql.fetch_statistics(user_email))


def get_fee_rules() -> list[FeeRule]:
    return [FeeRule.model_validate(rule) for rule in mysql.fetch_fee_rules(include_inactive=True)]


def get_country_config(include_deleted: bool = False) -> CountryConfigResponse:
    config = mysql.fetch_country_config(include_deleted=include_deleted)
    return CountryConfigResponse(
        countries=[Country.model_validate(item) for item in config["countries"]],
        path_rules=[CountryPathRule.model_validate(item) for item in config["path_rules"]],
        entity_type_rules=[
            EntityTypeRule.model_validate(item)
            for item in config["entity_type_rules"]
        ],
        language_rules=[LanguageRule.model_validate(item) for item in config["language_rules"]],
        fx_tax_rules=[FxTaxRule.model_validate(item) for item in config["fx_tax_rules"]],
        special_rules=[SpecialRule.model_validate(item) for item in config["special_rules"]],
    )


def create_country_config(payload: CountryCreate, current_user: dict[str, object]) -> Country:
    reference = get_jurisdiction_reference_candidate(payload.reference_id)
    if reference is None:
        raise KeyError("JURISDICTION_REFERENCE_NOT_FOUND")
    if _reference_hidden_or_trademark_only(reference):
        raise ValueError("REFERENCE_NOT_AVAILABLE_FOR_COUNTRY_MASTER")
    verified_at = payload.last_verified_at or payload.source_verified_at or datetime.now(timezone.utc)
    display_code = payload.display_code.strip() or reference.display_code
    name_cn = payload.name_cn.strip() or reference.name_cn
    name_en = payload.name_en.strip() or reference.name_en
    enabled = bool(payload.enabled)
    manual_override = (
        payload.manual_override
        or display_code != reference.display_code
        or name_cn != reference.name_cn
        or name_en != reference.name_en
    )
    values = {
        **payload.model_dump(),
        "code": reference.standard_code,
        "internal_code": reference.standard_code,
        "standard_code": reference.standard_code,
        "display_code": display_code,
        "name_cn": name_cn,
        "name_en": name_en,
        "enabled": enabled,
        "country_type": _jurisdiction_type_label(reference.jurisdiction_type),
        "jurisdiction_type": reference.jurisdiction_type,
        "international_region": reference.geo_region,
        "business_region": payload.business_region or list(reference.default_business_economic_regions),
        "source_name": reference.source_name,
        "source_url": reference.source_url,
        "source_version": reference.source_version,
        "source_note": reference.source_note,
        # Legacy compatibility only. Currency rules belong in the FX/tax module.
        "default_currency": reference.default_currency_legacy,
        "is_enabled": enabled,
        "quote_selectable": reference.quote_selectable_default,
        "quote_business_lines_json": json.dumps(reference.business_scope, ensure_ascii=False),
        "quote_option_group": reference.reference_category,
        "quote_display_name": f"{name_cn} ({display_code})",
        "not_selectable_reason": reference.not_selectable_reason,
        "source_verified": True,
        "last_verified_at": verified_at,
        "source_verified_at": verified_at,
        "source_verified_by": payload.source_verified_by or str(current_user.get("email") or current_user.get("id") or "local_admin"),
        "manual_override": manual_override,
    }
    return Country.model_validate(mysql.insert_country_config(values))


def create_countries_from_reference_bulk(
    payload: CountryBulkFromReferenceRequest,
    current_user: dict[str, object],
) -> CountryBulkFromReferenceResponse:
    verified_at = payload.source_verified_at or datetime.now(timezone.utc)
    verified_by = payload.source_verified_by or str(
        current_user.get("email") or current_user.get("id") or "local_admin"
    )
    response = CountryBulkFromReferenceResponse()
    seen_reference_ids: set[str] = set()

    for reference_id in payload.reference_ids:
        if reference_id in seen_reference_ids:
            response.skipped.append(
                CountryBulkFromReferenceResult(
                    reference_id=reference_id,
                    status="skipped",
                    existence_status="duplicate_request",
                    reason="请求中重复选择，已跳过",
                )
            )
            continue
        seen_reference_ids.add(reference_id)

        reference = get_jurisdiction_reference_candidate(reference_id)
        if reference is None:
            response.failed.append(
                CountryBulkFromReferenceResult(
                    reference_id=reference_id,
                    status="failed",
                    existence_status="not_exists",
                    reason="本地 reference 不存在或已停用",
                )
            )
            continue
        if _reference_hidden_or_trademark_only(reference):
            response.skipped.append(
                CountryBulkFromReferenceResult(
                    reference_id=reference.reference_id,
                    standard_code=reference.standard_code,
                    display_code=reference.display_code,
                    name_cn=reference.name_cn,
                    name_en=reference.name_en,
                    status="skipped",
                    existence_status="hidden_or_trademark_only",
                    reason="商标或隐藏 reference 默认不可见、不可选，已跳过",
                )
            )
            continue

        base_result = {
            "reference_id": reference.reference_id,
            "standard_code": reference.standard_code,
            "display_code": reference.display_code,
            "name_cn": reference.name_cn,
            "name_en": reference.name_en,
        }
        existence = mysql.inspect_country_reference_status(reference.standard_code, reference.display_code)
        existence_status = str(existence.get("status") or "not_exists")
        if existence_status == "active_exists":
            response.skipped.append(
                CountryBulkFromReferenceResult(
                    **base_result,
                    status="skipped",
                    existence_status=existence_status,
                    reason="主档中存在且未删除，已跳过",
                )
            )
            continue
        if existence_status in {"soft_deleted_exists", "legacy_exists_only"}:
            try:
                country = mysql.restore_country_config_from_reference(
                    {
                        "code": reference.standard_code,
                        "name_cn": reference.name_cn,
                        "name_en": reference.name_en,
                        "enabled": True,
                        "business_region": list(reference.default_business_economic_regions),
                        "region_remark": payload.batch_note,
                        "country_type": _jurisdiction_type_label(reference.jurisdiction_type),
                        "default_currency": reference.default_currency_legacy,
                        "internal_code": reference.standard_code,
                        "standard_code": reference.standard_code,
                        "display_code": reference.display_code,
                        "jurisdiction_type": reference.jurisdiction_type,
                        "is_enabled": True,
                        "international_region": reference.geo_region,
                        "source_name": reference.source_name,
                        "source_url": reference.source_url,
                        "source_version": reference.source_version,
                        "source_note": reference.source_note,
                        "source_verified": True,
                        "source_verified_at": verified_at,
                        "last_verified_at": verified_at,
                        "source_verified_by": verified_by,
                        "manual_override": False,
                        "remarks": payload.batch_note,
                    },
                    existence,
                )
            except Exception as exc:
                response.failed.append(
                    CountryBulkFromReferenceResult(
                        **base_result,
                        status="failed",
                        existence_status=existence_status,
                        reason=str(exc) or "恢复失败",
                    )
                )
                continue

            response.restored.append(
                CountryBulkFromReferenceResult(
                    **base_result,
                    status="restored",
                    existence_status=existence_status,
                    reason="已恢复到主档",
                    country=Country.model_validate(country),
                )
            )
            continue

        try:
            country = create_country_config(
                CountryCreate(
                    reference_id=reference.reference_id,
                    code=reference.standard_code,
                    name_cn=reference.name_cn,
                    name_en=reference.name_en,
                    enabled=True,
                    business_region=list(reference.default_business_economic_regions),
                    region_remark=payload.batch_note,
                    internal_code=reference.standard_code,
                    standard_code=reference.standard_code,
                    display_code=reference.display_code,
                    jurisdiction_type=reference.jurisdiction_type,
                    is_enabled=True,
                    source_note=reference.source_note,
                    source_verified=True,
                    source_verified_at=verified_at,
                    last_verified_at=verified_at,
                    source_verified_by=verified_by,
                    manual_override=False,
                    remarks=payload.batch_note,
                ),
                current_user,
            )
        except Exception as exc:
            response.failed.append(
                CountryBulkFromReferenceResult(
                    **base_result,
                    status="failed",
                    existence_status=existence_status,
                    reason=str(exc) or "新增失败",
                )
            )
            continue

        response.added.append(
            CountryBulkFromReferenceResult(
                **base_result,
                status="created",
                existence_status=existence_status,
                reason="新增成功",
                country=country,
            )
        )

    response.created_items = response.added
    response.restored_items = response.restored
    response.skipped_items = response.skipped
    response.failed_items = response.failed
    response.created_count = len(response.created_items)
    response.restored_count = len(response.restored_items)
    response.added_count = response.created_count
    response.skipped_count = len(response.skipped)
    response.failed_count = len(response.failed)
    return response


def update_country_config(country_code: str, payload: CountryUpdate) -> Country:
    values = payload.model_dump(exclude_unset=True)
    return Country.model_validate(mysql.update_country_config(country_code, values))


def delete_country_config(
    country_code: str,
    delete_reason: str,
    current_user: dict[str, object],
) -> None:
    deleted_by = str(current_user.get("email") or current_user.get("id") or "")
    mysql.soft_delete_country_config(country_code, deleted_by, delete_reason)


def restore_country_config(country_code: str, current_user: dict[str, object]) -> Country:
    code = country_code.upper()
    reference = next(
        (
            item
            for item in JURISDICTION_REFERENCES
            if item.is_active and code in {item.standard_code.upper(), item.display_code.upper()}
        ),
        None,
    )
    verified_at = datetime.now(timezone.utc)
    verified_by = str(current_user.get("email") or current_user.get("id") or "local_admin")
    if reference is not None:
        jurisdiction_type = "special_region" if code in {"HK", "MO", "TW"} else reference.jurisdiction_type
        record = {
            "code": reference.standard_code,
            "name_cn": reference.name_cn,
            "name_en": reference.name_en,
            "enabled": True,
            "business_region": list(reference.default_business_economic_regions),
            "country_type": _jurisdiction_type_label(jurisdiction_type),
            "default_currency": reference.default_currency_legacy,
            "internal_code": reference.standard_code,
            "standard_code": reference.standard_code,
            "display_code": reference.display_code,
            "jurisdiction_type": jurisdiction_type,
            "is_enabled": True,
            "international_region": reference.geo_region,
            "source_name": reference.source_name,
            "source_url": reference.source_url,
            "source_version": reference.source_version,
            "source_note": reference.source_note,
            "source_verified": True,
            "source_verified_at": verified_at,
            "last_verified_at": verified_at,
            "source_verified_by": verified_by,
            "manual_override": False,
        }
        existence = mysql.inspect_country_reference_status(reference.standard_code, reference.display_code)
    else:
        rows = mysql.fetch_country_config(include_deleted=True)["countries"]
        existing = next((item for item in rows if str(item.get("code") or "").upper() == code), None)
        if existing is None:
            raise KeyError(code)
        record = {
            **existing,
            "code": code,
            "enabled": True,
            "is_enabled": True,
            "source_verified": True,
            "source_verified_at": verified_at,
            "last_verified_at": verified_at,
            "source_verified_by": verified_by,
        }
        existence = {"country_code": code, "status": "soft_deleted_exists"}
    return Country.model_validate(mysql.restore_country_config_from_reference(record, existence))


def update_country_path_rule(rule_id: str, payload: CountryPathRuleUpdate) -> CountryPathRule:
    values = payload.model_dump(exclude_unset=True)
    return CountryPathRule.model_validate(mysql.update_country_path_rule(rule_id, values))


def create_country_path_rule(payload: CountryPathRuleCreate) -> CountryPathRule:
    values = payload.model_dump()
    values["id"] = f"path-{uuid4().hex[:12]}"
    return CountryPathRule.model_validate(mysql.insert_country_path_rule(values))


def delete_country_path_rule(rule_id: str) -> None:
    mysql.delete_country_path_rule(rule_id)


def update_entity_type_rule(rule_id: str, payload: EntityTypeRuleUpdate) -> EntityTypeRule:
    values = payload.model_dump(exclude_unset=True)
    return EntityTypeRule.model_validate(mysql.update_entity_type_rule(rule_id, values))


def create_entity_type_rule(payload: EntityTypeRuleCreate) -> EntityTypeRule:
    values = payload.model_dump()
    values["id"] = f"entity-{uuid4().hex[:12]}"
    return EntityTypeRule.model_validate(mysql.insert_entity_type_rule(values))


def delete_entity_type_rule(rule_id: str) -> None:
    mysql.delete_entity_type_rule(rule_id)


def update_language_rule(rule_id: str, payload: LanguageRuleUpdate) -> LanguageRule:
    values = payload.model_dump(exclude_unset=True)
    return LanguageRule.model_validate(mysql.update_language_rule(rule_id, values))


def create_language_rule(payload: LanguageRuleCreate) -> LanguageRule:
    values = payload.model_dump()
    values["id"] = f"lang-{uuid4().hex[:12]}"
    return LanguageRule.model_validate(mysql.insert_language_rule(values))


def delete_language_rule(rule_id: str) -> None:
    mysql.delete_language_rule(rule_id)


def update_fx_tax_rule(rule_id: str, payload: FxTaxRuleUpdate) -> FxTaxRule:
    values = payload.model_dump(exclude_unset=True)
    return FxTaxRule.model_validate(mysql.update_fx_tax_rule(rule_id, values))


def create_fx_tax_rule(payload: FxTaxRuleCreate) -> FxTaxRule:
    values = payload.model_dump()
    values["id"] = f"fx-{uuid4().hex[:12]}"
    return FxTaxRule.model_validate(mysql.insert_fx_tax_rule(values))


def delete_fx_tax_rule(rule_id: str) -> None:
    mysql.delete_fx_tax_rule(rule_id)


def update_special_rule(rule_id: str, payload: SpecialRuleUpdate) -> SpecialRule:
    values = payload.model_dump(exclude_unset=True)
    return SpecialRule.model_validate(mysql.update_special_rule(rule_id, values))


def create_special_rule(payload: SpecialRuleCreate) -> SpecialRule:
    values = payload.model_dump()
    values["id"] = f"special-{uuid4().hex[:12]}"
    return SpecialRule.model_validate(mysql.insert_special_rule(values))


def delete_special_rule(rule_id: str) -> None:
    mysql.delete_special_rule(rule_id)


def update_fee_rule(rule_id: str, payload: FeeRuleUpdate) -> FeeRule:
    values = payload.model_dump(exclude_unset=True)
    return FeeRule.model_validate(mysql.update_fee_rule(rule_id, values))


def create_fee_rule(payload: FeeRuleCreate) -> FeeRule:
    values = payload.model_dump()
    values["id"] = f"fee-{uuid4().hex[:12]}"
    return FeeRule.model_validate(mysql.insert_fee_rule(values))


def delete_fee_rule(rule_id: str) -> None:
    mysql.delete_fee_rule(rule_id)


def get_translation_rules() -> list[TranslationRule]:
    return [
        TranslationRule.model_validate(rule)
        for rule in mysql.fetch_translation_rules(include_disabled=True)
    ]


def update_translation_rule(rule_id: str, payload: TranslationRuleUpdate) -> TranslationRule:
    values = payload.model_dump(exclude_unset=True)
    return TranslationRule.model_validate(mysql.update_translation_rule(rule_id, values))


def _find_user(email: str | None) -> User | None:
    user = mysql.fetch_user_by_email(email)
    return User.model_validate(user) if user else None


def _resolve_draft_consultant(
    payload: QuotationDraftCreate,
    current_user: dict[str, object],
) -> dict[str, object]:
    if current_user["role"] == "admin" and payload.consultant_email:
        user = mysql.fetch_user_by_email(payload.consultant_email)
        if user is None or user["status"] != "active":
            raise KeyError(f"CONSULTANT_NOT_FOUND:{payload.consultant_email}")
        return user
    return current_user


def _ensure_formal_quote_allowed(consultant_email: str) -> None:
    mysql.refresh_quotation_followup_statuses()
    overdue_count = mysql.count_overdue_followup_quotations(
        consultant_email,
        FORMAL_QUOTE_OVERDUE_BLOCK_DAYS,
    )
    if overdue_count > 0 and not mysql.has_valid_quote_unlock(consultant_email):
        raise ValueError("FORMAL_QUOTE_BLOCKED_OVERDUE_FOLLOWUP")

    open_unconverted_count = mysql.count_open_unconverted_quotations(consultant_email)
    if (
        open_unconverted_count > FORMAL_QUOTE_UNCONVERTED_LIMIT
        and not mysql.has_valid_quote_unlock(consultant_email)
    ):
        raise ValueError("FORMAL_QUOTE_BLOCKED_UNCONVERTED")


def _jurisdiction_type_label(value: str) -> str:
    labels = {
        "single_country": "单一国家",
        "special_region": "特殊地区",
        "regional_office": "区域局",
        "international_organization": "国际组织",
        "treaty_entry": "条约体系入口",
        "internal_business_object": "内部业务对象",
    }
    return labels.get(value, value)


def _resolve_country(
    countries: list[dict[str, object]],
    country_code: str | None,
) -> dict[str, object] | None:
    if country_code:
        for country in countries:
            if str(country["code"]) == country_code:
                return country
        return None
    return countries[0] if countries else None


def _is_enabled_effective(rule: dict[str, object]) -> bool:
    if not bool(rule.get("enabled")):
        return False
    effective_date = rule.get("effective_date")
    if effective_date is None or effective_date == "":
        return True
    if isinstance(effective_date, date):
        return effective_date <= date.today()
    try:
        return date.fromisoformat(str(effective_date)) <= date.today()
    except ValueError:
        return True


def _entity_type_options(
    rules: list[dict[str, object]],
    country_code: str,
    application_type: str,
    filing_route: str,
) -> list[str]:
    matched_rules = [
        rule
        for rule in rules
        if bool(rule.get("enabled"))
        and str(rule["country_code"]) == country_code
        and str(rule["application_type"]) == application_type
        and str(rule.get("filing_route") or "") in {"", filing_route}
    ]
    values: list[str] = []
    for rule in matched_rules:
        values.extend(str(item) for item in rule.get("entity_types", []) if str(item))
    return _unique_strings(values)


def _validate_workbench_selection(
    *,
    country_code: str,
    application_type: str,
    filing_route: str,
    pct_route_detail: str,
    entity_type: str,
) -> None:
    config = mysql.fetch_country_config()
    path_rules = [
        rule
        for rule in config["path_rules"]
        if str(rule["country_code"]) == country_code and _is_enabled_effective(rule)
    ]
    if not path_rules:
        return

    matched_path_rules = [
        rule
        for rule in path_rules
        if str(rule["application_type"]) == application_type
        and str(rule["filing_route"]) == filing_route
    ]
    if not matched_path_rules:
        raise ValueError("INVALID_WORKBENCH_SELECTION")

    route_details = _unique_strings(
        rule["route_detail"] for rule in matched_path_rules if str(rule.get("route_detail") or "")
    )
    if route_details and pct_route_detail not in route_details:
        raise ValueError("INVALID_WORKBENCH_ROUTE_DETAIL")

    entity_types = _entity_type_options(
        config["entity_type_rules"],
        country_code,
        application_type,
        filing_route,
    )
    if entity_types and entity_type and entity_type not in entity_types:
        raise ValueError("INVALID_WORKBENCH_ENTITY_TYPE")


def _unique_strings(values) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _build_formal_item(
    quotation_id: str,
    draft_item: dict[str, object],
    sort_order: int,
) -> dict[str, object]:
    country_code = str(draft_item["country_code"])
    application_type = str(draft_item["application_type"])
    filing_route = str(draft_item["filing_route"])
    quote_currency = str(draft_item["quote_currency"])
    current_total = Decimal(draft_item["current_stage_total"])
    future_total = Decimal(draft_item["future_stage_total"])
    return {
        "id": f"{quotation_id}-{sort_order:03d}",
        "quotation_id": quotation_id,
        "draft_item_id": draft_item["id"],
        "country_code": country_code,
        "application_type": application_type,
        "filing_route": filing_route,
        "pct_route_detail": draft_item.get("pct_route_detail") or "",
        "entity_type": draft_item.get("entity_type") or "",
        "case_title": draft_item.get("case_title") or "",
        "stage": "报价明细",
        "item_group_key": "draft-item-summary",
        "item_name": f"{country_code} {application_type} {filing_route} 报价合计",
        "fee_type": "报价合计",
        "fee_category": "其他",
        "amount": Decimal(draft_item["total_amount"]),
        "currency": quote_currency,
        "quote_currency": quote_currency,
        "tax_included": False,
        "cost_nature": "当前费用",
        "opening_status": "未开卷",
        "not_opened_reason": "",
        "remark": f"当前费用：{current_total}；后续预估：{future_total}",
        "sort_order": sort_order,
    }
