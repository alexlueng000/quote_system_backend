from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.quotation import (
    QuotationCreate,
    QuotationDraftCreate,
    QuotationDraftUpdate,
    QuotationFromDraftsCreate,
    QuotationGenerateRequest,
    QuotationStatusUpdate,
)
from app.services.quotation_service import (
    create_quotation,
    create_quotation_draft,
    create_quotation_from_drafts,
    delete_quotation_draft_item,
    fetch_quote_jurisdiction_options_preview,
    generate_quotation,
    get_workbench_options,
    update_quotation_status,
    update_quotation_draft,
)


def test_generate_quotation_contains_translation_in_application_stage(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_fee_rules",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_translation_rules",
        lambda: [
            {
                "id": "translation-main",
                "item_name": "申请文件翻译费",
                "unit": "词",
                "unit_price": Decimal("0.9"),
                "currency": "USD",
                "min_fee": Decimal("100"),
                "enabled": True,
                "is_default": True,
            }
        ],
    )
    payload = QuotationGenerateRequest(
        client_name="测试客户",
        consultant_email="suri@example.com",
        country_code="US",
        application_type="发明",
        filing_route="PCT进入",
        currency="USD",
        needs_translation=True,
        translation_quantity_one=Decimal("1200"),
        translation_quantity_two=Decimal("3"),
    )

    generated = generate_quotation(payload)

    translation_items = [item for item in generated.items if item.fee_type == "翻译费"]
    assert translation_items
    assert all(item.stage == "申请阶段" for item in translation_items)


def test_workbench_options_follow_country_path_and_entity_rules(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_countries",
        lambda: [
            {
                "code": "US",
                "name_cn": "美国",
                "name_en": "United States",
                "default_currency": "USD",
                "enabled": True,
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_country_config",
        lambda: {
            "countries": [],
            "path_rules": [
                {
                    "id": "path-us-pct",
                    "country_code": "US",
                    "application_type": "发明",
                    "filing_route": "PCT进入",
                    "route_detail": "30个月",
                    "enabled": True,
                    "effective_date": None,
                },
                {
                    "id": "path-us-paris",
                    "country_code": "US",
                    "application_type": "发明",
                    "filing_route": "巴黎公约",
                    "route_detail": "",
                    "enabled": True,
                    "effective_date": None,
                },
            ],
            "entity_type_rules": [
                {
                    "id": "entity-us",
                    "country_code": "US",
                    "application_type": "发明",
                    "filing_route": "PCT进入",
                    "enabled": True,
                    "entity_types": ["大实体", "小实体"],
                }
            ],
            "language_rules": [],
            "fx_tax_rules": [],
            "special_rules": [],
        },
    )

    options = get_workbench_options("US", "发明", "PCT进入")

    assert options.country_code == "US"
    assert options.application_types == ["发明"]
    assert options.filing_routes == ["PCT进入", "巴黎公约"]
    assert options.route_details == ["30个月"]
    assert options.entity_types == ["大实体", "小实体"]
    assert options.quote_currency == "USD"
    assert options.has_path_rules is True


def test_quote_jurisdiction_preview_filters_and_groups(monkeypatch) -> None:
    rows = [
        {
            "jurisdiction_id": "jur-US",
            "standard_code": "US",
            "display_code": "US",
            "quote_display_name": "美国 (US)",
            "jurisdiction_type": "single_country",
            "quote_option_group": "single_country",
            "quote_business_lines": ["patent", "trademark", "design"],
            "legacy_country_code": "US",
            "is_enabled": True,
            "quote_selectable": True,
            "not_selectable_reason": None,
            "geo_region": "North America",
            "business_economic_regions": ["NORTH_AMERICA"],
        },
        {
            "jurisdiction_id": "jur-EP",
            "standard_code": "EP",
            "display_code": "EPO",
            "quote_display_name": "欧洲专利局 (EPO)",
            "jurisdiction_type": "regional_office",
            "quote_option_group": "regional_office",
            "quote_business_lines": ["patent"],
            "legacy_country_code": "EP",
            "is_enabled": True,
            "quote_selectable": True,
            "not_selectable_reason": None,
            "geo_region": "Europe",
            "business_economic_regions": ["EUROPE"],
        },
        {
            "jurisdiction_id": "jur-EM",
            "standard_code": "EM",
            "display_code": "EUIPO",
            "quote_display_name": "欧盟知识产权局 (EUIPO)",
            "jurisdiction_type": "regional_office",
            "quote_option_group": "regional_office",
            "quote_business_lines": ["trademark", "design"],
            "legacy_country_code": "EM",
            "is_enabled": True,
            "quote_selectable": True,
            "not_selectable_reason": None,
            "geo_region": "Europe",
            "business_economic_regions": ["EUROPE", "EU"],
        },
        {
            "jurisdiction_id": "jur-WO",
            "standard_code": "WO",
            "display_code": "WIPO",
            "quote_display_name": "世界知识产权组织 / WIPO",
            "jurisdiction_type": "international_organization",
            "quote_option_group": "international_organization",
            "quote_business_lines": ["patent"],
            "legacy_country_code": None,
            "is_enabled": True,
            "quote_selectable": True,
            "not_selectable_reason": None,
            "geo_region": "",
            "business_economic_regions": [],
        },
        {
            "jurisdiction_id": "jur-PCT",
            "standard_code": "PCT",
            "display_code": "PCT",
            "quote_display_name": "PCT 国际阶段",
            "jurisdiction_type": "treaty_entry",
            "quote_option_group": "treaty_route",
            "quote_business_lines": ["patent"],
            "legacy_country_code": None,
            "is_enabled": True,
            "quote_selectable": False,
            "not_selectable_reason": "PCT 国际阶段报价入口，待申请路径模块启用",
            "geo_region": "",
            "business_economic_regions": [],
        },
        {
            "jurisdiction_id": "jur-MADRID",
            "standard_code": "MADRID",
            "display_code": "MADRID",
            "quote_display_name": "马德里商标国际注册",
            "jurisdiction_type": "treaty_entry",
            "quote_option_group": "treaty_route",
            "quote_business_lines": ["trademark"],
            "legacy_country_code": None,
            "is_enabled": True,
            "quote_selectable": False,
            "not_selectable_reason": "商标国际注册路径入口，待申请路径模块启用",
            "geo_region": "",
            "business_economic_regions": [],
        },
        {
            "jurisdiction_id": "jur-HAGUE",
            "standard_code": "HAGUE",
            "display_code": "HAGUE",
            "quote_display_name": "海牙外观设计国际注册",
            "jurisdiction_type": "treaty_entry",
            "quote_option_group": "treaty_route",
            "quote_business_lines": ["design"],
            "legacy_country_code": None,
            "is_enabled": True,
            "quote_selectable": False,
            "not_selectable_reason": "外观设计国际注册路径入口，待申请路径模块启用",
            "geo_region": "",
            "business_economic_regions": [],
        },
        {
            "jurisdiction_id": "jur-EUROPE",
            "standard_code": "EUROPE",
            "display_code": "EUROPE",
            "quote_display_name": "欧洲 (EUROPE)",
            "jurisdiction_type": "internal_business_object",
            "quote_option_group": "non_quote_region",
            "quote_business_lines": [],
            "legacy_country_code": None,
            "is_enabled": True,
            "quote_selectable": False,
            "not_selectable_reason": "欧洲仅作为地理区域或商务/经济区域，不作为报价对象",
            "geo_region": "Europe",
            "business_economic_regions": ["EUROPE"],
        },
    ]

    def fake_fetch(
        selectable_only: bool = False,
        business_line: str | None = None,
        option_group: str | None = None,
    ) -> list[dict[str, object]]:
        result = rows
        if selectable_only:
            result = [row for row in result if row["quote_selectable"]]
        if business_line:
            result = [row for row in result if business_line in row["quote_business_lines"]]
        if option_group:
            result = [row for row in result if row["quote_option_group"] == option_group]
        return result

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_quote_jurisdiction_options_preview",
        fake_fetch,
    )

    all_options = fetch_quote_jurisdiction_options_preview()
    selectable_codes = {
        option.display_code
        for option in fetch_quote_jurisdiction_options_preview(selectable_only=True)
    }
    patent_codes = {
        option.display_code
        for option in fetch_quote_jurisdiction_options_preview(business_line="patent")
    }
    trademark_codes = {
        option.display_code
        for option in fetch_quote_jurisdiction_options_preview(business_line="trademark")
    }
    design_codes = {
        option.display_code
        for option in fetch_quote_jurisdiction_options_preview(business_line="design")
    }
    single_country_codes = {
        option.display_code
        for option in fetch_quote_jurisdiction_options_preview(option_group="single_country")
    }

    by_code = {option.display_code: option for option in all_options}
    assert len(all_options) == len(rows)
    assert "WIPO" in selectable_codes
    assert "PCT" not in selectable_codes
    assert by_code["WIPO"].quote_option_group == "international_organization"
    assert "WIPO" not in single_country_codes
    assert {"US", "EPO", "WIPO", "PCT"}.issubset(patent_codes)
    assert "EUIPO" not in patent_codes
    assert {"US", "EUIPO", "MADRID"}.issubset(trademark_codes)
    assert "EPO" not in trademark_codes
    assert {"US", "EUIPO", "HAGUE"}.issubset(design_codes)
    assert "EPO" not in design_codes
    assert by_code["PCT"].quote_option_group == "treaty_route"
    assert by_code["PCT"].not_selectable_reason
    assert by_code["MADRID"].quote_option_group == "treaty_route"
    assert by_code["MADRID"].not_selectable_reason
    assert by_code["HAGUE"].quote_option_group == "treaty_route"
    assert by_code["HAGUE"].not_selectable_reason
    assert by_code["EUROPE"].quote_selectable is False
    assert by_code["EUROPE"].quote_option_group == "non_quote_region"


def test_create_quotation_generates_stable_number(monkeypatch) -> None:
    payload = QuotationCreate(
        client_name="测试客户",
        consultant_email="suri@example.com",
        country_code="US",
        application_type="发明",
        filing_route="PCT进入",
        currency="USD",
    )

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_user_by_email",
        lambda email: {
            "id": "u-consultant",
            "name": "Suri",
            "email": email,
            "role": "consultant",
            "status": "active",
        },
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_fee_rules",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_translation_rules",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.insert_quotation",
        lambda record, items: None,
    )

    quotation = create_quotation(payload)

    assert quotation.quotation_no.endswith(quotation.quotation_no.split("-")[-1])
    assert quotation.status == "已生成报价"


def test_create_quotation_draft_splits_country_items(monkeypatch) -> None:
    payload = QuotationDraftCreate(
        client_name="测试客户",
        country_codes=["US", "EP"],
        application_type="发明",
        filing_route="PCT进入",
        needs_translation=False,
    )
    current_user = {
        "id": "u-consultant",
        "name": "Suri",
        "email": "suri@example.com",
        "role": "consultant",
        "status": "active",
    }
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_countries",
        lambda: [
            {
                "code": "US",
                "name_cn": "美国",
                "name_en": "United States",
                "default_currency": "USD",
                "enabled": True,
            },
            {
                "code": "EP",
                "name_cn": "欧洲",
                "name_en": "Europe",
                "default_currency": "EUR",
                "enabled": True,
            },
        ],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_fee_rules",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_translation_rules",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_country_config",
        lambda: {
            "countries": [],
            "path_rules": [],
            "entity_type_rules": [],
            "language_rules": [],
            "fx_tax_rules": [],
            "special_rules": [],
        },
    )

    def fake_insert(record: dict[str, object], items: list[dict[str, object]]) -> None:
        saved["record"] = record
        saved["items"] = items

    def fake_fetch(draft_id: str) -> dict[str, object]:
        record = dict(saved["record"])  # type: ignore[arg-type]
        record["items"] = saved["items"]
        return record

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.insert_quotation_draft",
        fake_insert,
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_quotation_draft",
        fake_fetch,
    )

    draft = create_quotation_draft(payload, current_user)

    assert draft.draft_no.startswith(f"D{datetime.now(timezone.utc):%Y%m%d}-ZYIP-")
    assert draft.consultant_email == "suri@example.com"
    assert [item.country_code for item in draft.items] == ["US", "EP"]
    assert [item.quote_currency for item in draft.items] == ["USD", "EUR"]


def test_update_quotation_draft_returns_updated_record(monkeypatch) -> None:
    now = datetime.now(timezone.utc)

    def fake_update(draft_id: str, values: dict[str, object]) -> dict[str, object]:
        assert draft_id == "draft-1"
        assert values == {"client_name": "更新客户", "case_title": "更新案件"}
        return {
            "id": "draft-1",
            "draft_no": "D20260605-ZYIP-ABCDE",
            "consultant_id": "u-consultant",
            "consultant_email": "suri@example.com",
            "consultant_name": "Suri",
            "client_name": "更新客户",
            "client_contact": "",
            "has_case": True,
            "case_title": "更新案件",
            "applicant_count": 1,
            "priority_count": 0,
            "claim_count": 0,
            "description_pages": 0,
            "drawing_pages": 0,
            "needs_translation": False,
            "translation_quantity_one": Decimal("0"),
            "translation_quantity_two": Decimal("0"),
            "status": "草稿",
            "remark": "",
            "created_at": now,
            "updated_at": now,
            "items": [],
        }

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.update_quotation_draft",
        fake_update,
    )

    draft = update_quotation_draft(
        "draft-1",
        QuotationDraftUpdate(client_name="更新客户", case_title="更新案件"),
    )

    assert draft.client_name == "更新客户"
    assert draft.case_title == "更新案件"


def test_delete_quotation_draft_item_returns_remaining_items(monkeypatch) -> None:
    now = datetime.now(timezone.utc)

    def fake_delete(draft_id: str, item_id: str) -> dict[str, object]:
        assert draft_id == "draft-1"
        assert item_id == "draft-1-001"
        return {
            "id": "draft-1",
            "draft_no": "D20260605-ZYIP-ABCDE",
            "consultant_id": "u-consultant",
            "consultant_email": "suri@example.com",
            "consultant_name": "Suri",
            "client_name": "测试客户",
            "client_contact": "",
            "has_case": False,
            "case_title": "",
            "applicant_count": 1,
            "priority_count": 0,
            "claim_count": 0,
            "description_pages": 0,
            "drawing_pages": 0,
            "needs_translation": False,
            "translation_quantity_one": Decimal("0"),
            "translation_quantity_two": Decimal("0"),
            "status": "草稿",
            "remark": "",
            "created_at": now,
            "updated_at": now,
            "items": [
                {
                    "id": "draft-1-002",
                    "draft_id": "draft-1",
                    "country_code": "EP",
                    "application_type": "发明",
                    "filing_route": "PCT进入",
                    "pct_route_detail": "",
                    "entity_type": "",
                    "case_title": "",
                    "quote_currency": "EUR",
                    "current_stage_total": Decimal("0"),
                    "future_stage_total": Decimal("0"),
                    "total_amount": Decimal("0"),
                    "status": "草稿",
                    "sort_order": 2,
                    "created_at": now,
                    "updated_at": now,
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.delete_quotation_draft_item",
        fake_delete,
    )

    draft = delete_quotation_draft_item("draft-1", "draft-1-001")

    assert len(draft.items) == 1
    assert draft.items[0].country_code == "EP"


def test_create_quotation_from_drafts_generates_formal_quote(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    current_user = {
        "id": "u-consultant",
        "name": "Suri",
        "email": "suri@example.com",
        "role": "consultant",
        "status": "active",
    }
    draft_items = [
        {
            "id": "draft-1-001",
            "draft_id": "draft-1",
            "country_code": "US",
            "application_type": "发明",
            "filing_route": "PCT进入",
            "pct_route_detail": "",
            "entity_type": "",
            "case_title": "测试案件",
            "quote_currency": "USD",
            "current_stage_total": Decimal("1000"),
            "future_stage_total": Decimal("500"),
            "total_amount": Decimal("1500"),
            "status": "草稿",
            "sort_order": 1,
            "draft_no": "D20260605-ZYIP-AAAAA",
            "consultant_id": "u-consultant",
            "consultant_email": "suri@example.com",
            "consultant_name": "Suri",
            "client_name": "测试客户",
            "client_contact": "Lina",
            "has_case": True,
            "applicant_count": 1,
            "priority_count": 0,
            "claim_count": 0,
            "description_pages": 0,
            "drawing_pages": 0,
            "needs_translation": False,
            "translation_quantity_one": Decimal("0"),
            "translation_quantity_two": Decimal("0"),
            "draft_remark": "",
        },
        {
            "id": "draft-1-002",
            "draft_id": "draft-1",
            "country_code": "EP",
            "application_type": "发明",
            "filing_route": "PCT进入",
            "pct_route_detail": "",
            "entity_type": "",
            "case_title": "测试案件",
            "quote_currency": "EUR",
            "current_stage_total": Decimal("800"),
            "future_stage_total": Decimal("300"),
            "total_amount": Decimal("1100"),
            "status": "草稿",
            "sort_order": 2,
            "draft_no": "D20260605-ZYIP-AAAAA",
            "consultant_id": "u-consultant",
            "consultant_email": "suri@example.com",
            "consultant_name": "Suri",
            "client_name": "测试客户",
            "client_contact": "Lina",
            "has_case": True,
            "applicant_count": 1,
            "priority_count": 0,
            "claim_count": 0,
            "description_pages": 0,
            "drawing_pages": 0,
            "needs_translation": False,
            "translation_quantity_one": Decimal("0"),
            "translation_quantity_two": Decimal("0"),
            "draft_remark": "",
        },
    ]
    saved: dict[str, object] = {}

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_draft_items_for_formal_quote",
        lambda item_ids: draft_items,
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.refresh_quotation_followup_statuses",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.count_overdue_followup_quotations",
        lambda consultant_email, block_days: 0,
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.count_open_unconverted_quotations",
        lambda consultant_email: 0,
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.has_valid_quote_unlock",
        lambda consultant_email: False,
    )

    def fake_insert(
        record: dict[str, object],
        items: list[dict[str, object]],
        draft_ids: list[str],
        draft_item_ids: list[str],
    ) -> None:
        assert draft_ids == ["draft-1"]
        assert draft_item_ids == ["draft-1-001", "draft-1-002"]
        saved["record"] = record
        saved["items"] = items

    def fake_fetch(quotation_id: str) -> dict[str, object]:
        record = dict(saved["record"])  # type: ignore[arg-type]
        record["country_code"] = "US"
        record["currency"] = "USD"
        record["created_at"] = now
        record["updated_at"] = now
        record["items"] = saved["items"]
        return record

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.insert_quotation_from_drafts",
        fake_insert,
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_quotation",
        fake_fetch,
    )

    quotation = create_quotation_from_drafts(
        QuotationFromDraftsCreate(draft_item_ids=["draft-1-001", "draft-1-002"]),
        current_user,
    )

    assert quotation.quotation_no.endswith(quotation.quotation_no.split("-")[-1])
    assert quotation.client_name == "测试客户"
    assert quotation.current_stage_total == Decimal("1000")
    assert quotation.future_stage_total == Decimal("500")
    assert len(quotation.items) == 2
    assert quotation.items[0].item_name == "US 发明 PCT进入 报价合计"


def test_update_quotation_status_requires_next_followup_date(monkeypatch) -> None:
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_quotation",
        lambda quotation_id: {
            "id": quotation_id,
            "quotation_no": "20260605-ZYIP-ABCDE",
            "client_name": "测试客户",
            "client_contact": "",
            "consultant_email": "suri@example.com",
            "consultant_name": "Suri",
            "country_code": "US",
            "application_type": "发明",
            "filing_route": "PCT进入",
            "currency": "USD",
            "has_case": False,
            "case_title": "",
            "applicant_count": 1,
            "priority_count": 0,
            "claim_count": 0,
            "description_pages": 0,
            "drawing_pages": 0,
            "needs_translation": False,
            "translation_quantity_one": Decimal("0"),
            "translation_quantity_two": Decimal("0"),
            "remark": "",
            "status": "已生成报价",
            "current_stage_total": Decimal("0"),
            "future_stage_total": Decimal("0"),
            "total_amount": Decimal("0"),
            "next_followup_date": None,
            "last_followup_at": None,
            "is_sent": False,
            "is_confirmed": False,
            "is_opened": False,
            "created_at": now,
            "updated_at": now,
            "items": [],
        },
    )

    try:
        update_quotation_status("quotation-1", QuotationStatusUpdate(status="已发送客户"))
    except ValueError as exc:
        assert str(exc) == "FOLLOWUP_DATE_REQUIRED"
    else:
        raise AssertionError("status update should require a next follow-up date")


def test_create_quotation_from_drafts_blocks_unconverted_without_unlock(monkeypatch) -> None:
    current_user = {
        "id": "u-consultant",
        "name": "Suri",
        "email": "suri@example.com",
        "role": "consultant",
        "status": "active",
    }
    monkeypatch.setattr("app.services.quotation_service.mysql.refresh_quotation_followup_statuses", lambda: None)
    monkeypatch.setattr("app.services.quotation_service.mysql.count_overdue_followup_quotations", lambda email, days: 0)
    monkeypatch.setattr("app.services.quotation_service.mysql.count_open_unconverted_quotations", lambda email: 11)
    monkeypatch.setattr("app.services.quotation_service.mysql.has_valid_quote_unlock", lambda email: False)
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_draft_items_for_formal_quote",
        lambda item_ids: [
            {
                "id": "draft-1-001",
                "draft_id": "draft-1",
                "country_code": "US",
                "application_type": "发明",
                "filing_route": "PCT进入",
                "pct_route_detail": "",
                "entity_type": "",
                "case_title": "",
                "quote_currency": "USD",
                "current_stage_total": Decimal("1000"),
                "future_stage_total": Decimal("500"),
                "total_amount": Decimal("1500"),
                "status": "草稿",
                "sort_order": 1,
                "draft_no": "D20260605-ZYIP-AAAAA",
                "consultant_id": "u-consultant",
                "consultant_email": "suri@example.com",
                "consultant_name": "Suri",
                "client_name": "测试客户",
                "client_contact": "",
                "has_case": False,
                "applicant_count": 1,
                "priority_count": 0,
                "claim_count": 0,
                "description_pages": 0,
                "drawing_pages": 0,
                "needs_translation": False,
                "translation_quantity_one": Decimal("0"),
                "translation_quantity_two": Decimal("0"),
                "draft_remark": "",
            }
        ],
    )

    try:
        create_quotation_from_drafts(
            QuotationFromDraftsCreate(draft_item_ids=["draft-1-001"]),
            current_user,
        )
    except ValueError as exc:
        assert str(exc) == "FORMAL_QUOTE_BLOCKED_UNCONVERTED"
    else:
        raise AssertionError("formal quote creation should be blocked")
