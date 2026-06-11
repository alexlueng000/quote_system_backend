from __future__ import annotations

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


TEST_SOURCE_PCT = "v1atest-source-pct"
TEST_SOURCE_EPC = "v1atest-source-epc"
TEST_ACTOR = "v1atest@example.com"
TEST_PCT_RELATION_BACKUP: list[dict[str, object]] = []


@pytest.fixture()
def v1a_records() -> None:
    _cleanup_v1a_records()
    _hide_cn_pct_published_relation()
    _ensure_test_source(TEST_SOURCE_PCT, "ip-system-pct", "v1atest://pct")
    _ensure_test_source(TEST_SOURCE_EPC, "ip-system-epc", "v1atest://epc")
    try:
        yield
    finally:
        _restore_cn_pct_published_relation()
        _cleanup_v1a_records()


def test_v1a_business_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/ip-systems/business-dashboard" in paths
    assert "/api/v1/ip-systems/jurisdiction-enablement-check" in paths
    assert "/api/v1/ip-systems/{system_id}/business-detail" in paths
    assert "/api/v1/jurisdictions/{jurisdiction_id}/ip-system-profile" in paths
    assert "/api/v1/ip-systems/{system_id}/reference-coverage" in paths
    assert "/api/v1/ip-systems/advanced-workbench" in paths


def test_business_dashboard_counts_only_published_current_and_dynamic_relation_types(v1a_records: None) -> None:
    before = ip_system_service.get_business_dashboard()
    pct_before = _dashboard_item(before, "PCT")

    _insert_pending_formal_relation()

    after = ip_system_service.get_business_dashboard()
    pct_after = _dashboard_item(after, "PCT")
    formal_relations = ip_system_service.get_system_relations(
        "ip-system-pct",
        current_only=True,
        published_only=True,
    )

    assert pct_after.current_relation_count == len(formal_relations)
    assert pct_after.current_relation_count == pct_before.current_relation_count
    assert "FORMER_MEMBER" not in pct_after.relation_type_counts
    assert pct_after.relation_type_counts


def test_business_detail_keeps_pending_review_out_of_formal_relations(v1a_records: None) -> None:
    review = ip_system_service.create_manual_relation_review(
        IpSystemManualRelationReviewCreate(
            jurisdiction_id="jur-KR",
            system_id="ip-system-epc",
            relation_type_code="VALIDATION_STATE",
            business_domain="patent",
            source_reference="v1atest://pending-review",
            data_quality_flags=["sample_only", "needs_official_confirmation"],
            review_comment="v1atest pending detail",
        ),
        actor=TEST_ACTOR,
    )

    detail = ip_system_service.get_business_detail("ip-system-epc")

    assert any(item.review_id == review.review_id for item in detail.pending_reviews)
    assert all(item.source_reference != "v1atest://pending-review" for item in detail.relations)
    assert any(item.item_type == "pending_review" for item in detail.todo_items)
    assert all("v1atest://pending-review" not in bucket.examples for bucket in detail.current_relation_summary)


def test_business_detail_defaults_to_summary_and_keeps_candidate_and_exception_out_of_formal_summary(v1a_records: None) -> None:
    created = ip_system_service.create_reference_candidates(
        "ip-system-pct",
        IpSystemReferenceCandidateCreate(
            source_config_id=TEST_SOURCE_PCT,
            business_domain="patent",
            relation_type_code="CONTRACTING_STATE",
            parse_mode="pasted_text",
            pasted_text="Japan (JP)\nV1A Exception Object (ZZ)",
            remark="v1atest detail summary",
        ),
        actor=TEST_ACTOR,
    )

    detail = ip_system_service.get_business_detail("ip-system-pct")

    formal_summary_count = sum(bucket.count for bucket in detail.current_relation_summary)
    assert detail.current_relation_summary
    assert formal_summary_count <= detail.relation_summary.current_relation_count
    assert any(item.item_type == "candidate" for item in detail.todo_items)
    assert any(item.item_type == "match_exception" for item in detail.todo_items)
    assert len(detail.candidates) >= len([item for item in created.candidates if item.match_status == "matched"])
    assert all("ZZ" not in bucket.examples for bucket in detail.current_relation_summary)


def test_reference_coverage_separates_candidate_published_pending_exception_and_scope(v1a_records: None) -> None:
    previous_cn_enabled = _set_jurisdiction_enabled("jur-CN", True)
    try:
        created = ip_system_service.create_reference_candidates(
            "ip-system-pct",
            IpSystemReferenceCandidateCreate(
                source_config_id=TEST_SOURCE_PCT,
                business_domain="patent",
                relation_type_code="CONTRACTING_STATE",
                parse_mode="pasted_text",
                pasted_text="Japan (JP)\nChina (CN)\nV1A Neverland (ZZ)",
                remark="v1atest reference coverage",
            ),
            actor=TEST_ACTOR,
        )
        jp_candidate = next(item for item in created.candidates if item.matched_jurisdiction_id == "jur-JP")
        review_response = ip_system_service.create_reviews_from_reference_candidates(
            IpSystemReferenceReviewCreate(
                candidate_ids=[jp_candidate.candidate_id],
                review_comment="v1atest candidate review",
            ),
            actor=TEST_ACTOR,
        )

        coverage = ip_system_service.get_reference_coverage("ip-system-pct", source_config_id=TEST_SOURCE_PCT)

        assert coverage.stats.parsed_candidate_count == 3
        assert coverage.stats.non_phase1_candidate_count == 1
        assert coverage.stats.match_exception_count == 1
        assert coverage.stats.pending_review_count >= len(review_response.reviews)
        assert coverage.stats.phase1_missing_count == 0
        assert coverage.stats.phase1_published_count >= 1
    finally:
        _set_jurisdiction_enabled("jur-CN", previous_cn_enabled)


def test_jurisdiction_profile_defaults_to_data_backed_cards_and_hides_not_applicable_systems() -> None:
    jp_profile = ip_system_service.get_jurisdiction_profile("jur-JP")
    jp_codes = {item.system_code for item in jp_profile.system_cards}
    jp_relation_codes = {
        item.system_code
        for item in ip_system_service.get_jurisdiction_relations("jur-JP", current_only=True, published_only=True)
    }

    assert jp_codes == jp_relation_codes
    assert "PCT" in jp_codes
    assert "PARIS" in jp_codes
    assert "EPC" not in jp_codes


def test_ep_profile_defaults_to_its_published_current_relations() -> None:
    ep_profile = ip_system_service.get_jurisdiction_profile("jur-EP")
    ep_codes = {item.system_code for item in ep_profile.system_cards}
    ep_relation_codes = {
        item.system_code
        for item in ip_system_service.get_jurisdiction_relations("jur-EP", current_only=True, published_only=True)
    }

    assert ep_codes == ep_relation_codes
    assert {"EPC", "PCT", "PARIS"}.issubset(ep_codes)


def test_reserved_systems_are_hidden_by_default() -> None:
    dashboard = ip_system_service.get_business_dashboard()
    visible_codes = {item.system_code for item in dashboard.items}

    assert {"HAGUE", "MADRID", "UPC_UP", "OAPI", "ARIPO"}.isdisjoint(visible_codes)


def test_enablement_check_queries_de_germany_or_returns_not_established(v1a_records: None) -> None:
    for query in ("DE", "Germany", "德国"):
        result = ip_system_service.get_jurisdiction_enablement_check(query)
        default_codes = {
            item.system_code
            for item in result.system_statuses
            if item.visibility == "default"
        }
        reserved_codes = {
            item.system_code
            for item in result.system_statuses
            if item.visibility == "reserved_hidden"
        }

        assert result.query == query
        assert {"PCT", "PARIS", "EPC", "EUIPO"}.issubset(default_codes)
        assert {"HAGUE", "MADRID", "UPC_UP", "OAPI", "ARIPO"}.issubset(reserved_codes)
        assert all(item.status == "reserved_hidden" for item in result.system_statuses if item.visibility == "reserved_hidden")
        assert result.master_status in {"active", "inactive", "deleted", "not_exists"}
        if result.matched_jurisdiction:
            assert result.matched_jurisdiction.jurisdiction_id
        else:
            assert any(action.action_key == "create_master_required" for action in result.recommended_next_actions)


def test_enablement_check_returns_create_master_required_when_master_missing(v1a_records: None) -> None:
    result = ip_system_service.get_jurisdiction_enablement_check("V1A Missing Jurisdiction")

    assert result.master_status == "not_exists"
    assert any(action.action_key == "create_master_required" for action in result.recommended_next_actions)


def test_enablement_check_returns_scope_required_for_non_phase1_master(v1a_records: None) -> None:
    result = ip_system_service.get_jurisdiction_enablement_check("CN")

    assert result.master_status in {"active", "inactive", "deleted"}
    assert result.phase_scope_status == "not_in_scope"
    assert any(action.action_key == "scope_required" for action in result.recommended_next_actions)


def test_enablement_check_returns_generate_review_or_publish_for_unpublished_candidate(v1a_records: None) -> None:
    ip_system_service.create_reference_candidates(
        "ip-system-pct",
        IpSystemReferenceCandidateCreate(
            source_config_id=TEST_SOURCE_PCT,
            business_domain="patent",
            relation_type_code="CONTRACTING_STATE",
            parse_mode="pasted_text",
            pasted_text="China (CN)",
            remark="v1atest enablement candidate",
        ),
        actor=TEST_ACTOR,
    )

    result = ip_system_service.get_jurisdiction_enablement_check("CN")

    assert any(item.matched_jurisdiction_id == "jur-CN" for item in result.reference_candidates)
    assert any(action.action_key == "generate_review_or_publish" for action in result.recommended_next_actions)


def test_enablement_check_returns_review_publish_required_for_pending_review(v1a_records: None) -> None:
    created = ip_system_service.create_reference_candidates(
        "ip-system-epc",
        IpSystemReferenceCandidateCreate(
            source_config_id=TEST_SOURCE_EPC,
            business_domain="patent",
            relation_type_code="VALIDATION_STATE",
            parse_mode="pasted_text",
            pasted_text="China (CN)",
            remark="v1atest enablement pending",
        ),
        actor=TEST_ACTOR,
    )
    candidate = next(item for item in created.candidates if item.matched_jurisdiction_id == "jur-CN")
    ip_system_service.create_reviews_from_reference_candidates(
        IpSystemReferenceReviewCreate(
            candidate_ids=[candidate.candidate_id],
            review_comment="v1atest enablement pending review",
        ),
        actor=TEST_ACTOR,
    )

    result = ip_system_service.get_jurisdiction_enablement_check("CN")

    assert result.pending_reviews
    assert any(action.action_key == "review_publish_required" for action in result.recommended_next_actions)


def test_enablement_check_returns_published_for_published_current_relation(v1a_records: None) -> None:
    result = ip_system_service.get_jurisdiction_enablement_check("JP")
    statuses = {item.system_code: item for item in result.system_statuses}

    assert result.published_relations
    assert any(action.action_key == "published" for action in result.recommended_next_actions)
    assert statuses["PCT"].status == "published"
    assert statuses["PARIS"].status == "published"
    assert statuses["EUIPO"].visibility == "default"


def test_enablement_check_system_statuses_distinguish_candidate_review_and_publish(v1a_records: None) -> None:
    previous_cn_visibility = _set_jurisdiction_current_for_test("jur-CN")
    try:
        created = ip_system_service.create_reference_candidates(
            "ip-system-pct",
            IpSystemReferenceCandidateCreate(
                source_config_id=TEST_SOURCE_PCT,
                business_domain="patent",
                relation_type_code="CONTRACTING_STATE",
                parse_mode="pasted_text",
                pasted_text="China (CN)",
                remark="v1atest status candidate",
            ),
            actor=TEST_ACTOR,
        )
        candidate = next(item for item in created.candidates if item.matched_jurisdiction_id == "jur-CN")

        candidate_result = ip_system_service.get_jurisdiction_enablement_check("CN")
        candidate_statuses = {item.system_code: item for item in candidate_result.system_statuses}

        assert candidate_statuses["PCT"].status == "reference_hit_unpublished"
        assert not _formal_relation_sources("jur-CN", "v1atest://pct")

        review_response = ip_system_service.create_reviews_from_reference_candidates(
            IpSystemReferenceReviewCreate(
                candidate_ids=[candidate.candidate_id],
                review_comment="v1atest status pending review",
            ),
            actor=TEST_ACTOR,
        )
        review_result = ip_system_service.get_jurisdiction_enablement_check("CN")
        review_statuses = {item.system_code: item for item in review_result.system_statuses}

        assert review_statuses["PCT"].status == "pending_review_exists"
        assert not _formal_relation_sources("jur-CN", "v1atest://pct")

        review = review_response.reviews[0]
        ip_system_service.update_change_review(
            review.review_id,
            IpSystemChangeReviewUpdate(review_status="approved", review_comment="v1atest approved"),
            actor=TEST_ACTOR,
        )
        assert not _formal_relation_sources("jur-CN", "v1atest://pct")

        ip_system_service.publish_batch(
            review_response.batch_id,
            IpSystemPublishBatchRequest(auto_approve_pending=False),
            actor=TEST_ACTOR,
            can_auto_approve=True,
        )
        published_result = ip_system_service.get_jurisdiction_enablement_check("CN")
        published_statuses = {item.system_code: item for item in published_result.system_statuses}

        assert published_statuses["PCT"].status == "published"
        assert _formal_relation_sources("jur-CN", "v1atest://pct") == ["v1atest://pct"]
    finally:
        _restore_jurisdiction_visibility("jur-CN", previous_cn_visibility)


def test_v1a_regional_semantics_are_not_contracting_state_and_euipo_stays_out_of_patent_ePC_mix() -> None:
    ep_relations = ip_system_service.get_jurisdiction_relations("jur-EP", current_only=True, published_only=True)
    ep_relation_keys = {
        (item.system_code, item.relation_type_code, item.business_domain)
        for item in ep_relations
    }
    systems = {item.system_code: item for item in ip_system_service.list_ip_systems(include_inactive=True)}

    assert ("PCT", "REGIONAL_PHASE_OFFICE", "patent") in ep_relation_keys
    assert ("EPC", "GRANTING_AUTHORITY", "patent") in ep_relation_keys
    assert ("PARIS", "PRIORITY_ROUTE_AVAILABLE", "general_ip") in ep_relation_keys
    assert ("PCT", "CONTRACTING_STATE", "patent") not in ep_relation_keys
    assert ("PARIS", "CONTRACTING_STATE", "general_ip") not in ep_relation_keys
    assert systems["EUIPO"].business_domain_scope != systems["EPC"].business_domain_scope
    assert systems["EUIPO"].system_category != systems["EPC"].system_category


def _dashboard_item(response, system_code: str):
    return next(item for item in response.items if item.system_code == system_code)


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
              'reference_only', 'V1A Test', 'manual_reference', 'manual_reference',
              'manual', 0, 1, 'v1atest source'
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
              'v1atest-pending-formal-relation', 'jur-KR', 'ip-system-pct',
              relation_type_id, 'patent', 1, CURDATE(), 'pending_review',
              'v1atest://pending-formal', 'Korea', 'KR', 'pending_review',
              JSON_ARRAY('sample_only', 'needs_official_confirmation'),
              'v1atest pending formal relation should not be read'
            FROM ip_system_relation_type
            WHERE relation_type_code = 'FORMER_MEMBER'
            LIMIT 1
            ON DUPLICATE KEY UPDATE
              publish_status = VALUES(publish_status),
              source_reference = VALUES(source_reference)
            """,
        )


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


def _set_jurisdiction_enabled(jurisdiction_id: str, enabled: bool) -> bool:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT is_enabled FROM jurisdictions WHERE jurisdiction_id = %s LIMIT 1", (jurisdiction_id,))
        row = cursor.fetchone()
        previous = bool(row["is_enabled"]) if row else False
        cursor.execute(
            "UPDATE jurisdictions SET is_enabled = %s WHERE jurisdiction_id = %s",
            (1 if enabled else 0, jurisdiction_id),
        )
    return previous


def _set_jurisdiction_current_for_test(jurisdiction_id: str) -> tuple[bool, bool]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT is_enabled, is_deleted FROM jurisdictions WHERE jurisdiction_id = %s LIMIT 1",
            (jurisdiction_id,),
        )
        row = cursor.fetchone() or {"is_enabled": 0, "is_deleted": 0}
        previous = (bool(row["is_enabled"]), bool(row.get("is_deleted") or False))
        cursor.execute(
            "UPDATE jurisdictions SET is_enabled = 1, is_deleted = 0 WHERE jurisdiction_id = %s",
            (jurisdiction_id,),
        )
    return previous


def _restore_jurisdiction_visibility(jurisdiction_id: str, previous: tuple[bool, bool]) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE jurisdictions SET is_enabled = %s, is_deleted = %s WHERE jurisdiction_id = %s",
            (1 if previous[0] else 0, 1 if previous[1] else 0, jurisdiction_id),
        )


def _cleanup_v1a_records() -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM ip_system_change_review WHERE review_comment LIKE 'v1atest%'")
        cursor.execute("DELETE FROM jurisdiction_ip_system_relation WHERE source_reference LIKE 'v1atest://%'")
        cursor.execute("DELETE FROM ip_system_relation_candidate WHERE source_config_id LIKE 'v1atest-%'")
        cursor.execute("DELETE FROM ip_system_match_exception WHERE source_config_id LIKE 'v1atest-%'")
        cursor.execute(
            "DELETE FROM ip_system_sync_batch WHERE source_config_id LIKE %s OR created_by = %s",
            ("v1atest-%", TEST_ACTOR),
        )
        cursor.execute("DELETE FROM ip_system_source_snapshot WHERE source_config_id LIKE 'v1atest-%'")
        cursor.execute("DELETE FROM ip_system_source_config WHERE source_config_id LIKE 'v1atest-%'")


def _hide_cn_pct_published_relation() -> None:
    global TEST_PCT_RELATION_BACKUP
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT r.relation_id, r.is_active
            FROM jurisdiction_ip_system_relation r
            JOIN ip_system_master s ON s.system_id = r.system_id
            JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
            WHERE r.jurisdiction_id = 'jur-CN'
              AND s.system_code = 'PCT'
              AND rt.relation_type_code = 'CONTRACTING_STATE'
              AND r.publish_status = 'published'
            """
        )
        TEST_PCT_RELATION_BACKUP = [dict(row) for row in cursor.fetchall()]
        if TEST_PCT_RELATION_BACKUP:
            relation_ids = [row["relation_id"] for row in TEST_PCT_RELATION_BACKUP]
            placeholders = ", ".join(["%s"] * len(relation_ids))
            cursor.execute(
                f"UPDATE jurisdiction_ip_system_relation SET is_active = 0 WHERE relation_id IN ({placeholders})",
                tuple(relation_ids),
            )


def _restore_cn_pct_published_relation() -> None:
    if not TEST_PCT_RELATION_BACKUP:
        return
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        for row in TEST_PCT_RELATION_BACKUP:
            cursor.execute(
                "UPDATE jurisdiction_ip_system_relation SET is_active = %s WHERE relation_id = %s",
                (row["is_active"], row["relation_id"]),
            )
    TEST_PCT_RELATION_BACKUP.clear()
