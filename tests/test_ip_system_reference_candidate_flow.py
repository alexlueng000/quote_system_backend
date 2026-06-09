from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.db import mysql
from app.main import app
from app.schemas.ip_system import (
    IpSystemChangeReviewUpdate,
    IpSystemManualRelationReviewCreate,
    IpSystemPublishBatchRequest,
    IpSystemReferenceCandidateCreate,
    IpSystemReferenceReviewCreate,
)
from app.services import ip_system_service


TEST_SOURCE_PCT = "p0test-source-pct"
TEST_SOURCE_MANUAL = "p0test-source-manual"
TEST_SOURCE_EUIPO = "p0test-source-euipo"


@pytest.fixture()
def p0test_sources() -> None:
    _cleanup_p0test_records()
    _ensure_test_source(TEST_SOURCE_PCT, "ip-system-pct", "p0test://pct")
    _ensure_test_source(TEST_SOURCE_MANUAL, "ip-system-epc", "p0test://manual")
    _ensure_test_source(TEST_SOURCE_EUIPO, "ip-system-euipo", "p0test://euipo")
    try:
        yield
    finally:
        _cleanup_p0test_records()


def test_ip_system_candidate_api_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/ip-systems/{system_id}/reference-candidates" in paths
    assert "/api/v1/ip-system-relation-candidates" in paths
    assert "/api/v1/jurisdictions/{jurisdiction_id}/ip-system-reference-check" in paths
    assert "/api/v1/ip-system-relation-candidates/reviews" in paths
    assert "/api/v1/ip-system-change-reviews/{review_id}" in paths
    assert "/api/v1/ip-system-sync-batches/{batch_id}/publish" in paths


def test_reference_candidate_review_publish_flow_and_formal_read_boundaries(p0test_sources: None) -> None:
    previous_enabled = _set_jurisdiction_enabled("jur-CN", True)
    try:
        created = ip_system_service.create_reference_candidates(
            "ip-system-pct",
            IpSystemReferenceCandidateCreate(
                source_config_id=TEST_SOURCE_PCT,
                business_domain="patent",
                relation_type_code="CONTRACTING_STATE",
                parse_mode="pasted_text",
                pasted_text="China (CN)\nP0 Test Neverland (ZZ)",
                remark="p0test pasted_text candidate source",
            ),
            actor="admin@example.com",
        )
        assert created.matched_count == 1
        assert created.unmatched_count == 1
        cn_candidate = next(
            item for item in created.candidates if item.matched_jurisdiction_id == "jur-CN"
        )

        check_result = ip_system_service.get_jurisdiction_reference_check("jur-CN")
        assert any(item.candidate_id == cn_candidate.candidate_id for item in check_result.reference_candidates)

        review_payload = ip_system_service.create_reviews_from_reference_candidates(
            IpSystemReferenceReviewCreate(
                candidate_ids=[cn_candidate.candidate_id],
                review_comment="p0test candidate confirmed",
            ),
            actor="admin@example.com",
        )
        assert review_payload.created_count == 1
        review = review_payload.reviews[0]
        assert review.review_status == "pending_review"

        assert not _formal_relation_sources("jur-CN", "p0test://pct")

        approved = ip_system_service.update_change_review(
            review.review_id,
            IpSystemChangeReviewUpdate(review_status="approved", review_comment="p0test approved"),
            actor="admin@example.com",
        )
        assert approved.review_status == "approved"

        published = ip_system_service.publish_batch(
            review_payload.batch_id,
            IpSystemPublishBatchRequest(auto_approve_pending=False),
            actor="admin@example.com",
            can_auto_approve=True,
        )
        assert published.published_count == 1

        formal_sources = _formal_relation_sources("jur-CN", "p0test://pct")
        assert formal_sources == ["p0test://pct"]
    finally:
        _set_jurisdiction_enabled("jur-CN", previous_enabled)


def test_manual_reference_candidate_enters_review_without_direct_publish(p0test_sources: None) -> None:
    payload = ip_system_service.create_reference_candidates(
        "ip-system-epc",
        IpSystemReferenceCandidateCreate(
            source_config_id=TEST_SOURCE_MANUAL,
            business_domain="patent",
            relation_type_code="VALIDATION_STATE",
            parse_mode="manual_reference",
            official_name="Japan",
            official_code="JP",
            evidence_text="P0 Test manual_reference evidence for Japan",
            data_quality_flags=["sample_only", "needs_official_confirmation"],
            remark="p0test manual_reference candidate source",
        ),
        actor="admin@example.com",
    )
    assert payload.total_candidates == 1
    assert payload.matched_count == 1
    candidate = payload.candidates[0]
    assert candidate.matched_jurisdiction_id == "jur-JP"
    assert set(candidate.data_quality_flags) == {"sample_only", "needs_official_confirmation"}

    review_response = ip_system_service.create_reviews_from_reference_candidates(
        IpSystemReferenceReviewCreate(
            candidate_ids=[candidate.candidate_id],
            review_comment="p0test manual candidate confirmed",
        ),
        actor="admin@example.com",
    )
    assert review_response.created_count == 1
    assert not _formal_relation_sources("jur-JP", "p0test://manual")


def test_formal_read_filters_publish_status_current_as_of_and_deleted_jurisdiction() -> None:
    _cleanup_p0test_records()
    try:
        active_review = ip_system_service.create_manual_relation_review(
            IpSystemManualRelationReviewCreate(
                jurisdiction_id="jur-KR",
                system_id="ip-system-epc",
                relation_type_code="VALIDATION_STATE",
                business_domain="patent",
                effective_date=date.today() - timedelta(days=10),
                source_reference="p0test://current",
                data_quality_flags=["sample_only", "needs_official_confirmation"],
                review_comment="p0test current relation",
            ),
            actor="admin@example.com",
        )
        ip_system_service.update_change_review(
            active_review.review_id,
            IpSystemChangeReviewUpdate(review_status="approved", review_comment="p0test approved"),
            actor="admin@example.com",
        )
        ip_system_service.publish_batch(
            active_review.batch_id,
            IpSystemPublishBatchRequest(auto_approve_pending=False),
            actor="admin@example.com",
            can_auto_approve=True,
        )

        expired_review = ip_system_service.create_manual_relation_review(
            IpSystemManualRelationReviewCreate(
                jurisdiction_id="jur-KR",
                system_id="ip-system-epc",
                relation_type_code="EXTENSION_STATE",
                business_domain="patent",
                effective_date=date.today() - timedelta(days=30),
                expiry_date=date.today() - timedelta(days=1),
                source_reference="p0test://expired",
                data_quality_flags=["sample_only", "needs_official_confirmation"],
                review_comment="p0test expired relation",
            ),
            actor="admin@example.com",
        )
        ip_system_service.update_change_review(
            expired_review.review_id,
            IpSystemChangeReviewUpdate(review_status="approved", review_comment="p0test approved"),
            actor="admin@example.com",
        )
        ip_system_service.publish_batch(
            expired_review.batch_id,
            IpSystemPublishBatchRequest(auto_approve_pending=False),
            actor="admin@example.com",
            can_auto_approve=True,
        )
        _insert_pending_formal_relation()

        current_sources = _formal_relation_sources("jur-KR", "p0test://")
        assert "p0test://current" in current_sources
        assert "p0test://expired" not in current_sources
        assert "p0test://pending-formal" not in current_sources

        all_relations = ip_system_service.get_jurisdiction_relations(
            "jur-KR",
            current_only=False,
            published_only=True,
        )
        all_sources = [item.source_reference for item in all_relations if item.source_reference.startswith("p0test://")]
        assert "p0test://current" in all_sources
        assert "p0test://expired" in all_sources
        assert "p0test://pending-formal" not in all_sources

        historical = ip_system_service.get_jurisdiction_relations(
            "jur-KR",
            as_of=date.today() - timedelta(days=2),
            current_only=True,
            published_only=True,
        )
        historical_sources = [
            item.source_reference for item in historical if item.source_reference.startswith("p0test://")
        ]
        assert "p0test://expired" in historical_sources

        _mark_jurisdiction_deleted("jur-KR", True)
        assert not _formal_relation_sources("jur-KR", "p0test://current")
    finally:
        _mark_jurisdiction_deleted("jur-KR", False)
        _cleanup_p0test_records()


def test_phase_one_system_status_and_forbidden_entry_routes(p0test_sources: None) -> None:
    systems = {item.system_code: item for item in ip_system_service.list_ip_systems(include_inactive=True)}
    for code in ("PCT", "PARIS", "EPC", "EUIPO"):
        assert systems[code].is_active is True
    for code in ("HAGUE", "UPC_UP", "OAPI", "ARIPO", "MADRID"):
        assert systems[code].is_active is False

    disabled_domains = _system_domain_enabled_values(("HAGUE", "UPC_UP", "OAPI", "ARIPO", "MADRID"))
    assert disabled_domains
    assert all(value == 0 for value in disabled_domains.values())

    forbidden_routes = _forbidden_regional_entry_routes()
    assert forbidden_routes == []

    payload = ip_system_service.create_reference_candidates(
        "ip-system-euipo",
        IpSystemReferenceCandidateCreate(
            source_config_id=TEST_SOURCE_EUIPO,
            business_domain="design",
            relation_type_code="COVERED_STATE",
            parse_mode="manual_reference",
            official_name="European Union Intellectual Property Office",
            official_code="EM",
            evidence_text="P0 Test EUIPO first-phase sample; not an entry_route.",
            data_quality_flags=["sample_only", "needs_official_confirmation"],
        ),
        actor="admin@example.com",
    )
    assert payload.matched_count == 1
    assert payload.candidates[0].matched_jurisdiction_id == "jur-EM"


def test_p0_7_regional_relation_types_and_epo_samples_are_available() -> None:
    relation_types = {item.relation_type_code: item for item in ip_system_service.list_relation_types()}
    for code in (
        "REGIONAL_PHASE_OFFICE",
        "GRANTING_AUTHORITY",
        "PRIORITY_ROUTE_AVAILABLE",
        "REGIONAL_COVERAGE",
    ):
        assert code in relation_types

    ep_relations = ip_system_service.get_jurisdiction_relations(
        "jur-EP",
        current_only=True,
        published_only=True,
    )
    relation_keys = {
        (item.system_code, item.relation_type_code, item.business_domain)
        for item in ep_relations
    }
    assert ("PCT", "REGIONAL_PHASE_OFFICE", "patent") in relation_keys
    assert ("EPC", "GRANTING_AUTHORITY", "patent") in relation_keys
    assert ("PARIS", "PRIORITY_ROUTE_AVAILABLE", "general_ip") in relation_keys
    assert ("PCT", "CONTRACTING_STATE", "patent") not in relation_keys
    assert ("PARIS", "CONTRACTING_STATE", "general_ip") not in relation_keys

    p0_7_rows = [
        item
        for item in ep_relations
        if item.relation_type_code in {
            "REGIONAL_PHASE_OFFICE",
            "GRANTING_AUTHORITY",
            "PRIORITY_ROUTE_AVAILABLE",
        }
    ]
    assert p0_7_rows
    for relation in p0_7_rows:
        assert {"sample_only", "needs_official_confirmation", "p0_7_regional_semantics"}.issubset(
            set(relation.data_quality_flags)
        )
        assert relation.publish_status == "published"
        assert relation.is_current_effective is True
        assert relation.quote_hint_enabled is False
        assert relation.path_rule_dependency is False

    reference_check = ip_system_service.get_jurisdiction_reference_check("jur-EP")
    assert all(item.publish_status == "published" for item in reference_check.published_relations)
    assert all(
        item.review_status in {"pending_review", "approved"}
        for item in reference_check.pending_reviews
    )


def test_p0_7_regional_offices_are_not_pct_or_paris_contracting_states() -> None:
    assert _forbidden_pct_contracting_state_rows() == []
    assert _paris_ep_contracting_state_rows() == []


def test_p0_7_reserved_regional_systems_remain_inactive() -> None:
    systems = {item.system_code: item for item in ip_system_service.list_ip_systems(include_inactive=True)}
    for code in ("OAPI", "ARIPO"):
        assert systems[code].is_active is False
    if "EAPO" in systems:
        assert systems["EAPO"].is_active is False

    disabled_domains = _system_domain_enabled_values(("OAPI", "ARIPO"))
    assert disabled_domains
    assert all(value == 0 for value in disabled_domains.values())


def _ensure_test_source(source_config_id: str, system_id: str, source_url: str) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ip_system_source_config (
              source_config_id, system_id, source_name, source_type, source_url,
              source_scope, official_source_name, parser_key, parse_mode,
              update_frequency, auto_check_enabled, is_active, remark
            )
            VALUES (
              %s, %s, %s, 'manual_test_reference', %s,
              'reference_only', 'P0 Test', 'manual_reference', 'manual_reference',
              'manual', 0, 1, 'p0test source'
            )
            ON DUPLICATE KEY UPDATE
              source_url = VALUES(source_url),
              source_scope = VALUES(source_scope),
              official_source_name = VALUES(official_source_name),
              parser_key = VALUES(parser_key),
              parse_mode = VALUES(parse_mode),
              is_active = VALUES(is_active),
              remark = VALUES(remark)
            """,
            (source_config_id, system_id, source_config_id, source_url),
        )


def _cleanup_p0test_records() -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM ip_system_change_review WHERE review_comment LIKE 'p0test%'")
        cursor.execute("DELETE FROM jurisdiction_ip_system_relation WHERE source_reference LIKE 'p0test://%'")
        cursor.execute("DELETE FROM ip_system_relation_candidate WHERE source_config_id LIKE 'p0test-%'")
        cursor.execute("DELETE FROM ip_system_match_exception WHERE source_config_id LIKE 'p0test-%'")
        cursor.execute("DELETE FROM ip_system_sync_batch WHERE source_config_id LIKE 'p0test-%'")
        cursor.execute("DELETE FROM ip_system_source_snapshot WHERE source_config_id LIKE 'p0test-%'")
        cursor.execute("DELETE FROM ip_system_source_config WHERE source_config_id LIKE 'p0test-%'")


def _formal_relation_sources(jurisdiction_id: str, source_prefix: str) -> list[str]:
    return [
        item.source_reference
        for item in ip_system_service.get_jurisdiction_relations(
            jurisdiction_id,
            current_only=True,
            published_only=True,
        )
        if item.source_reference.startswith(source_prefix)
    ]


def _insert_pending_formal_relation() -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO jurisdiction_ip_system_relation (
              relation_id, jurisdiction_id, system_id, relation_type_id, business_domain,
              is_active, effective_date, publish_status, source_reference,
              source_official_name, source_official_code, verification_status,
              data_quality_flags_json, admin_remark
            )
            SELECT
              'p0test-pending-formal-relation', 'jur-KR', 'ip-system-epc',
              relation_type_id, 'patent', 1, CURDATE(), 'pending_review',
              'p0test://pending-formal', 'Korea', 'KR', 'pending_review',
              JSON_ARRAY('sample_only', 'needs_official_confirmation'),
              'p0test pending formal relation should not be read'
            FROM ip_system_relation_type
            WHERE relation_type_code = 'FORMER_MEMBER'
            LIMIT 1
            ON DUPLICATE KEY UPDATE
              publish_status = VALUES(publish_status),
              source_reference = VALUES(source_reference)
            """,
        )


def _mark_jurisdiction_deleted(jurisdiction_id: str, deleted: bool) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE jurisdictions SET is_deleted = %s WHERE jurisdiction_id = %s",
            (1 if deleted else 0, jurisdiction_id),
        )


def _set_jurisdiction_enabled(jurisdiction_id: str, enabled: bool) -> bool:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT is_enabled FROM jurisdictions WHERE jurisdiction_id = %s LIMIT 1",
            (jurisdiction_id,),
        )
        row = cursor.fetchone()
        previous = bool(row["is_enabled"]) if row else False
        cursor.execute(
            "UPDATE jurisdictions SET is_enabled = %s WHERE jurisdiction_id = %s",
            (1 if enabled else 0, jurisdiction_id),
        )
    return previous


def _system_domain_enabled_values(system_codes: tuple[str, ...]) -> dict[str, int]:
    placeholders = ", ".join(["%s"] * len(system_codes))
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT CONCAT(s.system_code, ':', d.business_domain) AS key_value, d.is_enabled
            FROM ip_system_business_domain d
            JOIN ip_system_master s ON s.system_id = d.system_id
            WHERE s.system_code IN ({placeholders})
            """,
            system_codes,
        )
        return {str(row["key_value"]): int(row["is_enabled"]) for row in cursor.fetchall()}


def _forbidden_regional_entry_routes() -> list[str]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT filing_route
            FROM country_path_rules
            WHERE UPPER(filing_route) IN ('EPC', 'EPO', 'EUIPO', 'UPC_UP', 'UPC', 'UP')
            """
        )
        return [str(row["filing_route"]) for row in cursor.fetchall()]


def _forbidden_pct_contracting_state_rows() -> list[dict[str, object]]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT s.system_code, rt.relation_type_code, j.display_code, j.name_en, j.jurisdiction_type
            FROM jurisdiction_ip_system_relation r
            JOIN ip_system_master s ON s.system_id = r.system_id
            JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
            JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            WHERE s.system_code = 'PCT'
              AND rt.relation_type_code = 'CONTRACTING_STATE'
              AND r.publish_status = 'published'
              AND r.is_active = 1
              AND (
                j.jurisdiction_type <> 'single_country'
                OR j.display_code IN ('EP', 'EPO', 'EA', 'EAPO', 'OA', 'OAPI', 'AP', 'ARIPO')
                OR j.name_en LIKE '%European Patent%'
                OR j.name_en LIKE '%Eurasian%'
                OR j.name_en LIKE '%OAPI%'
                OR j.name_en LIKE '%ARIPO%'
                OR j.name_en LIKE '%African%'
              )
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def _paris_ep_contracting_state_rows() -> list[dict[str, object]]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT s.system_code, rt.relation_type_code, j.display_code, j.name_en, j.jurisdiction_type
            FROM jurisdiction_ip_system_relation r
            JOIN ip_system_master s ON s.system_id = r.system_id
            JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
            JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            WHERE s.system_code = 'PARIS'
              AND rt.relation_type_code = 'CONTRACTING_STATE'
              AND r.publish_status = 'published'
              AND r.is_active = 1
              AND j.jurisdiction_id = 'jur-EP'
            """
        )
        return [dict(row) for row in cursor.fetchall()]
