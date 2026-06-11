from __future__ import annotations

import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = WORKSPACE_ROOT / "frontend"
MIGRATIONS_ROOT = BACKEND_ROOT / "migrations"
DOCS_ROOT = WORKSPACE_ROOT / "docs"


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
    sql = _read(MIGRATIONS_ROOT / "jurisdiction_v11_acceptance_check.sql")

    forbidden_keywords = ["CREATE", "ALTER", "UPDATE", "DELETE", "INSERT", "DROP", "TRUNCATE"]
    for keyword in forbidden_keywords:
        assert re.search(rf"\b{keyword}\b", sql, flags=re.IGNORECASE) is None

    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    assert statements
    assert all(statement.upper().startswith("SELECT") for statement in statements)


def test_acceptance_check_sql_covers_stable_ids_and_legacy_mapping() -> None:
    sql = _read(MIGRATIONS_ROOT / "jurisdiction_v11_acceptance_check.sql")

    for code in ("US", "JP", "KR", "EP"):
        assert f"'{code}'" in sql
    assert "COALESCE(c.jurisdiction_id, m.jurisdiction_id)" in sql
    assert "country_jurisdiction_map" in sql
    assert "legacy_country_code_mapping_missing" in sql


def test_acceptance_check_sql_does_not_force_legacy_mapping_for_non_country_objects() -> None:
    sql = _read(MIGRATIONS_ROOT / "jurisdiction_v11_acceptance_check.sql")

    for code in ("WO", "PCT", "HAGUE", "MADRID", "WIPO"):
        assert f"'{code}'" in sql
    assert "non_country_objects_without_legacy_mapping_expected" in sql


def test_forbidden_regional_system_codes_are_not_entry_routes_in_seed_sql() -> None:
    quote_engine_seed = _read(MIGRATIONS_ROOT / "phase_1_quote_engine_config.sql")
    acceptance_sql = _read(MIGRATIONS_ROOT / "jurisdiction_v11_acceptance_check.sql")

    forbidden_route_codes = ("EPC", "EPO", "EUIPO", "UPC_UP", "UPC", "UP")
    for code in forbidden_route_codes:
        pattern = rf"filing_route[^,\n]*['\"]{re.escape(code)}['\"]"
        assert re.search(pattern, quote_engine_seed, flags=re.IGNORECASE) is None

    assert "forbidden_entry_route_codes" in acceptance_sql


def test_v11_acceptance_sql_checks_disabled_or_deleted_advisor_current_relations() -> None:
    sql = _read(MIGRATIONS_ROOT / "jurisdiction_v11_acceptance_check.sql")

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
    sql = _read(MIGRATIONS_ROOT / "phase_9_jurisdiction_v11b_reference_registry.sql")

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
    sql = _read(MIGRATIONS_ROOT / "phase_9_jurisdiction_v11b_reference_registry.sql")

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
    frontend_page = _read(FRONTEND_ROOT / "app" / "page.tsx")
    admin = _read(FRONTEND_ROOT / "app" / "components" / "admin.tsx")

    assert "/jurisdiction-references" in frontend_page
    assert "include_hidden=true" not in frontend_page
    assert "isVisibleReferenceCandidate" in admin
    assert "app/reference/jurisdictions" not in frontend_page


def test_source_management_frontend_exposes_required_edit_fields() -> None:
    admin = _read(FRONTEND_ROOT / "app" / "components" / "admin.tsx")
    page = _read(FRONTEND_ROOT / "app" / "page.tsx")

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
    admin = _read(FRONTEND_ROOT / "app" / "components" / "admin.tsx")

    assert 'enabled = reference.candidate_status == "active" and reference.quote_selectable_default and bool(payload.enabled)' in service
    assert "enabled_from_reference = reference.candidate_status == \"active\" and reference.quote_selectable_default" in service
    assert '"business_region": _reference_default_business_tags(reference)' in service
    assert '"remarks": ""' in service
    assert '"is_enabled": enabled_from_reference' in service
    assert 'const enabledFromReference = reference.candidate_status === "active" && reference.quote_selectable_default' in admin
    assert 'business_region: []' in admin
    assert 'is_enabled: enabledFromReference' in admin
    assert 'referenceStatusLabel(status: ReferenceExistenceStatus)' in admin
    assert '已删除，可恢复' in admin


def test_v11b_withdrawn_acceptance_report_is_marked_superseded() -> None:
    report = _read(DOCS_ROOT / "jurisdiction-master-v1.1-b-reference-registry-acceptance-report.md")

    assert "撤回 / 验收未通过 / superseded" in report
    assert "不作为 V1.1-B 正式验收依据" in report
    assert "人工验收发现" in report


def test_v11b_refinement_migration_covers_geo_office_and_source_scope() -> None:
    sql = _read(BACKEND_ROOT / "phase_10_jurisdiction_v11b_master_page_refinement.sql")
    rollback = _read(BACKEND_ROOT / "phase_10_jurisdiction_v11b_master_page_refinement_rollback.sql")

    assert "default_office_jurisdiction_id" in sql
    assert "default_office_code" in sql
    assert "nullable logical link" in sql
    assert "normalized into an enforced FK" in sql
    assert "WIPO_IP_OFFICES_DIRECTORY" in sql
    assert "UN_M49" in sql
    assert "BUSINESS_REGION_SOURCE" in sql
    assert "https://www.wipo.int/en/web/country-profiles/directory-ip-offices" in sql
    assert "Latin America and the Caribbean" in sql
    assert "Switzerland standard_code=CH uses WIPO ST.3" in sql
    assert "wipo_st3_code = 'CO'" in sql
    assert "CALL drop_column_if_exists('jurisdictions', 'default_office_code')" in rollback
    assert "source_id IN ('WIPO_IP_OFFICES_DIRECTORY', 'UN_M49', 'BUSINESS_REGION_SOURCE')" in rollback


def test_business_tags_can_be_empty_and_other_is_not_forced() -> None:
    from app.schemas.quotation import Country, CountryCreate

    country = Country.model_validate({
        "code": "CO",
        "name_cn": "哥伦比亚",
        "name_en": "Colombia",
        "default_currency": "USD",
        "enabled": True,
        "business_region": [],
    })
    mixed = Country.model_validate({
        "code": "CO",
        "name_cn": "哥伦比亚",
        "name_en": "Colombia",
        "default_currency": "USD",
        "enabled": True,
        "business_region": ["OTHER", "LATIN_AMERICA"],
    })
    create = CountryCreate.model_validate({
        "reference_id": "ref-co",
        "source_verified": True,
        "business_region": [],
    })

    assert country.business_region == []
    assert mixed.business_region == ["LATIN_AMERICA"]
    assert create.business_region == []


def test_country_master_reference_search_contract_and_deletion_boundaries() -> None:
    service = _read(BACKEND_ROOT / "app" / "services" / "quotation_service.py")
    mysql = _read(BACKEND_ROOT / "app" / "db" / "mysql.py")
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")
    options = _read(REPO_ROOT / "quote_system_frontend" / "app" / "options.ts")

    assert "REFERENCE_DEFAULT_HIDDEN_CODES = {\"EU\", \"IB\", \"PCT\", \"HAGUE\", \"MADRID\", \"NICE\"}" in service
    assert '"IB": "WO"' in service
    assert '"EUIPO": "EM"' in service
    assert '"EPO": "EP"' in service
    assert "reference.reference_category == \"treaty_route\"" in service
    assert "business_tables = {" in mysql
    business_table_block = mysql.split("business_tables = {", 1)[1].split("}", 1)[0]
    for table_name in ("fee_rules", "country_path_rules", "quotations", "quotation_items", "jurisdiction_ip_system_relation"):
        assert table_name in business_table_block
    assert "jurisdiction_reference_registry" not in business_table_block
    assert "该对象已有正式业务数据引用，请改为停用" in mysql
    assert "jurisdiction_reference_registry" not in mysql.split("business_tables = {", 1)[1].split("}", 1)[0]
    assert "publish_status = 'published'" in mysql
    soft_delete_block = mysql.split("def soft_delete_country_config(", 1)[1].split("def update_country_path_rule", 1)[0]
    assert 'country_updates["is_deleted"] = True' in soft_delete_block
    assert 'country_updates["deleted_at"] = now' in soft_delete_block
    assert 'jurisdiction_updates["is_deleted"] = True' in soft_delete_block
    assert 'jurisdiction_updates["deleted_at"] = now' in soft_delete_block
    assert "_resolve_country_code_for_delete" in mysql
    assert "UPDATE countries SET" in soft_delete_block
    assert "UPDATE jurisdictions SET" in soft_delete_block
    assert "单一国家/地区" in options
    assert "SOUTH_AMERICA" not in options
    assert '"region-sources"' not in _read(REPO_ROOT / "quote_system_frontend" / "app" / "types.ts")
    assert "确认本批次字段来源核验" in admin
    assert "未配置" in admin
    assert "其他 / 待确认" not in admin
    assert 'label: "其他", value: "Other"' in options
    assert "pending_review" not in options
    assert "default_office_code" in admin
    assert "确认当前字段来源核验" in admin
    assert "未确认来源核验也可新增" in admin
    assert "source_verified: countryForm.source_verified" in admin
    assert "字段值为空、字段值为未配置、来源 URL 缺失或 review_status=deprecated" in admin
    page = _read(REPO_ROOT / "quote_system_frontend" / "app" / "page.tsx")
    delete_frontend_block = page.split("async function deleteCountryConfigRow(", 1)[1].split("async function restoreCountryConfigRow", 1)[0]
    assert "fetch(`${apiBase}/countries/${country.code}`" in delete_frontend_block
    assert 'method: "DELETE"' in delete_frontend_block
    assert "JSON.stringify({ delete_reason: deleteReason })" in delete_frontend_block
    assert "country-config?include_deleted=true" in delete_frontend_block
    assert "setCountryConfig((await refreshed.json()) as CountryConfig)" in delete_frontend_block
    assert "country-config?include_deleted=true" in page
    assert "国家/地区/受理局删除失败。" not in page


def test_colombia_uses_wipo_st3_code_and_un_m49_geo_region() -> None:
    from app.reference.jurisdiction_registry import default_registry_items
    from app.reference.jurisdictions import JURISDICTION_REFERENCES

    static_by_code = {item.standard_code.upper(): item for item in JURISDICTION_REFERENCES}
    registry_by_code = {item.standard_code.upper(): item for item in default_registry_items()}

    colombia = static_by_code["CO"]
    registry_colombia = registry_by_code["CO"]

    assert colombia.display_code == "CO"
    assert colombia.source_name == "WIPO ST.3 / UN M49"
    assert colombia.geo_region == "Latin America and the Caribbean"
    assert colombia.default_business_economic_regions == ("LATIN_AMERICA",)
    assert "WIPO Lex" not in colombia.source_note

    assert registry_colombia.geo_region == "Latin America and the Caribbean"
    assert registry_colombia.default_business_economic_regions == ("LATIN_AMERICA",)
    assert registry_colombia.source_id == "WIPO_ST3"


def test_field_level_sources_geo_and_office_defaults_do_not_use_wipo_lex() -> None:
    from app.db import mysql
    from app.reference.jurisdiction_registry import default_registry_items
    from app.services import quotation_service

    registry_by_code = {item.standard_code.upper(): item for item in default_registry_items()}
    switzerland = registry_by_code["CH"]
    colombia = registry_by_code["CO"]

    assert switzerland.geo_region == "Europe"
    assert switzerland.default_business_economic_regions == ()
    assert colombia.geo_region == "Latin America and the Caribbean"
    assert colombia.default_business_economic_regions == ("LATIN_AMERICA",)

    normalized_ch = mysql._reference_registry_row({  # noqa: SLF001
        "reference_id": "ref-ch",
        "standard_code": "CH",
        "display_code": "CH",
        "name_cn": "瑞士",
        "name_en": "Switzerland",
        "aliases_json": "[]",
        "business_scope_json": "[]",
        "default_business_economic_regions_json": "[\"OTHER\"]",
        "geo_region": "Other",
        "source_id": "WIPO_LEX_REFERENCE",
        "source_name": "WIPO Lex treaty reference baseline",
        "source_note": "",
    })
    assert normalized_ch["geo_region"] == "Europe"
    assert normalized_ch["default_business_economic_regions"] == []
    assert "international_region=UN_M49" in normalized_ch["source_note"]

    assert quotation_service._reference_default_business_tags(colombia) == ["LATIN_AMERICA"]  # noqa: SLF001
    assert quotation_service._reference_geo_region(switzerland) == "Europe"  # noqa: SLF001
    office = quotation_service._reference_default_office_fields(colombia)  # noqa: SLF001
    assert office["default_office_code"] == "SIC"
    assert office["default_office_code"] != "CO"
    assert "WIPO_IP_OFFICES_DIRECTORY" in office["default_office_source_note"]


def test_office_directory_registry_minimum_mapping_and_nl_default() -> None:
    from app.db import mysql
    from app.reference.jurisdiction_office_directory import default_office_directory_items
    from app.reference.ip_system_official_baseline import COUNTRY_NAMES
    from app.reference.jurisdiction_registry import default_registry_items
    from app.services import quotation_service

    directory_by_code = {item.country_code: item for item in default_office_directory_items()}
    assert set(COUNTRY_NAMES).issubset(directory_by_code)
    for code in ("CA", "NL", "CN", "US", "JP", "KR", "DE", "CO", "EP", "EM", "WO"):
        assert code in directory_by_code
        assert directory_by_code[code].office_name_en
        assert directory_by_code[code].source_id == "WIPO_IP_OFFICES_DIRECTORY"
        assert directory_by_code[code].office_type in {"national_ip_office", "regional_office", "international_office"}
        if code in COUNTRY_NAMES:
            assert directory_by_code[code].office_display_code != code

    nl = next(item for item in default_registry_items() if item.standard_code == "NL")
    assert quotation_service._reference_geo_region(nl) == "Europe"  # noqa: SLF001
    nl_office = quotation_service._reference_default_office_fields(nl)  # noqa: SLF001
    assert nl_office["default_office_name_en"] == "Netherlands Patent Office"
    assert nl_office["default_office_code"] == ""
    assert nl_office["default_office_type"] == "national_ip_office"

    normalized_nl = mysql._reference_registry_row({  # noqa: SLF001
        "reference_id": "ref-nl",
        "standard_code": "NL",
        "display_code": "NL",
        "name_cn": "荷兰",
        "name_en": "Netherlands",
        "aliases_json": "[]",
        "business_scope_json": "[]",
        "default_business_economic_regions_json": "[\"EUROPE\"]",
        "geo_region": "Europe",
        "source_id": "WIPO_ST3",
        "source_name": "WIPO ST.3",
        "source_note": "",
    })
    assert normalized_nl["default_office_name_en"] == "Netherlands Patent Office"
    assert normalized_nl["default_office_code"] == ""
    assert "WIPO_IP_OFFICES_DIRECTORY" in normalized_nl["default_office_source_note"]

    canada = next(item for item in default_registry_items() if item.standard_code == "CA")
    ca_office = quotation_service._reference_default_office_fields(canada)  # noqa: SLF001
    assert ca_office["default_office_name_en"] == "Canadian Intellectual Property Office"
    assert ca_office["default_office_type"] == "national_ip_office"


def test_v11b_field_source_matrix_and_full_un_m49_mapping() -> None:
    from app.reference.ip_system_official_baseline import COUNTRY_NAMES
    from app.reference.jurisdiction_field_sources import FIELD_SOURCE_IDS_BY_FIELD, UN_M49_REGION_BY_CODE
    from app.reference.jurisdiction_registry import default_registry_items

    assert FIELD_SOURCE_IDS_BY_FIELD["standard_code/display_code"] == "WIPO_ST3"
    assert FIELD_SOURCE_IDS_BY_FIELD["international_region"] == "UN_M49"
    assert FIELD_SOURCE_IDS_BY_FIELD["business_region"] == "BUSINESS_REGION_SOURCE"
    assert FIELD_SOURCE_IDS_BY_FIELD["default_office"] == "WIPO_IP_OFFICES_DIRECTORY"

    assert set(COUNTRY_NAMES).issubset(UN_M49_REGION_BY_CODE)
    by_code = {item.standard_code.upper(): item for item in default_registry_items()}
    expected_regions = {
        "CA": "North America",
        "CH": "Europe",
        "CO": "Latin America and the Caribbean",
        "NL": "Europe",
        "JP": "Asia",
        "KR": "Asia",
        "CN": "Asia",
        "AU": "Oceania",
        "NZ": "Oceania",
    }
    for code, region in expected_regions.items():
        assert by_code[code].geo_region == region
    assert by_code["CA"].default_business_economic_regions == ("NORTH_AMERICA", "APEC")
    assert by_code["NL"].default_business_economic_regions == ("EUROPE", "EU")
    assert all(by_code[code].geo_region != "Other" for code in COUNTRY_NAMES)


def test_frontend_field_source_table_excludes_candidate_source_and_summarizes_master_sources() -> None:
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")

    field_source_block = admin.split("function buildFieldSourceRows(", 1)[1].split("function fieldSourcesAreVerifiable", 1)[0]
    assert "WIPO_ST3" in field_source_block
    assert "UN_M49" in field_source_block
    assert "BUSINESS_REGION_SOURCE" in field_source_block
    assert "WIPO_IP_OFFICES_DIRECTORY" in field_source_block
    assert "WIPO_LEX_REFERENCE" not in field_source_block
    edit_block = admin.split("<summary className=\"cursor-pointer font-medium text-[oklch(34%_0.06_178)]\">导入轨迹</summary>", 1)[1].split("<div className=\"rounded-md border border-[oklch(80%_0.026_178)]", 1)[0]
    assert "WIPO Lex" in edit_block
    assert "该信息仅说明对象进入 reference 候选池的来源，不参与字段来源核验。" in edit_block
    assert "高级导入轨迹" not in admin
    assert "候选来源" not in admin
    assert "字段来源摘要" in admin
    assert "legacy_countries" not in admin.split("字段来源摘要", 1)[1]
    assert "WIPO Lex" not in admin.split("字段来源摘要", 1)[1].split("</tbody>", 1)[0]


def test_v11b_repair_migration_and_frontend_staging_contract() -> None:
    migration = _read(BACKEND_ROOT / "phase_11_jurisdiction_office_directory_registry.sql")
    rollback = _read(BACKEND_ROOT / "phase_11_jurisdiction_office_directory_registry_rollback.sql")
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")
    page = _read(REPO_ROOT / "quote_system_frontend" / "app" / "page.tsx")
    schemas = _read(BACKEND_ROOT / "app" / "schemas" / "quotation.py")

    assert "CREATE TABLE IF NOT EXISTS jurisdiction_office_directory_registry" in migration
    for field in (
        "country_code",
        "jurisdiction_code",
        "country_name_en",
        "office_role",
        "office_name_en",
        "office_name_cn",
        "office_display_code",
        "office_type",
        "source_id",
        "source_url",
        "source_version",
        "review_status",
        "is_active",
        "source_note",
    ):
        assert field in migration
    assert "'NL', 'NL', 'Netherlands'" in migration
    assert "Netherlands Patent Office" in migration
    assert "'CA', 'CA', 'Canada'" in migration
    assert "Canadian Intellectual Property Office" in migration
    assert "DROP TABLE IF EXISTS jurisdiction_office_directory_registry" in rollback

    assert "批量新增暂存清单" in admin
    assert "编辑本批次清单" in admin
    assert "selectedBulkReferences.length ? selectedBulkReferences.map" in admin
    assert "从清单移除" in admin
    assert "stagingIssueForField" in admin
    assert "jurisdiction_type" in admin
    assert "updateBulkStaging" in admin
    assert "stagingValidationMessage" in admin
    assert "overwrite_existing_fields" in admin
    assert "staging_items: stagingItems" in page
    assert "source_verified: sourceVerified" in page
    assert "CountryBulkFromReferenceStagingItem" in schemas
    assert "source verification is required" not in schemas


def test_kr_office_uses_moip_and_kipo_only_as_alias() -> None:
    from app.reference.jurisdiction_field_sources import (
        OFFICE_ALIASES_BY_COUNTRY,
        OFFICE_DISPLAY_CODE_BY_COUNTRY,
        OFFICE_NAME_CN_BY_COUNTRY,
    )
    from app.reference.jurisdiction_office_directory import default_office_directory_items
    from app.reference.jurisdiction_registry import default_registry_items
    from app.services import quotation_service

    kr_directory = next(item for item in default_office_directory_items() if item.country_code == "KR")
    kr_reference = next(item for item in default_registry_items() if item.standard_code == "KR")
    kr_office = quotation_service._reference_default_office_fields(kr_reference)  # noqa: SLF001
    migration = _read(BACKEND_ROOT / "phase_10_jurisdiction_v11b_master_page_refinement.sql")
    frontend = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")

    assert kr_directory.office_name_en == "Ministry of Intellectual Property"
    assert kr_directory.office_display_code == "MOIP"
    assert OFFICE_DISPLAY_CODE_BY_COUNTRY["KR"] == "MOIP"
    assert OFFICE_NAME_CN_BY_COUNTRY["KR"] == "韩国知识产权部"
    assert "KIPO" in OFFICE_ALIASES_BY_COUNTRY["KR"]
    assert kr_office["default_office_name_en"] == "Ministry of Intellectual Property"
    assert kr_office["default_office_code"] == "MOIP"
    assert kr_office["default_office_name_cn"] == "韩国知识产权部"
    assert "WHEN 'KR' THEN 'MOIP'" in migration
    assert "WHEN 'KR' THEN 'KIPO'" not in migration
    assert 'default_office_code: "MOIP"' in frontend


def test_manual_remarks_are_separate_from_import_trace() -> None:
    service = _read(BACKEND_ROOT / "app" / "services" / "quotation_service.py")
    admin = _read(REPO_ROOT / "quote_system_frontend" / "app" / "components" / "admin.tsx")
    page = _read(REPO_ROOT / "quote_system_frontend" / "app" / "page.tsx")

    assert '"remarks": ""' in service
    assert "created_from_reference：候选对象仅用于带出主档字段" in service
    assert "从 reference 批量添加" in admin
    assert "从本地 reference 批量添加" not in admin
    assert "businessRemark(country.remarks" in admin
    assert "isTechnicalRemark(value)" in admin
    assert "source_note" in page
    assert "batch_note: \"\"" in page
