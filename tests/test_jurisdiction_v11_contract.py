from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "quote_system_backend"
DOCS_ROOT = REPO_ROOT / "docs"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v11_contract_documents_cover_required_p0_items() -> None:
    plan = _read(DOCS_ROOT / "jurisdiction-master-v1.1-compatibility-patch-plan.md")
    contract = _read(DOCS_ROOT / "jurisdiction-master-v1.1-cross-module-contract.md")
    combined = plan + "\n" + contract

    required_terms = [
        "jurisdiction_id",
        "country_jurisdiction_map",
        "country_code",
        "EP",
        "EPO",
        "EPC",
        "EUIPO",
        "UPC_UP",
        "ip_system_master",
        "entry_route",
        "is_deleted",
        "is_enabled",
        "已验收",
        "不要求当前一期报价工作台立即切换",
        "不要求迁移历史报价",
    ]

    for term in required_terms:
        assert term in combined


def test_acceptance_check_sql_is_read_only_select_only() -> None:
    sql = _read(BACKEND_ROOT / "jurisdiction_v11_acceptance_check.sql")

    forbidden_keywords = ["CREATE", "ALTER", "UPDATE", "DELETE", "INSERT", "DROP", "TRUNCATE"]
    for keyword in forbidden_keywords:
        assert re.search(rf"\b{keyword}\b", sql, flags=re.IGNORECASE) is None

    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    assert statements
    assert all(statement.upper().startswith("SELECT") for statement in statements)


def test_acceptance_check_sql_covers_stable_ids_and_legacy_mapping() -> None:
    sql = _read(BACKEND_ROOT / "jurisdiction_v11_acceptance_check.sql")

    for code in ("US", "JP", "KR", "EP"):
        assert f"'{code}'" in sql
    assert "COALESCE(c.jurisdiction_id, m.jurisdiction_id)" in sql
    assert "country_jurisdiction_map" in sql
    assert "legacy_country_code_mapping_missing" in sql


def test_acceptance_check_sql_does_not_force_legacy_mapping_for_non_country_objects() -> None:
    sql = _read(BACKEND_ROOT / "jurisdiction_v11_acceptance_check.sql")

    for code in ("WO", "PCT", "HAGUE", "MADRID", "WIPO"):
        assert f"'{code}'" in sql
    assert "non_country_objects_without_legacy_mapping_expected" in sql


def test_forbidden_regional_system_codes_are_not_entry_routes_in_seed_sql() -> None:
    quote_engine_seed = _read(BACKEND_ROOT / "phase_1_quote_engine_config.sql")
    acceptance_sql = _read(BACKEND_ROOT / "jurisdiction_v11_acceptance_check.sql")

    forbidden_route_codes = ("EPC", "EPO", "EUIPO", "UPC_UP", "UPC", "UP")
    for code in forbidden_route_codes:
        pattern = rf"filing_route[^,\n]*['\"]{re.escape(code)}['\"]"
        assert re.search(pattern, quote_engine_seed, flags=re.IGNORECASE) is None

    assert "forbidden_entry_route_codes" in acceptance_sql


def test_v11_acceptance_sql_checks_disabled_or_deleted_advisor_current_relations() -> None:
    sql = _read(BACKEND_ROOT / "jurisdiction_v11_acceptance_check.sql")

    assert "advisor_current_relation_with_disabled_or_deleted_jurisdiction" in sql
    assert "r.publish_status = 'published'" in sql
    assert "r.is_active = 1" in sql
    assert "j.is_enabled = 0" in sql
    assert "COALESCE(j.is_deleted, 0) = 1" in sql


def test_ip_system_current_reader_filters_disabled_or_deleted_jurisdictions() -> None:
    service = _read(BACKEND_ROOT / "app" / "services" / "ip_system_service.py")

    fetch_relations = service.split("def _fetch_relations(", 1)[1].split(
        "def _publish_review_with_cursor", 1
    )[0]

    assert "j.is_enabled = 1" in fetch_relations
    assert "is_deleted" in fetch_relations


def test_reference_registry_migration_is_candidate_pool_not_second_master() -> None:
    sql = _read(BACKEND_ROOT / "phase_9_jurisdiction_v11b_reference_registry.sql")

    assert "CREATE TABLE IF NOT EXISTS jurisdiction_reference_registry" in sql
    assert "jurisdiction_id VARCHAR(64) NULL" in sql
    assert "FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id)" in sql
    assert "quote_selectable_default" in sql
    assert "not_selectable_reason" in sql
    assert "linked_formal_master" in sql
    assert "JOIN jurisdictions j" in sql
    assert "candidate_status = 'candidate'" in sql
    assert "UPPER(internal_code) IN ('HK', 'MO', 'TW')" in sql
    assert "country_type = '特殊地区'" in sql


def test_belt_and_road_tag_source_is_pending_review_without_bulk_mapping() -> None:
    sql = _read(BACKEND_ROOT / "phase_9_jurisdiction_v11b_reference_registry.sql")

    assert "BELT_AND_ROAD_SOURCE" in sql
    assert "一带一路仅作为商务/市场标签机制预留" in sql
    assert "'pending_review'" in sql
    assert re.search(r"INSERT\s+INTO\s+jurisdiction_region_tag_map", sql, flags=re.IGNORECASE) is None


def test_reference_registry_defaults_keep_regions_and_reserved_boundaries() -> None:
    from app.db import mysql
    from app.reference.jurisdiction_registry import default_registry_items

    by_code = {item.standard_code.upper(): item for item in default_registry_items()}
    for code in ("HK", "MO", "TW"):
        assert by_code[code].jurisdiction_type == "special_region"
        assert by_code[code].reference_category == "region"

    visible_codes = {row["standard_code"] for row in mysql._fallback_reference_registry("", include_hidden=False)}  # noqa: SLF001
    assert "MADRID" not in visible_codes
    assert "NICE" not in visible_codes
    assert by_code["MADRID"].visibility_scope == "reserved_hidden"
    assert by_code["MADRID"].business_scope == ("trademark",)

    assert by_code["HAGUE"].business_scope == ("design",)
    assert by_code["HAGUE"].candidate_status == "reserved"
    assert by_code["HAGUE"].quote_selectable_default is False


def test_frontend_reference_entry_uses_api_and_default_visible_candidates() -> None:
    frontend_page = _read(REPO_ROOT / "quote_system_frontend" / "app" / "page.tsx")
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")

    assert "/jurisdiction-references" in frontend_page
    assert "include_hidden=true" not in frontend_page
    assert "isVisibleReferenceCandidate" in admin
    assert "app/reference/jurisdictions" not in frontend_page


def test_source_management_frontend_exposes_required_edit_fields() -> None:
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")
    page = _read(REPO_ROOT / "quote_system_frontend" / "app" / "page.tsx")

    for term in (
        "source_name",
        "source_url",
        "source_note",
        "source_version",
        "review_status",
        "last_reviewed_at",
        "next_review_due_at",
        "dataSourceToForm",
    ):
        assert term in admin
    assert 'method: existing ? "PATCH" : "POST"' in page


def test_reference_create_restore_logic_does_not_treat_unquoted_as_deleted() -> None:
    service = _read(BACKEND_ROOT / "app" / "services" / "quotation_service.py")
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")

    assert "enabled = bool(payload.enabled)" in service
    assert 'enabled=True,\n                    business_region=list(reference.default_business_economic_regions)' in service
    assert '"is_enabled": True' in service
    assert 'enabled: true' in admin
    assert 'is_enabled: true' in admin
    assert 'referenceStatusLabel(status: ReferenceExistenceStatus)' in admin
    assert '已删除，可恢复' in admin
