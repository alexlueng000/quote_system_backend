from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.db import mysql
from app.schemas.quotation import (
    BootstrapResponse,
    Country,
    FeeRule,
    FeeRuleUpdate,
    GeneratedQuotation,
    QuotationCreate,
    QuotationGenerateRequest,
    QuotationItem,
    QuotationListResponse,
    QuotationResponse,
    QuotationStatusUpdate,
    StatisticsResponse,
    TranslationRule,
    TranslationRuleUpdate,
    User,
)

STATUSES = [
    "草稿",
    "已生成报价",
    "已发送客户",
    "跟进中",
    "需价格调整",
    "已确认",
    "已开卷",
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


def get_bootstrap() -> BootstrapResponse:
    return BootstrapResponse(
        users=[User.model_validate(user) for user in mysql.fetch_all_users()],
        countries=[Country.model_validate(country) for country in mysql.fetch_countries()],
        application_types=["发明", "实用新型", "外观"],
        filing_routes=["直接申请", "巴黎公约", "PCT进入"],
        currencies=["CNY", "USD", "EUR", "JPY", "KRW"],
        statuses=STATUSES,
        fee_rules=[FeeRule.model_validate(rule) for rule in mysql.fetch_fee_rules()],
        translation_rules=[TranslationRule.model_validate(rule) for rule in mysql.fetch_translation_rules()],
    )


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
        "is_sent": payload.status in {"已发送客户", "跟进中", "已确认", "已开卷"},
        "is_confirmed": payload.status in {"已确认", "已开卷"},
        "is_opened": payload.status == "已开卷",
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
    mysql.update_quotation_status(quotation_id, payload.status)
    return get_quotation(quotation_id)


def get_statistics(user_email: str | None = None) -> StatisticsResponse:
    return StatisticsResponse.model_validate(mysql.fetch_statistics(user_email))


def get_fee_rules() -> list[FeeRule]:
    return [FeeRule.model_validate(rule) for rule in mysql.fetch_fee_rules(include_inactive=True)]


def update_fee_rule(rule_id: str, payload: FeeRuleUpdate) -> FeeRule:
    values = payload.model_dump(exclude_unset=True)
    return FeeRule.model_validate(mysql.update_fee_rule(rule_id, values))


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
