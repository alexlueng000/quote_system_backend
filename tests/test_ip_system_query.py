from __future__ import annotations

from datetime import date

from app.main import app
from app.reference.ip_system_official_baseline import official_baseline_count
from app.schemas.ip_system_query import IpSystemQuerySystem
from app.services import ip_system_query_service
from app.services.ip_system_query_service import OfficialMember


def test_ip_system_query_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/ip-system-query/systems" in paths
    assert "/api/v1/ip-system-query/systems/{system_code}/members" in paths
    assert "/api/v1/ip-system-query/jurisdictions/search" in paths
    assert "/api/v1/ip-system-query/jurisdictions/memberships" in paths
    assert "/api/v1/ip-system-query/systems/{system_code}/check-updates" in paths
    assert "/api/v1/ip-system-query/systems/{system_code}/apply-updates" in paths
    assert "/api/v1/ip-system-query/data-sources" in paths
    assert "/api/v1/ip-system-query/data-sources/{source_id}" in paths
    assert "/api/v1/ip-system-query/data-sources/{source_id}/check-updates" in paths
    assert "/api/v1/ip-system-query/data-sources/{source_id}/apply-updates" in paths
    assert "/api/v1/ip-system-query/update-history" in paths
    assert "/api/v1/ip-system-query/reference-objects" in paths
    assert "/api/v1/ip-system-query/systems/{system_code}/members/{jurisdiction_code}/remark" in paths


def test_query_service_filters_unconfirmed_rows() -> None:
    assert not ip_system_query_service._is_confirmed_row({  # noqa: SLF001
        "verification_status": "pending_review",
        "data_quality_flags_json": None,
    })
    assert not ip_system_query_service._is_confirmed_row({  # noqa: SLF001
        "verification_status": "confirmed",
        "data_quality_flags_json": '["sample_only"]',
    })
    assert not ip_system_query_service._is_confirmed_row({  # noqa: SLF001
        "verification_status": "confirmed",
        "data_quality_flags_json": '["needs_official_confirmation"]',
    })
    assert ip_system_query_service._is_confirmed_row({  # noqa: SLF001
        "verification_status": "confirmed",
        "data_quality_flags_json": None,
    })


def test_jurisdiction_memberships_return_only_lightweight_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        ip_system_query_service,
        "_jurisdictions_by_ids",
        lambda ids: {
            "jur-DE": {
                "jurisdiction_id": "jur-DE",
                "display_code": "DE",
                "name_cn": "德国",
                "name_en": "Germany",
            }
        },
    )
    monkeypatch.setattr(
        ip_system_query_service,
        "_official_member_rows",
        lambda *args, **kwargs: [
            {
                "system_code": "PCT",
                "jurisdiction_code": "DE",
                "name_zh": "德国",
                "name_en": "Germany",
                "effective_date": date(1978, 1, 24),
                "remark": "已确认",
            },
            {
                "system_code": "EPC",
                "jurisdiction_code": "DE",
                "name_zh": "德国",
                "name_en": "Germany",
                "effective_date": date(1977, 10, 7),
                "remark": "",
            },
        ],
    )
    monkeypatch.setattr(
        ip_system_query_service,
        "_master_status_by_codes",
        lambda codes: {"DE": {"jurisdiction_id": "jur-DE", "name_zh": "德国", "name_en": "Germany", "status": "exists", "label": "已录入主档"}},
    )

    groups = ip_system_query_service.get_jurisdiction_memberships(["jur-DE"])

    assert len(groups) == 1
    assert groups[0].name_zh == "德国"
    assert [item.system_code for item in groups[0].memberships] == ["PCT", "EPC"]
    assert groups[0].memberships[0].system_name_zh == "专利合作条约"
    assert groups[0].memberships[0].remark == "已确认"


def test_p0_official_baseline_counts_are_formal() -> None:
    assert official_baseline_count("PCT") == 158
    assert official_baseline_count("PARIS") == 181
    assert official_baseline_count("EPC") == 40
    assert official_baseline_count("EU_DESIGN") == 27


def test_pct_route_hint_only_marks_regional_only_states() -> None:
    regional_only = ip_system_query_service._route_hint("BE", "PCT", "pct_contracting_state")  # noqa: SLF001
    ordinary = ip_system_query_service._route_hint("DE", "PCT", "pct_contracting_state")  # noqa: SLF001

    assert regional_only["pct_route_type"] == "regional_only"
    assert regional_only["regional_system_code"] == "EP"
    assert ordinary["pct_route_type"] == "national_or_regional"
    assert ordinary["regional_system_code"] == "EP"
    assert ip_system_query_service._route_hint("US", "PCT", "pct_contracting_state") == {}  # noqa: SLF001


def test_pct_route_hint_covers_ap_ea_ep_oa_examples() -> None:
    assert ip_system_query_service._route_hint("SZ", "PCT", "pct_contracting_state")["regional_system_code"] == "AP"  # noqa: SLF001
    assert ip_system_query_service._route_hint("BW", "PCT", "pct_contracting_state")["pct_route_type"] == "national_or_regional"  # noqa: SLF001
    assert ip_system_query_service._route_hint("AM", "PCT", "pct_contracting_state")["regional_system_code"] == "EA"  # noqa: SLF001
    assert ip_system_query_service._route_hint("BF", "PCT", "pct_contracting_state")["regional_system_code"] == "OA"  # noqa: SLF001


def test_paris_non_pct_route_hint_does_not_create_pct_membership() -> None:
    hint = ip_system_query_service._route_hint("AF", "PARIS", "paris_contracting_party")  # noqa: SLF001
    pct_hint = ip_system_query_service._route_hint("AF", "PCT", "pct_contracting_state")  # noqa: SLF001

    assert hint["pct_route_type"] == "paris_only_non_pct"
    assert pct_hint == {}


def test_epc_current_relations_exclude_historical_and_moldova_validation() -> None:
    rows = ip_system_query_service._epc_relation_reference_rows(include_historical=False)  # noqa: SLF001
    relation_by_code = {
        str(row["jurisdiction_code"]): str(row["membership_relation_type"])
        for row in rows
    }

    assert relation_by_code["BA"] == "extension_state"
    assert relation_by_code["MA"] == "validation_state"
    assert "MD" not in relation_by_code
    assert "AL" not in relation_by_code


def test_reference_objects_include_hong_kong_without_treaty_membership(monkeypatch) -> None:
    monkeypatch.setattr(ip_system_query_service, "_master_status_by_codes", lambda codes: {})
    response = ip_system_query_service.list_reference_objects()
    hk = next(item for item in response.objects if item.code == "HK")

    assert response.reference_count == 202
    assert hk.name_zh == "中国香港"
    assert hk.object_type == "region"
    assert not hk.is_pct_contracting_state
    assert not hk.is_paris_contracting_party


def test_reference_object_search_aliases_find_hk_mo_and_eu(monkeypatch) -> None:
    monkeypatch.setattr(ip_system_query_service, "_master_status_by_codes", lambda codes: {})

    cn_hk_matches = ip_system_query_service._search_reference_objects("中国香港")  # noqa: SLF001
    hk_matches = ip_system_query_service._search_reference_objects("Hong Kong")  # noqa: SLF001
    hk_code_matches = ip_system_query_service._search_reference_objects("HK")  # noqa: SLF001
    hk_punct_matches = ip_system_query_service._search_reference_objects("Hong Kong, China")  # noqa: SLF001
    cn_mo_matches = ip_system_query_service._search_reference_objects("中国澳门")  # noqa: SLF001
    mo_matches = ip_system_query_service._search_reference_objects("Macau")  # noqa: SLF001
    mo_code_matches = ip_system_query_service._search_reference_objects("MO")  # noqa: SLF001
    eu_matches = ip_system_query_service._search_reference_objects("欧盟")  # noqa: SLF001
    eu_code_matches = ip_system_query_service._search_reference_objects("EU")  # noqa: SLF001

    assert cn_hk_matches[0].code == "HK"
    assert hk_matches[0].code == "HK"
    assert hk_matches[0].has_reference_object
    assert hk_code_matches[0].code == "HK"
    assert hk_punct_matches[0].code == "HK"
    assert cn_mo_matches[0].code == "MO"
    assert mo_matches[0].code == "MO"
    assert mo_code_matches[0].code == "MO"
    assert eu_matches[0].code == "EU"
    assert eu_code_matches[0].code == "EU"


def test_reference_object_search_aliases_find_regional_display_codes(monkeypatch) -> None:
    monkeypatch.setattr(ip_system_query_service, "_master_status_by_codes", lambda codes: {})

    expected = {
        "EPO": "EP",
        "EUIPO": "EM",
        "WIPO": "WO",
        "OAPI": "OA",
        "ARIPO": "AP",
        "EAPO": "EA",
    }

    for keyword, standard_code in expected.items():
        matches = ip_system_query_service._search_reference_objects(keyword)  # noqa: SLF001
        assert matches[0].code == standard_code
        assert ip_system_query_service._is_exact_reference_query(keyword, standard_code)  # noqa: SLF001


def test_jurisdiction_search_merges_ep_epo_reference_into_canonical_master(monkeypatch) -> None:
    class FakeCursor:
        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, *args, **kwargs) -> None:
            return None

        def execute(self, *args, **kwargs) -> None:
            return None

        def fetchall(self) -> list[dict[str, object]]:
            return [
                {
                    "jurisdiction_id": "jur-EP",
                    "display_code": "EPO",
                    "internal_code": "EP",
                    "name_cn": "欧洲专利局",
                    "name_en": "European Patent Office",
                    "jurisdiction_type": "regional_office",
                }
            ]

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

    class FakeConnectionScope:
        def __enter__(self) -> FakeConnection:
            return FakeConnection()

        def __exit__(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(
        ip_system_query_service,
        "_search_official_members",
        lambda keyword: [
            ip_system_query_service.IpSystemJurisdictionOption(
                code="EP",
                name_zh="欧洲专利局",
                name_en="European Patent Office",
                member_type="regional_office",
                master_status="missing",
                master_status_label="未录入主档",
                matched_system_codes=["EPC"],
            )
        ],
    )
    monkeypatch.setattr(ip_system_query_service, "_master_status_by_codes", lambda codes: {})
    monkeypatch.setattr(ip_system_query_service, "_reference_baseline_by_code", lambda: {})
    monkeypatch.setattr(ip_system_query_service.mysql, "connection_scope", lambda: FakeConnectionScope())

    for keyword in ("欧洲", "EP", "EPO", "European Patent Office"):
        matches = ip_system_query_service.search_jurisdictions(keyword)
        epo_matches = [
            item
            for item in matches
            if item.name_en == "European Patent Office" or item.code in {"EP", "EPO"}
        ]
        assert len(epo_matches) == 1
        assert epo_matches[0].jurisdiction_id == "jur-EP"
        assert epo_matches[0].code == "EPO"
        assert epo_matches[0].has_reference_object
        assert epo_matches[0].object_type_label == "区域局"


def test_jurisdiction_search_filters_non_country_query_scope_objects(monkeypatch) -> None:
    rows = [
        {
            "jurisdiction_id": "jur-EP",
            "display_code": "EPO",
            "internal_code": "EP",
            "name_cn": "欧洲专利局",
            "name_en": "European Patent Office",
            "jurisdiction_type": "regional_office",
        },
        {
            "jurisdiction_id": "jur-EM",
            "display_code": "EUIPO",
            "internal_code": "EM",
            "name_cn": "欧盟知识产权局",
            "name_en": "European Union Intellectual Property Office",
            "jurisdiction_type": "regional_office",
        },
        {
            "jurisdiction_id": "jur-WO",
            "display_code": "WIPO",
            "internal_code": "WO",
            "name_cn": "世界知识产权组织",
            "name_en": "World Intellectual Property Organization",
            "jurisdiction_type": "international_organization",
        },
        {
            "jurisdiction_id": "jur-IB",
            "display_code": "IB",
            "internal_code": "IB",
            "name_cn": "WIPO 国际局",
            "name_en": "International Bureau of WIPO",
            "jurisdiction_type": "international_organization",
        },
        {
            "jurisdiction_id": "jur-EU",
            "display_code": "EU",
            "internal_code": "EU",
            "name_cn": "欧洲联盟",
            "name_en": "European Union",
            "jurisdiction_type": "international_organization",
        },
        {
            "jurisdiction_id": "jur-PCT",
            "display_code": "PCT",
            "internal_code": "PCT",
            "name_cn": "专利合作条约入口",
            "name_en": "Patent Cooperation Treaty",
            "jurisdiction_type": "treaty_entry",
        },
        {
            "jurisdiction_id": "jur-HAGUE",
            "display_code": "Hague",
            "internal_code": "HAGUE",
            "name_cn": "海牙体系",
            "name_en": "Hague System",
            "jurisdiction_type": "treaty_entry",
        },
        {
            "jurisdiction_id": "jur-MADRID",
            "display_code": "Madrid",
            "internal_code": "MADRID",
            "name_cn": "马德里体系",
            "name_en": "Madrid System",
            "jurisdiction_type": "treaty_entry",
        },
        {
            "jurisdiction_id": "jur-NICE",
            "display_code": "Nice",
            "internal_code": "NICE",
            "name_cn": "尼斯分类",
            "name_en": "Nice Classification",
            "jurisdiction_type": "treaty_entry",
        },
    ]

    class FakeCursor:
        keyword = ""

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, *args, **kwargs) -> None:
            return None

        def execute(self, query, params) -> None:
            self.keyword = str(params[0]).strip("%").upper()

        def fetchall(self) -> list[dict[str, object]]:
            if not self.keyword:
                return []
            return [
                row
                for row in rows
                if any(
                    self.keyword in str(row.get(field) or "").upper()
                    for field in ("display_code", "internal_code", "name_cn", "name_en")
                )
            ]

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

    class FakeConnectionScope:
        def __enter__(self) -> FakeConnection:
            return FakeConnection()

        def __exit__(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(ip_system_query_service, "_search_official_members", lambda keyword: [])
    monkeypatch.setattr(ip_system_query_service, "_master_status_by_codes", lambda codes: {})
    monkeypatch.setattr(ip_system_query_service, "_reference_baseline_by_code", lambda: {})
    monkeypatch.setattr(ip_system_query_service.mysql, "connection_scope", lambda: FakeConnectionScope())

    europe_matches = ip_system_query_service.search_jurisdictions("欧洲")
    assert {item.code for item in europe_matches} == {"EPO"}

    broad_eu_matches = ip_system_query_service.search_jurisdictions("欧")
    assert "EU" not in {item.code for item in broad_eu_matches}
    assert {"EPO", "EUIPO", "EA"}.issubset({item.code for item in broad_eu_matches})

    euipo_matches = ip_system_query_service.search_jurisdictions("EM")
    assert [item.code for item in euipo_matches if item.name_zh == "欧盟知识产权局"] == ["EUIPO"]

    for keyword in ("PCT", "Hague", "Madrid", "Nice"):
        assert ip_system_query_service.search_jurisdictions(keyword) == []

    wipo_matches = ip_system_query_service.search_jurisdictions("WO")
    assert [item.code for item in wipo_matches if item.name_zh == "世界知识产权组织"] == ["WIPO"]

    for keyword in ("wi", "WIPO", "IB", "International Bureau", "International Bureau of WIPO", "世界知识产权组织"):
        matches = ip_system_query_service.search_jurisdictions(keyword)
        wipo_related = [
            item
            for item in matches
            if item.code in {"WIPO", "WO", "IB"} or "WIPO" in item.name_en or item.name_zh == "世界知识产权组织"
        ]
        assert len(wipo_related) == 1
        assert wipo_related[0].code == "WIPO"
        assert wipo_related[0].name_zh == "世界知识产权组织"


def test_reference_only_membership_query_returns_display_group(monkeypatch) -> None:
    monkeypatch.setattr(ip_system_query_service, "_jurisdictions_by_ids", lambda ids: {})
    monkeypatch.setattr(ip_system_query_service, "_display_member_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(ip_system_query_service, "_master_status_by_codes", lambda codes: {})
    hk_reference = next(item for item in ip_system_query_service.list_reference_objects().objects if item.code == "HK")
    monkeypatch.setattr(ip_system_query_service, "_reference_objects_by_code", lambda codes=None: {"HK": hk_reference})

    groups = ip_system_query_service.get_jurisdiction_memberships_by_codes(
        jurisdiction_ids=[],
        jurisdiction_codes=["HK"],
    )

    assert len(groups) == 1
    assert groups[0].code == "HK"
    assert groups[0].name_zh == "中国香港"
    assert groups[0].object_type_label == "地区 / 特别行政区"
    assert groups[0].has_reference_object
    assert not groups[0].memberships
    assert not groups[0].is_pct_contracting_state
    assert not groups[0].is_paris_contracting_party


def test_check_updates_returns_simple_diffs(monkeypatch) -> None:
    monkeypatch.setattr(
        ip_system_query_service,
        "_get_system_by_code",
        lambda system_code: IpSystemQuerySystem(
            system_code="PCT",
            name_zh="专利合作条约",
            name_en="Patent Cooperation Treaty",
            short_name="PCT",
            category="international_treaty",
            source_url="https://example.test/pct",
        ),
    )
    monkeypatch.setattr(
        ip_system_query_service,
        "_fetch_official_members",
        lambda system: [
            OfficialMember(
                code="DE",
                name_en="Germany",
                effective_date=date(1978, 1, 24),
                remark="",
                source_url=system.source_url,
            ),
            OfficialMember(
                code="FR",
                name_en="France",
                effective_date=date(1978, 1, 24),
                remark="",
                source_url=system.source_url,
            ),
        ],
    )
    monkeypatch.setattr(
        ip_system_query_service,
        "_official_member_rows",
        lambda system_code: [
            {
                "jurisdiction_code": "DE",
                "name_zh": "德国",
                "name_en": "Germany",
                "effective_date": date(1978, 1, 1),
                "source_url": "https://example.test/old",
                "remark": "",
            },
            {
                "jurisdiction_code": "JP",
                "name_zh": "日本",
                "name_en": "Japan",
                "effective_date": date(1978, 1, 1),
                "source_url": "https://example.test/old",
                "remark": "",
            },
        ],
    )
    result = ip_system_query_service.check_updates("PCT")

    change_types = {item.change_type for item in result.diffs}
    assert result.has_changes
    assert {"added_member", "removed_member", "effective_date_changed", "source_changed"}.issubset(change_types)
