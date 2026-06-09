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
