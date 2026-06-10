from __future__ import annotations

import re
import html as html_lib
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.db import mysql
from app.reference.ip_system_official_baseline import (
    COUNTRY_NAMES,
    EPC_CODES,
    EPC_SOURCE_NAME,
    EPC_SOURCE_URL,
    EU_DESIGN_SOURCE_NAME,
    EU_DESIGN_SOURCE_URL,
    EU_MEMBER_CODES,
    PARIS_SOURCE_NAME,
    PARIS_SOURCE_URL,
    PARIS_NON_PCT_SOURCE_NAME,
    PARIS_NON_PCT_SOURCE_URL,
    PCT_REGIONAL_DESIGNATIONS_SOURCE_NAME,
    PCT_REGIONAL_DESIGNATIONS_SOURCE_URL,
    PCT_SOURCE_NAME,
    PCT_SOURCE_URL,
    WIPO_LEX_MEMBERS_SOURCE_NAME,
    WIPO_LEX_MEMBERS_SOURCE_URL,
    official_baseline_members,
    official_baseline_source,
)
from app.schemas.ip_system_query import (
    IpSystemApplyUpdatesResponse,
    IpSystemCheckUpdatesResponse,
    IpSystemDataSource,
    IpSystemDataSourceCreate,
    IpSystemDataSourceUpdate,
    IpSystemJurisdictionMembership,
    IpSystemJurisdictionMembershipGroup,
    IpSystemJurisdictionOption,
    IpSystemMemberRemarkUpdate,
    IpSystemMemberStats,
    IpSystemMembersResponse,
    IpSystemQueryMember,
    IpSystemQuerySystem,
    IpSystemReferenceObject,
    IpSystemReferenceObjectsResponse,
    IpSystemUpdateDiff,
    IpSystemUpdateHistoryItem,
)


P0_UPDATE_SYSTEM_CODES = {"PCT", "PARIS", "EPC", "EU_DESIGN"}
P0_SYSTEM_CODES = ("PCT", "PARIS", "EPC", "EU_DESIGN")
RESERVED_SYSTEM_CODES = {"HAGUE", "UPC_UP", "MADRID", "OAPI", "ARIPO", "EAPO"}
SYSTEM_DISPLAY_OVERRIDES = {
    "PCT": {"name_zh": "专利合作条约", "short_name": "PCT"},
    "PARIS": {"name_zh": "巴黎公约", "short_name": "Paris Convention"},
    "EPC": {"name_zh": "欧洲专利公约", "short_name": "EPC"},
    "HAGUE": {"name_zh": "海牙体系", "short_name": "Hague System"},
    "EUIPO": {"name_zh": "欧盟外观设计体系", "short_name": "EU Design / RCD"},
    "EU_DESIGN": {"name_zh": "欧盟外观设计体系", "short_name": "EU Design / RCD"},
}
RELATION_TYPE_BY_SYSTEM = {
    "PCT": "CONTRACTING_STATE",
    "PARIS": "CONTRACTING_STATE",
    "EPC": "MEMBER_STATE",
    "HAGUE": "CONTRACTING_STATE",
    "EUIPO": "COVERED_STATE",
    "EU_DESIGN": "COVERED_STATE",
}
UNCONFIRMED_VERIFICATION_STATUSES = {"pending_review", "draft", "rejected", "archived"}
UNCONFIRMED_FLAGS = {"sample_only", "needs_official_confirmation"}
MEMBERSHIP_RELATION_LABELS = {
    "pct_contracting_state": "PCT 缔约国",
    "paris_contracting_party": "Paris 缔约方",
    "epc_member_state": "EPC 成员国",
    "covered_state": "适用成员国",
    "extension_state": "延伸国",
    "validation_state": "生效国",
    "historical_extension_state": "历史延伸",
    "historical_validation_state": "历史生效",
}
PCT_ROUTE_LABELS = {
    "regional_only": "仅可通过 {system} 区域阶段取得保护",
    "national_or_regional": "也可通过 {system} 区域阶段进入",
    "extension_or_validation": "可通过 {system} 生效/延伸覆盖，需确认",
    "paris_only_non_pct": "仅巴黎路径 / 非 PCT",
}
SOURCE_TYPE_BOUNDARIES = {
    "treaty_membership_source": {
        "apply_target": "confirmed membership baseline",
        "affects_membership_count": True,
        "expected_scope_suffix": "P0 confirmed membership baseline",
    },
    "regional_route_source": {
        "apply_target": "PCT regional route baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "PCT regional route baseline",
    },
    "paris_non_pct_route_source": {
        "apply_target": "Paris non-PCT route baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "Paris non-PCT route baseline",
    },
    "reference_source": {
        "apply_target": "reference object baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "WIPO Lex reference object baseline",
    },
    "design_scope_source": {
        "apply_target": "EU Design/RCD scope baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "EU Design/RCD scope baseline",
    },
    "extension_state_source": {
        "apply_target": "EPC extension relation baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "EPC extension relation baseline",
    },
    "validation_state_source": {
        "apply_target": "EPC validation relation baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "EPC validation relation baseline",
    },
}
PCT_ONLY_REGIONAL_EP_CODES = {"BE", "CY", "FR", "GR", "IE", "LT", "LV", "MC", "ME", "MT", "NL", "SI", "SM"}
PCT_REGIONAL_SYSTEM_NAMES = {
    "AP": "ARIPO patent",
    "EA": "Eurasian patent",
    "EP": "European patent",
    "OA": "OAPI patent",
}
PCT_REGIONAL_ROUTES: dict[str, list[dict[str, str]]] = {}
for route_code in PCT_ONLY_REGIONAL_EP_CODES:
    PCT_REGIONAL_ROUTES.setdefault(route_code, []).append({"type": "regional_only", "system_code": "EP"})
for route_code in set(EPC_CODES) - PCT_ONLY_REGIONAL_EP_CODES:
    PCT_REGIONAL_ROUTES.setdefault(route_code, []).append({"type": "national_or_regional", "system_code": "EP"})
for route_code in {"SZ"}:
    PCT_REGIONAL_ROUTES.setdefault(route_code, []).append({"type": "regional_only", "system_code": "AP"})
for route_code in {"BW", "GH", "KE", "MZ", "NA", "RW", "UG", "ZM", "ZW"}:
    PCT_REGIONAL_ROUTES.setdefault(route_code, []).append({"type": "national_or_regional", "system_code": "AP"})
for route_code in {"AM", "AZ", "BY", "KG", "KZ", "RU", "TJ", "TM"}:
    PCT_REGIONAL_ROUTES.setdefault(route_code, []).append({"type": "national_or_regional", "system_code": "EA"})
for route_code in {"BF", "BJ", "CF", "CG", "CI", "CM", "GA", "GN", "GQ", "GW", "KM", "ML", "MR", "NE", "SN", "TD", "TG"}:
    PCT_REGIONAL_ROUTES.setdefault(route_code, []).append({"type": "regional_only", "system_code": "OA"})
PARIS_NON_PCT_ROUTE_CODES = {"AF", "AD", "AR", "BS", "BD", "BT", "BO", "BI", "CD", "ET", "FJ", "GY", "HT", "VA", "KI", "LB", "NP", "PK", "PY", "SR", "TO", "VE", "YE"}
EPC_EXTENSION_STATE_CODES = {"BA"}
EPC_VALIDATION_STATE_CODES = {"MA", "TN", "KH", "GE", "LA"}
EPC_HISTORICAL_EXTENSION_STATE_CODES = {"AL", "HR", "ME", "MK", "RS", "SI"}
EPC_HISTORICAL_VALIDATION_STATE_CODES = {"MD"}
HISTORICAL_RELATION_TYPES = {"historical_extension_state", "historical_validation_state"}
EPC_RELATION_EFFECTIVE_DATES = {
    "BA": date(2004, 12, 1),
    "MA": date(2015, 3, 1),
    "TN": date(2017, 12, 1),
    "KH": date(2018, 3, 1),
    "GE": date(2024, 1, 15),
    "LA": date(2025, 4, 1),
    "MD": date(2015, 11, 1),
}
REFERENCE_EXTRA_OBJECTS = [
    ("HK", "中国香港", "Hong Kong, China", "region", "地区 / 特别行政区"),
    ("MO", "中国澳门", "Macao, China", "region", "地区 / 特别行政区"),
    ("EP", "欧洲专利局", "European Patent Office", "regional_office", "区域局"),
    ("AP", "非洲地区知识产权组织", "African Regional Intellectual Property Organization", "regional_office", "区域局"),
    ("OA", "非洲知识产权组织", "African Intellectual Property Organization", "regional_office", "区域局"),
    ("EA", "欧亚专利组织", "Eurasian Patent Organization", "regional_office", "区域局"),
    ("EM", "欧盟知识产权局", "European Union Intellectual Property Office", "regional_office", "区域局"),
    ("WO", "世界知识产权组织", "World Intellectual Property Organization", "intergovernmental_org", "政府间组织"),
    ("EU", "欧洲联盟", "European Union", "intergovernmental_org", "政府间组织"),
    ("BX", "比荷卢知识产权组织", "Benelux Office for Intellectual Property", "regional_office", "区域局"),
    ("GC", "海湾合作委员会", "Gulf Cooperation Council", "intergovernmental_org", "政府间组织"),
    ("IB", "WIPO 国际局", "International Bureau of WIPO", "intergovernmental_org", "政府间组织"),
    ("XK", "科索沃", "Kosovo", "reference_object", "其他参考对象"),
    ("PS", "巴勒斯坦", "Palestine", "reference_object", "其他参考对象"),
    ("TW", "中国台湾", "Taiwan, Province of China", "region", "地区 / 特别行政区"),
    ("FO", "法罗群岛", "Faroe Islands", "region", "地区 / 特别行政区"),
    ("GL", "格陵兰", "Greenland", "region", "地区 / 特别行政区"),
    ("GI", "直布罗陀", "Gibraltar", "region", "地区 / 特别行政区"),
    ("IM", "马恩岛", "Isle of Man", "region", "地区 / 特别行政区"),
    ("JE", "泽西", "Jersey", "region", "地区 / 特别行政区"),
]
REFERENCE_SEARCH_ALIASES = {
    "HK": {
        "HK",
        "香港",
        "中國香港",
        "中国香港",
        "HONG KONG",
        "HONG KONG CHINA",
        "HONG KONG, CHINA",
    },
    "MO": {
        "MO",
        "澳门",
        "澳門",
        "中國澳門",
        "中国澳门",
        "MACAO",
        "MACAU",
        "MACAO CHINA",
        "MACAU CHINA",
        "MACAO, CHINA",
        "MACAU, CHINA",
    },
    "EU": {"EU", "欧盟", "歐盟", "欧洲联盟", "歐洲聯盟", "EUROPEAN UNION"},
}


@dataclass(frozen=True)
class OfficialMember:
    code: str
    name_en: str
    effective_date: date | None = None
    remark: str = ""
    source_url: str = ""


def list_systems(*, include_reserved: bool = False) -> list[IpSystemQuerySystem]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT system_code, system_name_cn, system_name_en, system_category,
                   source_url, official_source_name, last_verified_at, remark, display_order
            FROM ip_system_master
            ORDER BY display_order, system_code
            """
        )
        rows = [_normalize_row(row) for row in cursor.fetchall()]
    systems_by_code = {str(row["system_code"]).upper(): row for row in rows}
    p0_rows: list[dict[str, object]] = []
    for code in P0_SYSTEM_CODES:
        if code == "EU_DESIGN":
            row = dict(systems_by_code.get("EUIPO", {}))
            row["system_code"] = "EU_DESIGN"
            row["system_name_cn"] = "欧盟外观设计体系"
            row["system_name_en"] = "EU Design / Registered Community Design"
            row["system_category"] = "regional_design_system"
            row["source_url"] = EU_DESIGN_SOURCE_URL
            row["official_source_name"] = EU_DESIGN_SOURCE_NAME
            row["remark"] = "欧盟外观设计权利在欧盟成员国范围内适用。"
            p0_rows.append(row)
        elif code in systems_by_code:
            p0_rows.append(systems_by_code[code])
    systems = [_system_from_row(row, is_p0=True, is_reserved=False) for row in p0_rows]
    if include_reserved:
        reserved = [
            _system_from_row(row, is_p0=False, is_reserved=True)
            for row in rows
            if str(row.get("system_code") or "").upper() in RESERVED_SYSTEM_CODES
        ]
        systems.extend(reserved)
    return systems


def get_system_members(system_code: str) -> IpSystemMembersResponse:
    system = _get_system_by_code(system_code)
    rows = _display_member_rows(system.system_code)
    historical_rows = _historical_member_rows(system.system_code)
    master_map = _master_status_by_codes([str(row["jurisdiction_code"]) for row in rows])
    members = [_member_from_official_row(row, master_map.get(str(row["jurisdiction_code"]).upper())) for row in rows]
    historical_master_map = _master_status_by_codes([str(row["jurisdiction_code"]) for row in historical_rows])
    historical_members = [
        _member_from_official_row(row, historical_master_map.get(str(row["jurisdiction_code"]).upper()))
        for row in historical_rows
    ]
    relation_type_counts = _relation_type_counts(members)
    member_state_count = sum(
        1
        for item in members
        if _is_member_count_relation(system.system_code, item.membership_relation_type)
    )
    existing_count = sum(
        1
        for item in members
        if item.master_status in {"exists", "regional_office", "system_object"}
        and _is_member_count_relation(system.system_code, item.membership_relation_type)
    )
    return IpSystemMembersResponse(
        system=system,
        stats=IpSystemMemberStats(
            official_member_count=member_state_count,
            existing_in_master_count=existing_count,
            missing_in_master_count=member_state_count - existing_count,
            applicable_relation_count=len(members),
            relation_type_counts=relation_type_counts,
            last_checked_at=system.last_checked_at,
            source_name=system.source_name,
            source_url=system.source_url,
        ),
        overall_remark=_overall_remark(system.system_code),
        members=members,
        historical_members=historical_members,
    )


def search_jurisdictions(keyword: str) -> list[IpSystemJurisdictionOption]:
    value = keyword.strip()
    if not value:
        return []
    official_options = _search_official_members(value)
    seen_codes = {item.code.upper() for item in official_options}
    like = f"%{value}%"
    code = value.upper()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT jurisdiction_id, display_code, internal_code, name_cn, name_en, jurisdiction_type
            FROM jurisdictions
            WHERE COALESCE(is_deleted, 0) = 0
              AND is_enabled = 1
              AND (
                name_cn LIKE %s
                OR name_en LIKE %s
                OR UPPER(display_code) LIKE %s
                OR UPPER(internal_code) LIKE %s
                OR UPPER(COALESCE(wipo_st3_code, '')) LIKE %s
              )
            ORDER BY display_order, display_code
            LIMIT 30
            """,
            (like, like, f"%{code}%", f"%{code}%", f"%{code}%"),
        )
        rows = cursor.fetchall()
    options = list(official_options)
    for row in rows:
        option = _jurisdiction_option(row)
        if option.code.upper() not in seen_codes:
            options.append(option)
            seen_codes.add(option.code.upper())
    reference_options = _search_reference_objects(value)
    exact_reference_options = [
        option for option in reference_options if _is_exact_reference_query(value, option.code)
    ]
    fuzzy_reference_options = [
        option for option in reference_options if option.code not in {item.code for item in exact_reference_options}
    ]
    for option in reversed(exact_reference_options):
        option_code = option.code.upper()
        if option_code not in seen_codes:
            options.insert(0, option)
            seen_codes.add(option_code)
        else:
            options = [
                _merge_reference_option(existing, option) if existing.code.upper() == option_code else existing
                for existing in options
            ]
            options.sort(key=lambda item: 0 if item.code.upper() == option_code else 1)
    for option in fuzzy_reference_options:
        option_code = option.code.upper()
        if option_code not in seen_codes:
            options.append(option)
            seen_codes.add(option_code)
        else:
            options = [
                _merge_reference_option(existing, option) if existing.code.upper() == option_code else existing
                for existing in options
            ]
    return options[:30]


def get_jurisdiction_memberships(jurisdiction_ids: list[str]) -> list[IpSystemJurisdictionMembershipGroup]:
    return get_jurisdiction_memberships_by_codes(jurisdiction_ids=jurisdiction_ids, jurisdiction_codes=[])


def get_jurisdiction_memberships_by_codes(
    *,
    jurisdiction_ids: list[str],
    jurisdiction_codes: list[str],
) -> list[IpSystemJurisdictionMembershipGroup]:
    cleaned_ids = [item.strip() for item in jurisdiction_ids if item.strip()]
    cleaned_codes = [item.strip().upper() for item in jurisdiction_codes if item.strip()]
    if not cleaned_ids and not cleaned_codes:
        return []
    jurisdictions = _jurisdictions_by_ids(cleaned_ids)
    codes_from_ids = [
        str(item.get("display_code") or item.get("internal_code") or "").upper()
        for item in jurisdictions.values()
        if item.get("display_code") or item.get("internal_code")
    ]
    requested_codes = list(dict.fromkeys([*codes_from_ids, *cleaned_codes]))
    rows = _display_member_rows(jurisdiction_codes=requested_codes)
    rows_by_code: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        rows_by_code.setdefault(str(row["jurisdiction_code"]).upper(), []).append(row)
    master_map = _master_status_by_codes(requested_codes)
    reference_map = _reference_objects_by_code(requested_codes)
    groups: list[IpSystemJurisdictionMembershipGroup] = []
    for jurisdiction_id in cleaned_ids:
        jurisdiction = jurisdictions.get(jurisdiction_id)
        if not jurisdiction:
            continue
        code = str(jurisdiction.get("display_code") or jurisdiction.get("internal_code") or "").upper()
        master = master_map.get(code)
        reference = reference_map.get(code)
        groups.append(
            IpSystemJurisdictionMembershipGroup(
                jurisdiction_id=jurisdiction_id,
                code=code,
                name_zh=str(jurisdiction.get("name_cn") or (reference.name_zh if reference else "") or ""),
                name_en=str(jurisdiction.get("name_en") or (reference.name_en if reference else "") or ""),
                master_status=master["status"] if master else "missing",
                master_status_label=master["label"] if master else "未录入主档",
                **_reference_group_fields(reference),
                memberships=[
                    _membership_from_official_row(row)
                    for row in rows_by_code.get(code, [])
                ],
            )
        )
    grouped_existing_codes = {group.code.upper() for group in groups}
    for code in requested_codes:
        if code in grouped_existing_codes:
            continue
        code_rows = rows_by_code.get(code, [])
        reference = reference_map.get(code)
        if not code_rows and not reference:
            continue
        master = master_map.get(code)
        first = code_rows[0] if code_rows else {}
        groups.append(
            IpSystemJurisdictionMembershipGroup(
                jurisdiction_id=master.get("jurisdiction_id") if master else None,
                code=code,
                name_zh=str((first.get("name_zh") or (master.get("name_zh") if master else "") or (reference.name_zh if reference else "")) or ""),
                name_en=str((first.get("name_en") or (master.get("name_en") if master else "") or (reference.name_en if reference else "")) or ""),
                master_status=master["status"] if master else "missing",
                master_status_label=master["label"] if master else "未录入主档",
                **_reference_group_fields(reference),
                memberships=[_membership_from_official_row(row) for row in code_rows],
            )
        )
    return groups


def check_updates(system_code: str) -> IpSystemCheckUpdatesResponse:
    system = _get_system_by_code(system_code)
    normalized_code = _normalize_system_code(system.system_code)
    expected_count = len(official_baseline_members(normalized_code))
    boundary = _source_type_boundary("treaty_membership_source")
    if normalized_code not in P0_UPDATE_SYSTEM_CODES:
        return IpSystemCheckUpdatesResponse(
            system_code=normalized_code,
            checked_at=datetime.now(),
            source_url=system.source_url,
            source_name=system.source_name,
            source_type="treaty_membership_source",
            apply_target=boundary["apply_target"],
            affects_membership_count=bool(boundary["affects_membership_count"]),
            check_status="skipped",
            expected_count=expected_count,
            expected_scope=f"{normalized_code} P0 confirmed membership baseline",
            parsed_count=0,
            parsed_date_count=0,
            current_baseline_count=len(_official_member_rows(normalized_code)),
            apply_allowed=False,
            has_changes=False,
            message="该体系暂未纳入第一期官方检查更新范围。",
        )
    try:
        official_members = _fetch_official_members(system)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        parsed_count = getattr(exc, "parsed_count", None)
        return IpSystemCheckUpdatesResponse(
            system_code=normalized_code,
            checked_at=datetime.now(),
            source_url=system.source_url,
            source_name=system.source_name,
            source_type="treaty_membership_source",
            apply_target=boundary["apply_target"],
            affects_membership_count=bool(boundary["affects_membership_count"]),
            check_status="failed",
            expected_count=expected_count,
            expected_scope=f"{normalized_code} P0 confirmed membership baseline",
            parsed_count=parsed_count,
            parsed_date_count=None,
            current_baseline_count=len(_official_member_rows(normalized_code)),
            failure_reason=str(exc),
            apply_allowed=False,
            has_changes=False,
            message=f"官方来源检查失败：{exc}",
        )
    diffs = _build_update_diffs(normalized_code, official_members)
    parsed_date_count = sum(1 for member in official_members if member.effective_date is not None)
    current_count = len(_official_member_rows(normalized_code))
    summary_preview = _build_update_summary(
        system_code=normalized_code,
        source_type="treaty_membership_source",
        parsed_count=len(official_members),
        parsed_date_count=parsed_date_count,
        current_baseline_count=current_count,
        diff_counts=_diff_counts(diffs),
        written_count=None,
        written_date_count=None,
    )
    return IpSystemCheckUpdatesResponse(
        system_code=normalized_code,
        checked_at=datetime.now(),
        source_url=system.source_url,
        source_name=system.source_name,
        source_type="treaty_membership_source",
        apply_target=boundary["apply_target"],
        affects_membership_count=bool(boundary["affects_membership_count"]),
        check_status="success",
        expected_count=expected_count,
        expected_scope=f"{normalized_code} P0 confirmed membership baseline",
        parsed_count=len(official_members),
        parsed_date_count=parsed_date_count,
        current_baseline_count=current_count,
        apply_allowed=True,
        diff_summary=_diff_counts(diffs),
        has_changes=bool(diffs),
        summary_preview=summary_preview,
        message="发现变化" if diffs else "未发现变化",
        diffs=diffs,
    )


def apply_updates(
    system_code: str,
    diffs: list[IpSystemUpdateDiff],
    *,
    actor: str = "",
    source_id: str = "",
) -> IpSystemApplyUpdatesResponse:
    system = _get_system_by_code(system_code)
    normalized_code = _normalize_system_code(system.system_code)
    boundary = _source_type_boundary("treaty_membership_source")
    if normalized_code not in P0_UPDATE_SYSTEM_CODES:
        return IpSystemApplyUpdatesResponse(
            system_code=normalized_code,
            updated_count=0,
            apply_target=boundary["apply_target"],
            affects_membership_count=bool(boundary["affects_membership_count"]),
            message="该体系暂未纳入第一期官方检查更新范围。",
        )
    try:
        official_members = _fetch_official_members(system)
    except (HTTPError, URLError, TimeoutError, ValueError):
        official_members = _members_from_diffs(diffs)
    changes = _build_update_diffs(normalized_code, official_members) if official_members else diffs
    if not changes and not official_members:
        summary = "未发现变化"
        _mark_system_apply_success(normalized_code, summary)
        _record_update_history(
            source_id=source_id,
            system_code=normalized_code,
            source_name=system.source_name,
            source_type="treaty_membership_source",
            operation="apply",
            update_type="membership_baseline",
            update_count=0,
            parsed_count=0,
            parsed_date_count=0,
            written_date_count=0,
            system_summary=summary,
            actor=actor,
            status="success",
        )
        return IpSystemApplyUpdatesResponse(
            system_code=normalized_code,
            updated_count=0,
            parsed_count=0,
            parsed_date_count=0,
            written_date_count=0,
            apply_target=boundary["apply_target"],
            affects_membership_count=bool(boundary["affects_membership_count"]),
            summary=summary,
            message=summary,
        )
    members_to_write = official_members or _members_from_diffs(changes)
    updated_count = 0
    written_date_count = 0
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "ip_system_official_members"):
            raise KeyError("IP_SYSTEM_OFFICIAL_BASELINE_NOT_FOUND")
        _ensure_official_member_lightweight_columns(cursor)
        for diff in changes:
            if diff.change_type == "removed_member":
                cursor.execute(
                    """
                    UPDATE ip_system_official_members
                    SET is_confirmed = 0, remark = %s
                    WHERE system_code = %s AND jurisdiction_code = %s
                    """,
                    ("官方来源检查：成员已删除。", normalized_code, diff.code),
                )
        for index, member in enumerate(members_to_write, start=1):
            name_zh, fallback_name_en = COUNTRY_NAMES.get(member.code.upper(), ("", ""))
            cursor.execute(
                """
                INSERT INTO ip_system_official_members (
                  system_code, jurisdiction_code, name_zh, name_en, member_type,
                  membership_relation_type, effective_date, source_name, source_url, remark,
                  is_confirmed, display_order
                )
                VALUES (%s, %s, %s, %s, 'country', %s, %s, %s, %s, %s, 1, 1000)
                ON DUPLICATE KEY UPDATE
                  name_en = VALUES(name_en),
                  membership_relation_type = VALUES(membership_relation_type),
                  effective_date = COALESCE(VALUES(effective_date), effective_date),
                  source_url = VALUES(source_url),
                  remark = VALUES(remark),
                  is_confirmed = 1
                """,
                (
                    normalized_code,
                    member.code.upper(),
                    name_zh,
                    member.name_en or fallback_name_en,
                    _default_membership_relation_type(normalized_code),
                    member.effective_date,
                    system.source_name,
                    member.source_url or system.source_url,
                    member.remark,
                ),
            )
            updated_count += 1
            if member.effective_date is not None:
                written_date_count += 1
    diff_counts = _diff_counts(changes)
    parsed_date_count = sum(1 for member in members_to_write if member.effective_date is not None)
    summary = _build_update_summary(
        system_code=normalized_code,
        source_type="treaty_membership_source",
        parsed_count=len(members_to_write),
        parsed_date_count=parsed_date_count,
        current_baseline_count=None,
        diff_counts=diff_counts,
        written_count=updated_count,
        written_date_count=written_date_count,
    )
    message = summary
    _mark_system_apply_success(normalized_code, summary)
    _record_update_history(
        source_id=source_id,
        system_code=normalized_code,
        source_name=system.source_name,
        source_type="treaty_membership_source",
        operation="apply",
        update_type="membership_baseline",
        update_count=updated_count,
        parsed_count=len(members_to_write),
        parsed_date_count=parsed_date_count,
        written_date_count=written_date_count,
        system_summary=summary,
        actor=actor,
        status="success",
    )
    return IpSystemApplyUpdatesResponse(
        system_code=normalized_code,
        updated_count=updated_count,
        parsed_count=len(members_to_write),
        parsed_date_count=parsed_date_count,
        written_date_count=written_date_count,
        apply_target=boundary["apply_target"],
        affects_membership_count=bool(boundary["affects_membership_count"]),
        summary=summary,
        message=message,
    )


def list_data_sources(system_code: str | None = None) -> list[IpSystemDataSource]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_data_source_table(cursor)
        params: list[object] = []
        where = ""
        if system_code:
            where = "WHERE UPPER(system_code) = %s"
            params.append(_normalize_system_code(system_code))
        cursor.execute(
            f"""
            SELECT id, system_code, source_name, source_type, source_url, purpose_note,
                   is_enabled, last_checked_at, last_success_at, last_check_status,
                   last_check_message, last_check_summary, last_update_summary,
                   admin_update_note, created_at, updated_at
            FROM ip_system_data_source
            {where}
            ORDER BY FIELD(system_code, 'PCT', 'PARIS', 'EPC', 'EU_DESIGN'),
                     system_code, source_type, source_name
            """,
            tuple(params),
        )
        rows = [_normalize_row(row) for row in cursor.fetchall()]
    return [_data_source_from_row(row) for row in rows]


def create_data_source(payload: IpSystemDataSourceCreate) -> IpSystemDataSource:
    system_code = _normalize_system_code(payload.system_code)
    if system_code != "REFERENCE":
        _get_system_by_code(system_code)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_data_source_table(cursor)
        source_id = f"ipds-{uuid4().hex}"
        cursor.execute(
            """
            INSERT INTO ip_system_data_source (
              id, system_code, source_name, source_type, source_url, purpose_note, is_enabled
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                source_id,
                system_code,
                payload.source_name.strip(),
                payload.source_type.strip(),
                payload.source_url.strip(),
                payload.purpose_note.strip(),
                1 if payload.is_enabled else 0,
            ),
        )
    return get_data_source(source_id)


def update_data_source(source_id: str, payload: IpSystemDataSourceUpdate) -> IpSystemDataSource:
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return get_data_source(source_id)
    allowed = {
        "system_code",
        "source_name",
        "source_type",
        "source_url",
        "purpose_note",
        "is_enabled",
        "last_update_summary",
        "admin_update_note",
    }
    assignments: list[str] = []
    params: list[object] = []
    for key, value in values.items():
        if key not in allowed:
            continue
        if key == "system_code" and value is not None:
            value = _normalize_system_code(str(value))
            if value != "REFERENCE":
                _get_system_by_code(str(value))
        if key == "is_enabled":
            value = 1 if value else 0
        assignments.append(f"{key} = %s")
        params.append(value)
    if not assignments:
        return get_data_source(source_id)
    params.append(source_id)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_data_source_table(cursor)
        cursor.execute(
            f"UPDATE ip_system_data_source SET {', '.join(assignments)} WHERE id = %s",
            tuple(params),
        )
        if cursor.rowcount == 0:
            raise KeyError(source_id)
    return get_data_source(source_id)


def get_data_source(source_id: str) -> IpSystemDataSource:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_data_source_table(cursor)
        cursor.execute(
            """
            SELECT id, system_code, source_name, source_type, source_url, purpose_note,
                   is_enabled, last_checked_at, last_success_at, last_check_status,
                   last_check_message, last_check_summary, last_update_summary,
                   admin_update_note, created_at, updated_at
            FROM ip_system_data_source
            WHERE id = %s
            LIMIT 1
            """,
            (source_id,),
        )
        row = cursor.fetchone()
    if not row:
        raise KeyError(source_id)
    return _data_source_from_row(_normalize_row(row))


def check_data_source_updates(source_id: str) -> IpSystemCheckUpdatesResponse:
    source = get_data_source(source_id)
    boundary = _source_type_boundary(source.source_type)
    if source.source_type != "treaty_membership_source":
        baseline_items = _non_membership_baseline_items(source)
        parsed_count = len(baseline_items)
        current_count = _non_membership_baseline_count(source)
        summary = _build_non_membership_summary(
            source=source,
            parsed_count=parsed_count,
            current_count=current_count,
            written_count=None,
        )
        result = IpSystemCheckUpdatesResponse(
            system_code=source.system_code,
            source_id=source.id,
            checked_at=datetime.now(),
            source_url=source.source_url,
            source_name=source.source_name,
            source_type=source.source_type,
            apply_target=str(boundary["apply_target"]),
            affects_membership_count=bool(boundary["affects_membership_count"]),
            check_status="success",
            expected_count=202 if source.source_type == "reference_source" else None,
            expected_scope=str(boundary["expected_scope_suffix"] or source.purpose_note),
            parsed_count=parsed_count,
            parsed_date_count=sum(1 for item in baseline_items if item.get("effective_date")),
            current_baseline_count=current_count,
            apply_allowed=True,
            has_changes=parsed_count != current_count,
            summary_preview=summary,
            message=summary,
            diffs=[],
        )
    else:
        result = check_updates(source.system_code)
        result.source_id = source.id
    summary = result.summary_preview or (_diff_summary(result.diffs) if result.diffs else result.message)
    status = "failed" if result.check_status == "failed" else ("changed" if result.has_changes else "success")
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_data_source_table(cursor)
        cursor.execute(
            """
            UPDATE ip_system_data_source
            SET last_checked_at = %s,
                last_check_status = %s,
                last_check_message = %s,
                last_check_summary = %s
            WHERE id = %s
            """,
            (
                result.checked_at,
                status,
                result.message,
                summary,
                source_id,
            ),
        )
    return result


def apply_data_source_updates(
    source_id: str,
    diffs: list[IpSystemUpdateDiff],
    *,
    actor: str = "",
) -> IpSystemApplyUpdatesResponse:
    source = get_data_source(source_id)
    if source.source_type != "treaty_membership_source":
        result = _apply_non_membership_source(source, actor=actor)
    else:
        result = apply_updates(source.system_code, diffs, actor=actor, source_id=source.id)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_data_source_table(cursor)
        cursor.execute(
            """
            UPDATE ip_system_data_source
            SET last_success_at = NOW(),
                last_update_summary = %s
            WHERE id = %s
            """,
            (result.summary or result.message, source_id),
        )
    return result


def list_update_history(source_id: str | None = None, limit: int = 50) -> list[IpSystemUpdateHistoryItem]:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_update_history_table(cursor)
        params: list[object] = []
        where = ""
        if source_id:
            where = "WHERE source_id = %s"
            params.append(source_id)
        params.append(max(1, min(limit, 1000)))
        cursor.execute(
            f"""
            SELECT id, source_id, system_code, source_name, source_type, operation,
                   update_type, update_count, parsed_count, parsed_date_count,
                   written_date_count, system_summary, admin_note, actor, status,
                   failure_reason, created_at
            FROM ip_system_update_history
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            tuple(params),
        )
        rows = [_normalize_row(row) for row in cursor.fetchall()]
    return [_history_from_row(row) for row in rows]


def _diff_summary(diffs: list[IpSystemUpdateDiff]) -> str:
    if not diffs:
        return "未发现变化"
    counts: dict[str, int] = {}
    for diff in diffs:
        counts[diff.change_type] = counts.get(diff.change_type, 0) + 1
    parts = [f"{diffLabels} {count}" for diffLabels, count in (
        ("新增", counts.get("added_member", 0)),
        ("删除", counts.get("removed_member", 0)),
        ("日期变化", counts.get("effective_date_changed", 0)),
        ("备注变化", counts.get("remark_changed", 0)),
        ("来源变化", counts.get("source_changed", 0)),
    ) if count]
    return "；".join(parts) or f"发现 {len(diffs)} 项变化"


def _source_type_boundary(source_type: str) -> dict[str, object]:
    return SOURCE_TYPE_BOUNDARIES.get(source_type, {
        "apply_target": "reference/scope baseline",
        "affects_membership_count": False,
        "expected_scope_suffix": "non-membership baseline",
    })


def _build_update_summary(
    *,
    system_code: str,
    source_type: str,
    parsed_count: int,
    parsed_date_count: int,
    current_baseline_count: int | None,
    diff_counts: dict[str, int],
    written_count: int | None,
    written_date_count: int | None,
) -> str:
    boundary = _source_type_boundary(source_type)
    parts = [
        f"本次检查解析 {system_code} 成员数据 {parsed_count} 条",
        f"解析到日期 {parsed_date_count} 条",
        f"新增 {diff_counts.get('added_member', 0)} 条",
        f"删除 {diff_counts.get('removed_member', 0)} 条",
        f"补齐/更新日期 {diff_counts.get('effective_date_changed', 0)} 条",
        f"更新官方备注 {diff_counts.get('remark_changed', 0)} 条",
        f"更新来源 {diff_counts.get('source_changed', 0)} 条",
    ]
    if current_baseline_count is not None:
        parts.append(f"当前基准数量 {current_baseline_count} 条")
    if written_count is not None:
        parts.append(f"确认后写入 {boundary['apply_target']} {written_count} 条")
    if written_date_count is not None:
        parts.append(f"实际写入日期 {written_date_count} 条")
    parts.append("影响成员计数" if boundary["affects_membership_count"] else "不影响成员计数")
    return "；".join(parts)


def _build_non_membership_summary(
    *,
    source: IpSystemDataSource,
    parsed_count: int,
    current_count: int | None,
    written_count: int | None,
) -> str:
    boundary = _source_type_boundary(source.source_type)
    parts = [
        f"本次检查解析 {source.source_type} {parsed_count} 条",
        f"确认后将写入 {boundary['apply_target']}",
        "不写正式成员数据",
        "不影响成员计数",
    ]
    if current_count is not None:
        parts.append(f"当前基准数量 {current_count} 条")
    if written_count is not None:
        parts.append(f"确认后写入 {written_count} 条")
    return "；".join(parts)


def _members_from_diffs(diffs: list[IpSystemUpdateDiff]) -> list[OfficialMember]:
    members: dict[str, OfficialMember] = {}
    for diff in diffs:
        if diff.change_type == "removed_member":
            continue
        code = diff.code.upper()
        current = members.get(code)
        members[code] = OfficialMember(
            code=code,
            name_en=diff.name_en or (current.name_en if current else ""),
            effective_date=diff.new_effective_date or (current.effective_date if current else None),
            remark=diff.new_remark or (current.remark if current else ""),
            source_url=diff.new_source_url or (current.source_url if current else ""),
        )
    return list(members.values())


def _diff_counts(diffs: list[IpSystemUpdateDiff]) -> dict[str, int]:
    counts = {
        "added_member": 0,
        "removed_member": 0,
        "effective_date_changed": 0,
        "remark_changed": 0,
        "source_changed": 0,
    }
    for diff in diffs:
        counts[diff.change_type] = counts.get(diff.change_type, 0) + 1
    return counts


def _non_membership_baseline_items(source: IpSystemDataSource) -> list[dict[str, object]]:
    source_type = source.source_type
    if source_type == "reference_source":
        return [
            {
                "baseline_kind": "reference_object",
                "system_code": "REFERENCE",
                "object_code": item.code,
                "object_name_zh": item.name_zh,
                "object_name_en": item.name_en,
                "object_type": item.object_type,
                "relation_type": "",
                "route_type": "",
                "regional_system_code": "",
                "system_hint": item.system_hint,
                "profile_url": item.profile_url,
                "effective_date": None,
            }
            for item in list_reference_objects().objects
        ]
    if source_type == "regional_route_source":
        items: list[dict[str, object]] = []
        for code, routes in sorted(PCT_REGIONAL_ROUTES.items()):
            name_zh, name_en = COUNTRY_NAMES.get(code, (code, code))
            for route in routes:
                items.append({
                    "baseline_kind": "pct_regional_route",
                    "system_code": "PCT",
                    "object_code": code,
                    "object_name_zh": name_zh,
                    "object_name_en": name_en,
                    "object_type": "country",
                    "relation_type": "",
                    "route_type": route["type"],
                    "regional_system_code": route["system_code"],
                    "system_hint": _short_route_text(route["type"], route["system_code"]),
                    "profile_url": "",
                    "effective_date": None,
                })
        return items
    if source_type == "paris_non_pct_route_source":
        return [
            {
                "baseline_kind": "paris_non_pct_route",
                "system_code": "PARIS",
                "object_code": code,
                "object_name_zh": COUNTRY_NAMES.get(code, (code, code))[0],
                "object_name_en": COUNTRY_NAMES.get(code, (code, code))[1],
                "object_type": "country",
                "relation_type": "paris_contracting_party",
                "route_type": "paris_only_non_pct",
                "regional_system_code": "",
                "system_hint": PCT_ROUTE_LABELS["paris_only_non_pct"],
                "profile_url": "",
                "effective_date": None,
            }
            for code in sorted(PARIS_NON_PCT_ROUTE_CODES)
        ]
    if source_type == "design_scope_source":
        return [
            {
                "baseline_kind": "eu_design_scope",
                "system_code": "EU_DESIGN",
                "object_code": code,
                "object_name_zh": COUNTRY_NAMES.get(code, (code, code))[0],
                "object_name_en": COUNTRY_NAMES.get(code, (code, code))[1],
                "object_type": "country",
                "relation_type": "covered_state",
                "route_type": "",
                "regional_system_code": "EU",
                "system_hint": "欧盟外观设计权利按欧盟成员资格在欧盟成员国范围内适用。",
                "profile_url": "",
                "effective_date": None,
            }
            for code in EU_MEMBER_CODES
        ]
    if source_type in {"extension_state_source", "validation_state_source"}:
        wanted = "extension_state" if source_type == "extension_state_source" else "validation_state"
        return [
            {
                "baseline_kind": wanted,
                "system_code": "EPC",
                "object_code": str(row["jurisdiction_code"]),
                "object_name_zh": str(row["name_zh"]),
                "object_name_en": str(row["name_en"]),
                "object_type": str(row["member_type"]),
                "relation_type": wanted,
                "route_type": "",
                "regional_system_code": "EP",
                "system_hint": _membership_relation_type_label(wanted),
                "profile_url": "",
                "effective_date": row.get("effective_date"),
            }
            for row in _epc_relation_reference_rows(include_historical=False)
            if str(row["membership_relation_type"]) == wanted
        ]
    return []


def _non_membership_baseline_count(source: IpSystemDataSource) -> int | None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_non_membership_baseline_table(cursor)
        cursor.execute(
            """
            SELECT COUNT(*) AS item_count
            FROM ip_system_non_membership_baseline
            WHERE source_id = %s AND is_active = 1
            """,
            (source.id,),
        )
        row = cursor.fetchone()
    return int(row["item_count"] or 0) if row else 0


def _apply_non_membership_source(source: IpSystemDataSource, *, actor: str = "") -> IpSystemApplyUpdatesResponse:
    boundary = _source_type_boundary(source.source_type)
    items = _non_membership_baseline_items(source)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_non_membership_baseline_table(cursor)
        cursor.execute(
            "UPDATE ip_system_non_membership_baseline SET is_active = 0 WHERE source_id = %s",
            (source.id,),
        )
        for item in items:
            cursor.execute(
                """
                INSERT INTO ip_system_non_membership_baseline (
                  source_id, source_type, system_code, object_code, object_name_zh,
                  object_name_en, object_type, baseline_kind, relation_type, route_type,
                  regional_system_code, system_hint, profile_url, source_name, source_url,
                  effective_date, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                  object_name_zh = VALUES(object_name_zh),
                  object_name_en = VALUES(object_name_en),
                  object_type = VALUES(object_type),
                  route_type = VALUES(route_type),
                  regional_system_code = VALUES(regional_system_code),
                  system_hint = VALUES(system_hint),
                  profile_url = VALUES(profile_url),
                  source_name = VALUES(source_name),
                  source_url = VALUES(source_url),
                  effective_date = VALUES(effective_date),
                  is_active = 1
                """,
                (
                    source.id,
                    source.source_type,
                    item["system_code"],
                    item["object_code"],
                    item["object_name_zh"],
                    item["object_name_en"],
                    item["object_type"],
                    item["baseline_kind"],
                    item["relation_type"],
                    item["route_type"],
                    item["regional_system_code"],
                    item["system_hint"],
                    item["profile_url"],
                    source.source_name,
                    source.source_url,
                    item["effective_date"],
                ),
            )
    summary = _build_non_membership_summary(
        source=source,
        parsed_count=len(items),
        current_count=None,
        written_count=len(items),
    )
    _record_update_history(
        source_id=source.id,
        system_code=source.system_code,
        source_name=source.source_name,
        source_type=source.source_type,
        operation="apply",
        update_type=str(boundary["apply_target"]),
        update_count=len(items),
        parsed_count=len(items),
        parsed_date_count=sum(1 for item in items if item.get("effective_date")),
        written_date_count=sum(1 for item in items if item.get("effective_date")),
        system_summary=summary,
        actor=actor,
        status="success",
    )
    return IpSystemApplyUpdatesResponse(
        system_code=source.system_code,
        updated_count=len(items),
        parsed_count=len(items),
        parsed_date_count=sum(1 for item in items if item.get("effective_date")),
        written_date_count=sum(1 for item in items if item.get("effective_date")),
        apply_target=str(boundary["apply_target"]),
        affects_membership_count=bool(boundary["affects_membership_count"]),
        summary=summary,
        message=summary,
    )


def update_member_remark(
    system_code: str,
    jurisdiction_code: str,
    payload: IpSystemMemberRemarkUpdate,
    user_email: str,
) -> IpSystemQueryMember:
    normalized_system = _normalize_system_code(system_code)
    normalized_code = jurisdiction_code.strip().upper()
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "ip_system_official_members"):
            raise KeyError("IP_SYSTEM_OFFICIAL_BASELINE_NOT_FOUND")
        _ensure_official_member_lightweight_columns(cursor)
        cursor.execute(
            """
            UPDATE ip_system_official_members
            SET internal_remark = %s,
                remark_updated_at = NOW(),
                remark_updated_by = %s
            WHERE system_code = %s
              AND jurisdiction_code = %s
              AND is_confirmed = 1
            """,
            (payload.internal_remark.strip(), user_email, normalized_system, normalized_code),
        )
        if cursor.rowcount == 0:
            raise KeyError(jurisdiction_code)
    rows = _display_member_rows(normalized_system, jurisdiction_codes=[normalized_code])
    if not rows:
        raise KeyError(jurisdiction_code)
    master = _master_status_by_codes([normalized_code]).get(normalized_code)
    return _member_from_official_row(rows[0], master)


def list_reference_objects() -> IpSystemReferenceObjectsResponse:
    objects_by_code: dict[str, dict[str, str]] = {}
    for code, names in COUNTRY_NAMES.items():
        objects_by_code[code] = {
            "code": code,
            "name_zh": names[0],
            "name_en": names[1],
            "object_type": "country",
            "object_type_label": "国家",
        }
    for code, name_zh, name_en, object_type, object_type_label in REFERENCE_EXTRA_OBJECTS:
        objects_by_code[code] = {
            "code": code,
            "name_zh": name_zh,
            "name_en": name_en,
            "object_type": object_type,
            "object_type_label": object_type_label,
        }
    ordered_codes = sorted(objects_by_code)
    master_map = _master_status_by_codes(ordered_codes)
    pct_codes = {member.jurisdiction_code for member in official_baseline_members("PCT")}
    paris_codes = {member.jurisdiction_code for member in official_baseline_members("PARIS")}
    epc_codes = {member.jurisdiction_code for member in official_baseline_members("EPC")}
    eu_design_codes = {member.jurisdiction_code for member in official_baseline_members("EU_DESIGN")}
    reference_baseline = _reference_baseline_by_code()
    current_epc_relation_by_code = {
        str(row["jurisdiction_code"]): str(row["membership_relation_type"])
        for row in _epc_relation_reference_rows(include_historical=False)
    }
    objects: list[IpSystemReferenceObject] = []
    for index, code in enumerate(ordered_codes, start=1):
        item = objects_by_code[code]
        epc_relation = "epc_member_state" if code in epc_codes else current_epc_relation_by_code.get(code, "")
        hint = _reference_object_hint(
            code=code,
            object_type=item["object_type"],
            is_pct=code in pct_codes,
            is_paris=code in paris_codes,
            epc_relation=epc_relation,
            is_eu_design=code in eu_design_codes,
        )
        master = master_map.get(code)
        objects.append(IpSystemReferenceObject(
            sequence_no=index,
            name_zh=item["name_zh"],
            name_en=item["name_en"],
            code=code,
            object_type=item["object_type"],
            object_type_label=item["object_type_label"],
            master_status=master["status"] if master else "missing",
            master_status_label=master["label"] if master else "未录入主档",
            is_pct_contracting_state=code in pct_codes,
            is_paris_contracting_party=code in paris_codes,
            epc_relation_type=epc_relation,
            epc_relation_type_label=_membership_relation_type_label(epc_relation) if epc_relation else "否",
            is_eu_design_covered=code in eu_design_codes,
            system_hint=hint,
            profile_url=f"{WIPO_LEX_MEMBERS_SOURCE_URL}/{code.lower()}" if len(code) == 2 else WIPO_LEX_MEMBERS_SOURCE_URL,
            internal_remark=reference_baseline.get(code, ""),
        ))
    return IpSystemReferenceObjectsResponse(
        source_name="WIPO Lex 管辖区/组织参考名录",
        source_type="reference_source",
        source_url=WIPO_LEX_MEMBERS_SOURCE_URL,
        reference_count=202,
        objects=objects,
    )


def _reference_objects_by_code(codes: list[str] | None = None) -> dict[str, IpSystemReferenceObject]:
    wanted = {code.strip().upper() for code in (codes or []) if code.strip()}
    objects = list_reference_objects().objects
    return {
        item.code.upper(): item
        for item in objects
        if not wanted or item.code.upper() in wanted
    }


def _search_reference_objects(keyword: str) -> list[IpSystemJurisdictionOption]:
    value = keyword.strip()
    if not value:
        return []
    normalized = _normalize_reference_search_text(value)
    matches: list[tuple[int, str, IpSystemJurisdictionOption]] = []
    for item in list_reference_objects().objects:
        aliases = REFERENCE_SEARCH_ALIASES.get(item.code.upper(), set())
        normalized_aliases = {_normalize_reference_search_text(alias) for alias in aliases}
        normalized_code = _normalize_reference_search_text(item.code)
        normalized_name_zh = _normalize_reference_search_text(item.name_zh)
        normalized_name_en = _normalize_reference_search_text(item.name_en)
        haystack = {
            normalized_code,
            normalized_name_zh,
            normalized_name_en,
            _normalize_reference_search_text(item.object_type_label),
            *normalized_aliases,
        }
        if not any(normalized and normalized in candidate for candidate in haystack):
            continue
        if normalized == normalized_code or normalized in normalized_aliases:
            score = 0
        elif normalized in {normalized_name_zh, normalized_name_en}:
            score = 1
        else:
            score = 2
        matches.append((score, item.code, _reference_option(item)))
    return [option for _, _, option in sorted(matches, key=lambda item: (item[0], item[1]))[:30]]


def _reference_option(item: IpSystemReferenceObject) -> IpSystemJurisdictionOption:
    return IpSystemJurisdictionOption(
        jurisdiction_id=None,
        code=item.code,
        name_zh=item.name_zh,
        name_en=item.name_en,
        member_type=item.object_type,
        master_status=item.master_status,
        master_status_label=item.master_status_label,
        matched_system_codes=[],
        **_reference_group_fields(item),
    )


def _merge_reference_option(
    option: IpSystemJurisdictionOption,
    reference_option: IpSystemJurisdictionOption,
) -> IpSystemJurisdictionOption:
    data = option.model_dump()
    reference_data = reference_option.model_dump()
    for key in (
        "has_reference_object",
        "object_type",
        "object_type_label",
        "reference_source_name",
        "reference_profile_url",
        "reference_system_hint",
        "is_pct_contracting_state",
        "is_paris_contracting_party",
        "epc_relation_type_label",
        "is_eu_design_covered",
    ):
        data[key] = reference_data.get(key)
    if not data.get("name_zh"):
        data["name_zh"] = reference_data.get("name_zh", "")
    if not data.get("name_en"):
        data["name_en"] = reference_data.get("name_en", "")
    if not data.get("member_type"):
        data["member_type"] = reference_data.get("member_type", "")
    return IpSystemJurisdictionOption(**data)


def _is_exact_reference_query(keyword: str, code: str) -> bool:
    normalized = _normalize_reference_search_text(keyword)
    normalized_code = code.upper()
    aliases = {
        _normalize_reference_search_text(alias)
        for alias in REFERENCE_SEARCH_ALIASES.get(normalized_code, set())
    }
    return normalized == _normalize_reference_search_text(normalized_code) or normalized in aliases


def _reference_group_fields(item: IpSystemReferenceObject | None) -> dict[str, object]:
    if item is None:
        return {}
    return {
        "has_reference_object": True,
        "object_type": item.object_type,
        "object_type_label": item.object_type_label,
        "reference_source_name": "WIPO Lex 参考对象",
        "reference_profile_url": item.profile_url,
        "reference_system_hint": item.system_hint,
        "is_pct_contracting_state": item.is_pct_contracting_state,
        "is_paris_contracting_party": item.is_paris_contracting_party,
        "epc_relation_type_label": item.epc_relation_type_label,
        "is_eu_design_covered": item.is_eu_design_covered,
    }


def _normalize_reference_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    return re.sub(r"[\s,，、/／()（）.-]+", "", normalized)


def _reference_object_hint(
    *,
    code: str,
    object_type: str,
    is_pct: bool,
    is_paris: bool,
    epc_relation: str,
    is_eu_design: bool,
) -> str:
    if code == "HK":
        return "可作为报价管辖区/地区对象；未作为独立 PCT 或 Paris 缔约对象展示，具体保护路径需按香港本地制度确认。"
    if is_paris and not is_pct and code in PARIS_NON_PCT_ROUTE_CODES:
        return "仅巴黎路径 / 非 PCT。"
    if object_type != "country":
        return "WIPO Lex 参考对象；不直接生成条约成员关系，需按对应本地或区域制度确认。"
    if not any([is_pct, is_paris, epc_relation, is_eu_design]):
        return "WIPO Lex 参考对象；当前未在 PCT / Paris / EPC / EU Design 正式数据中显示独立关系。"
    return ""


def _reference_baseline_by_code() -> dict[str, str]:
    try:
        with mysql.connection_scope() as connection, connection.cursor() as cursor:
            _ensure_non_membership_baseline_table(cursor)
            cursor.execute(
                """
                SELECT object_code, internal_remark
                FROM ip_system_non_membership_baseline
                WHERE source_type = 'reference_source'
                  AND is_active = 1
                """
            )
            rows = cursor.fetchall()
    except Exception:
        return {}
    return {
        str(row["object_code"]).upper(): str(row.get("internal_remark") or "")
        for row in rows
    }


def _confirmed_relation_rows(
    *,
    system_code: str | None = None,
    jurisdiction_ids: list[str] | None = None,
) -> list[dict[str, object]]:
    where_parts = [
        "r.is_active = 1",
        "(r.effective_date IS NULL OR r.effective_date <= CURDATE())",
        "(r.expiry_date IS NULL OR r.expiry_date >= CURDATE())",
        "j.is_enabled = 1",
        "COALESCE(j.is_deleted, 0) = 0",
        "s.is_active = 1",
    ]
    params: list[object] = []
    if system_code:
        where_parts.append("s.system_code = %s")
        params.append(system_code)
    if jurisdiction_ids:
        placeholders = ", ".join(["%s"] * len(jurisdiction_ids))
        where_parts.append(f"r.jurisdiction_id IN ({placeholders})")
        params.extend(jurisdiction_ids)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT r.relation_id, r.jurisdiction_id, r.effective_date,
                   r.source_reference, r.source_official_name, r.source_official_code,
                   r.verification_status, r.special_statement, r.admin_remark,
                   r.data_quality_flags_json,
                   j.display_code AS jurisdiction_code,
                   j.name_cn AS jurisdiction_name_cn,
                   j.name_en AS jurisdiction_name_en,
                   s.system_code, s.system_name_cn, s.system_name_en,
                   rt.relation_type_name_cn
            FROM jurisdiction_ip_system_relation r
            JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            JOIN ip_system_master s ON s.system_id = r.system_id
            JOIN ip_system_relation_type rt ON rt.relation_type_id = r.relation_type_id
            WHERE {" AND ".join(where_parts)}
            ORDER BY s.display_order, j.display_order, j.display_code
            LIMIT 1000
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
    return [_normalize_row(row) for row in rows if _is_confirmed_row(row)]


def _is_confirmed_row(row: dict[str, object]) -> bool:
    status = str(row.get("verification_status") or "").strip().lower()
    if status in UNCONFIRMED_VERIFICATION_STATUSES:
        return False
    flags = _flags(row.get("data_quality_flags_json"))
    return not (flags & UNCONFIRMED_FLAGS)


def _build_update_diffs(system_code: str, official_members: list[OfficialMember]) -> list[IpSystemUpdateDiff]:
    current_rows = _official_member_rows(system_code)
    current_by_code = {str(row.get("jurisdiction_code") or "").upper(): row for row in current_rows}
    official_by_code = {item.code.upper(): item for item in official_members if item.code}
    diffs: list[IpSystemUpdateDiff] = []
    for code, member in sorted(official_by_code.items()):
        current = current_by_code.get(code)
        if not current:
            diffs.append(IpSystemUpdateDiff(
                change_type="added_member",
                code=code,
                name_en=member.name_en,
                new_effective_date=member.effective_date,
                new_remark=member.remark,
                new_source_url=member.source_url,
            ))
            continue
        current_effective = current.get("effective_date")
        current_remark = _relation_remark(current)
        current_source = str(current.get("source_url") or current.get("source_reference") or "")
        if current_effective != member.effective_date:
            diffs.append(IpSystemUpdateDiff(
                change_type="effective_date_changed",
                code=code,
                name_zh=str(current.get("name_zh") or ""),
                name_en=member.name_en or str(current.get("name_en") or ""),
                old_effective_date=current_effective,
                new_effective_date=member.effective_date,
                old_source_url=current_source,
                new_source_url=member.source_url,
            ))
        if current_remark != member.remark:
            diffs.append(IpSystemUpdateDiff(
                change_type="remark_changed",
                code=code,
                name_zh=str(current.get("name_zh") or ""),
                name_en=member.name_en or str(current.get("name_en") or ""),
                old_remark=current_remark,
                new_remark=member.remark,
                old_source_url=current_source,
                new_source_url=member.source_url,
            ))
        if member.source_url and current_source and current_source != member.source_url:
            diffs.append(IpSystemUpdateDiff(
                change_type="source_changed",
                code=code,
                name_zh=str(current.get("name_zh") or ""),
                name_en=member.name_en or str(current.get("name_en") or ""),
                old_source_url=current_source,
                new_source_url=member.source_url,
            ))
    for code, current in sorted(current_by_code.items()):
        if code not in official_by_code:
            diffs.append(IpSystemUpdateDiff(
                change_type="removed_member",
                code=code,
                name_zh=str(current.get("name_zh") or ""),
                name_en=str(current.get("name_en") or ""),
                old_effective_date=current.get("effective_date"),
                old_remark=_relation_remark(current),
                old_source_url=str(current.get("source_url") or current.get("source_reference") or ""),
            ))
    return diffs


def _official_member_rows(
    system_code: str | None = None,
    *,
    jurisdiction_codes: list[str] | None = None,
) -> list[dict[str, object]]:
    baseline_rows = _official_baseline_rows(system_code, jurisdiction_codes=jurisdiction_codes)
    where_parts = ["is_confirmed = 1"]
    params: list[object] = []
    if system_code:
        where_parts.append("system_code = %s")
        params.append(_normalize_system_code(system_code))
    else:
        placeholders = ", ".join(["%s"] * len(P0_SYSTEM_CODES))
        where_parts.append(f"system_code IN ({placeholders})")
        params.extend(P0_SYSTEM_CODES)
    if jurisdiction_codes:
        placeholders = ", ".join(["%s"] * len(jurisdiction_codes))
        where_parts.append(f"UPPER(jurisdiction_code) IN ({placeholders})")
        params.extend([code.upper() for code in jurisdiction_codes])
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "ip_system_official_members"):
            return baseline_rows
        cursor.execute(
            f"""
            SELECT *
            FROM ip_system_official_members
            WHERE {" AND ".join(where_parts)}
            ORDER BY FIELD(system_code, 'PCT', 'PARIS', 'EPC', 'EU_DESIGN'),
                     display_order, jurisdiction_code
            """,
            tuple(params),
        )
        db_rows = [_normalize_row(row) for row in cursor.fetchall()]
    allowed_keys = {
        (member.system_code.upper(), member.jurisdiction_code.upper())
        for member in official_baseline_members(system_code)
    }
    if allowed_keys:
        db_rows = [
            row
            for row in db_rows
            if (
                str(row.get("system_code") or "").upper(),
                str(row.get("jurisdiction_code") or "").upper(),
            ) in allowed_keys
        ]
    if not baseline_rows:
        return db_rows
    db_by_key = {
        (str(row.get("system_code") or "").upper(), str(row.get("jurisdiction_code") or "").upper()): row
        for row in db_rows
    }
    merged: list[dict[str, object]] = []
    for baseline_row in baseline_rows:
        key = (
            str(baseline_row.get("system_code") or "").upper(),
            str(baseline_row.get("jurisdiction_code") or "").upper(),
        )
        db_row = db_by_key.get(key)
        if db_row:
            merged_row = dict(db_row)
            if not merged_row.get("effective_date") and baseline_row.get("effective_date"):
                merged_row["effective_date"] = baseline_row.get("effective_date")
            if _is_system_level_repeated_remark(str(merged_row.get("system_code") or ""), str(merged_row.get("remark") or "")):
                merged_row["remark"] = ""
            merged.append(merged_row)
        else:
            merged.append(baseline_row)
    baseline_keys = {
        (str(row.get("system_code") or "").upper(), str(row.get("jurisdiction_code") or "").upper())
        for row in baseline_rows
    }
    for row in db_rows:
        key = (str(row.get("system_code") or "").upper(), str(row.get("jurisdiction_code") or "").upper())
        if key not in baseline_keys:
            merged.append(row)
    return merged


def _display_member_rows(
    system_code: str | None = None,
    *,
    jurisdiction_codes: list[str] | None = None,
) -> list[dict[str, object]]:
    rows = _official_member_rows(system_code, jurisdiction_codes=jurisdiction_codes)
    normalized = _normalize_system_code(system_code or "") if system_code else ""
    if normalized == "EPC" or (not normalized and jurisdiction_codes):
        rows.extend(_epc_relation_reference_rows(jurisdiction_codes=jurisdiction_codes, include_historical=False))
    return rows


def _historical_member_rows(system_code: str) -> list[dict[str, object]]:
    if _normalize_system_code(system_code) != "EPC":
        return []
    return _epc_relation_reference_rows(jurisdiction_codes=None, include_historical=True)


def _official_baseline_rows(
    system_code: str | None = None,
    *,
    jurisdiction_codes: list[str] | None = None,
) -> list[dict[str, object]]:
    allowed_codes = {code.upper() for code in jurisdiction_codes or []}
    rows: list[dict[str, object]] = []
    for member in official_baseline_members(system_code):
        if allowed_codes and member.jurisdiction_code.upper() not in allowed_codes:
            continue
        remark = "" if _is_system_level_repeated_remark(member.system_code, member.remark) else member.remark
        if member.effective_date is None and member.system_code != "EU_DESIGN":
            remark = remark or "加入/生效日期待官方检查更新确认。"
        rows.append({
            "system_code": member.system_code,
            "jurisdiction_code": member.jurisdiction_code,
            "name_zh": member.name_zh,
            "name_en": member.name_en,
            "member_type": member.member_type,
            "effective_date": member.effective_date,
            "source_name": member.source_name,
            "source_url": member.source_url,
            "remark": remark,
            "membership_relation_type": _default_membership_relation_type(member.system_code),
            "is_confirmed": 1,
            "display_order": member.display_order,
        })
    return rows


def _is_system_level_repeated_remark(system_code: str, remark: str) -> bool:
    normalized = _normalize_system_code(system_code)
    value = remark.strip()
    if normalized == "EU_DESIGN" and value in {
        "按欧盟成员资格适用。",
        "按欧盟成员资格适用；欧盟外观设计权利在欧盟成员国范围内适用。",
    }:
        return True
    return False


def _epc_relation_reference_rows(
    *,
    jurisdiction_codes: list[str] | None = None,
    include_historical: bool = False,
) -> list[dict[str, object]]:
    allowed = {code.upper() for code in jurisdiction_codes or []}
    rows: list[dict[str, object]] = []
    relation_sets = [
        ("extension_state", EPC_EXTENSION_STATE_CODES, "EPO Extension States", "EPC 延伸国；也可通过 Euro-PCT 进入欧洲阶段后请求延伸，具体以 EPO 规则及当地法为准。"),
        ("validation_state", EPC_VALIDATION_STATE_CODES, "EPO Validation States", "EPC 生效国；也可通过 Euro-PCT 进入欧洲阶段后请求生效，具体以 EPO 规则及当地法为准。"),
    ]
    if include_historical:
        relation_sets.extend([
            ("historical_extension_state", EPC_HISTORICAL_EXTENSION_STATE_CODES, "EPO Extension States", "仅对特定历史日期前/期间的申请可能有意义；当前新案不作为可选路径。"),
            ("historical_validation_state", EPC_HISTORICAL_VALIDATION_STATE_CODES, "EPO Validation States", "仅对特定历史日期前/期间的申请可能有意义；当前新案不作为可选路径。"),
        ])
    display_order = 5000
    for relation_type, codes, source_name, remark in relation_sets:
        for code in sorted(codes):
            if allowed and code not in allowed:
                continue
            name_zh, name_en = COUNTRY_NAMES.get(code, (code, code))
            rows.append({
                "system_code": "EPC",
                "jurisdiction_code": code,
                "name_zh": name_zh,
                "name_en": name_en,
                "member_type": "country",
                "effective_date": EPC_RELATION_EFFECTIVE_DATES.get(code),
                "source_name": source_name,
                "source_url": EPC_SOURCE_URL,
                "remark": remark,
                "membership_relation_type": relation_type,
                "is_historical_relation": relation_type in HISTORICAL_RELATION_TYPES,
                "is_confirmed": 1,
                "display_order": display_order,
            })
            display_order += 10
    return rows


def _search_official_members(keyword: str) -> list[IpSystemJurisdictionOption]:
    value = keyword.strip()
    lowered = value.lower()
    code = value.upper()
    grouped: dict[str, dict[str, object]] = {}
    for row in _official_member_rows():
        row_code = str(row.get("jurisdiction_code") or "").upper()
        name_zh = str(row.get("name_zh") or "")
        name_en = str(row.get("name_en") or "")
        if lowered not in name_zh.lower() and lowered not in name_en.lower() and code not in row_code:
            continue
        grouped.setdefault(row_code, {
            "jurisdiction_code": row_code,
            "name_zh": name_zh,
            "name_en": name_en,
            "member_type": str(row.get("member_type") or "country"),
            "system_codes": [],
        })
        grouped[row_code]["system_codes"].append(str(row.get("system_code") or ""))
    rows = sorted(grouped.values(), key=lambda row: str(row["jurisdiction_code"]))[:30]
    master_map = _master_status_by_codes([str(row["jurisdiction_code"]) for row in rows])
    options: list[IpSystemJurisdictionOption] = []
    for row in rows:
        code_value = str(row["jurisdiction_code"]).upper()
        master = master_map.get(code_value)
        options.append(
            IpSystemJurisdictionOption(
                jurisdiction_id=master.get("jurisdiction_id") if master else None,
                code=code_value,
                name_zh=str((row.get("name_zh") or (master.get("name_zh") if master else "")) or ""),
                name_en=str((row.get("name_en") or (master.get("name_en") if master else "")) or ""),
                member_type=str(row.get("member_type") or "country"),
                master_status=master["status"] if master else "missing",
                master_status_label=master["label"] if master else "未录入主档",
                matched_system_codes=list(dict.fromkeys(row.get("system_codes") or [])),
            )
        )
    return options


def _member_from_official_row(row: dict[str, object], master: dict[str, str] | None) -> IpSystemQueryMember:
    status = _status_for_member_type(str(row.get("member_type") or ""), master)
    system_code = str(row.get("system_code") or "")
    relation_type = str(row.get("membership_relation_type") or _default_membership_relation_type(system_code))
    route = _route_hint(str(row.get("jurisdiction_code") or ""), system_code, relation_type)
    internal_remark = _clean_public_remark(str(row.get("internal_remark") or ""))
    return IpSystemQueryMember(
        name_zh=str((row.get("name_zh") or (master.get("name_zh") if master else "")) or ""),
        name_en=str((row.get("name_en") or (master.get("name_en") if master else "")) or ""),
        code=str(row.get("jurisdiction_code") or ""),
        effective_date=row.get("effective_date"),
        date_label="加入/生效/适用时间",
        member_type=str(row.get("member_type") or "country"),
        master_status=status["status"],
        master_status_label=status["label"],
        membership_relation_type=relation_type,
        membership_relation_type_label=_membership_relation_type_label(relation_type),
        pct_route_type=str(route.get("pct_route_type") or ""),
        pct_route_type_label=str(route.get("pct_route_type_label") or ""),
        regional_system_code=str(route.get("regional_system_code") or ""),
        regional_system_name=str(route.get("regional_system_name") or ""),
        route_remark=str(route.get("route_remark") or ""),
        is_historical_relation=bool(row.get("is_historical_relation")),
        internal_remark=internal_remark,
        remark_updated_at=row.get("remark_updated_at"),
        remark_updated_by=str(row.get("remark_updated_by") or ""),
        remark=str(row.get("remark") or ""),
    )


def _membership_from_official_row(row: dict[str, object]) -> IpSystemJurisdictionMembership:
    system_code = str(row.get("system_code") or "")
    relation_type = str(row.get("membership_relation_type") or _default_membership_relation_type(system_code))
    route = _route_hint(str(row.get("jurisdiction_code") or ""), system_code, relation_type)
    return IpSystemJurisdictionMembership(
        system_code=system_code,
        system_name_zh=_system_display_value(system_code, "name_zh", system_code),
        system_name_en=str(row.get("system_name_en") or ""),
        short_name=_system_display_value(system_code, "short_name", system_code),
        effective_date=row.get("effective_date"),
        membership_relation_type=relation_type,
        membership_relation_type_label=_membership_relation_type_label(relation_type),
        pct_route_type=str(route.get("pct_route_type") or ""),
        pct_route_type_label=str(route.get("pct_route_type_label") or ""),
        regional_system_code=str(route.get("regional_system_code") or ""),
        regional_system_name=str(route.get("regional_system_name") or ""),
        route_remark=str(route.get("route_remark") or ""),
        is_historical_relation=bool(row.get("is_historical_relation")),
        internal_remark=_clean_public_remark(str(row.get("internal_remark") or "")),
        remark=str(row.get("remark") or ""),
    )


def _default_membership_relation_type(system_code: str) -> str:
    normalized = _normalize_system_code(system_code)
    if normalized == "PCT":
        return "pct_contracting_state"
    if normalized == "PARIS":
        return "paris_contracting_party"
    if normalized == "EPC":
        return "epc_member_state"
    if normalized == "EU_DESIGN":
        return "covered_state"
    return "member_state"


def _membership_relation_type_label(value: str) -> str:
    return MEMBERSHIP_RELATION_LABELS.get(value, value or "-")


def _route_hint(code: str, system_code: str, relation_type: str) -> dict[str, str]:
    normalized = _normalize_system_code(system_code)
    normalized_code = code.upper()
    if normalized == "PCT" and relation_type == "pct_contracting_state":
        routes = PCT_REGIONAL_ROUTES.get(normalized_code, [])
        if not routes:
            return {}
        route_types = [item["type"] for item in routes]
        route_type = "regional_only" if "regional_only" in route_types else route_types[0]
        system_codes = [item["system_code"] for item in routes]
        remarks = [_short_route_text(route["type"], route["system_code"]) for route in routes]
        return {
            "pct_route_type": route_type,
            "pct_route_type_label": " / ".join(remarks),
            "regional_system_code": " / ".join(system_codes),
            "regional_system_name": " / ".join(PCT_REGIONAL_SYSTEM_NAMES.get(code, code) for code in system_codes),
            "route_remark": "",
        }
    if normalized == "PARIS" and relation_type == "paris_contracting_party":
        if normalized_code not in PARIS_NON_PCT_ROUTE_CODES:
            return {}
        return {
            "pct_route_type": "paris_only_non_pct",
            "pct_route_type_label": PCT_ROUTE_LABELS["paris_only_non_pct"],
            "regional_system_code": "",
            "regional_system_name": "",
            "route_remark": "",
        }
    return {}


def _short_route_text(route_type: str, regional_system_code: str) -> str:
    template = PCT_ROUTE_LABELS.get(route_type, route_type)
    return template.format(system=regional_system_code) if "{system}" in template else template


def _overall_remark(system_code: str) -> str:
    normalized = _normalize_system_code(system_code)
    if normalized == "EU_DESIGN":
        return "欧盟外观设计权利按欧盟成员资格在欧盟成员国范围内适用。"
    return ""


def _is_member_count_relation(system_code: str, relation_type: str) -> bool:
    normalized = _normalize_system_code(system_code)
    if normalized == "EPC":
        return relation_type == "epc_member_state"
    return relation_type in {"pct_contracting_state", "paris_contracting_party", "covered_state", "member_state"}


def _relation_type_counts(members: list[IpSystemQueryMember]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for member in members:
        counts[member.membership_relation_type] = counts.get(member.membership_relation_type, 0) + 1
    return counts


def _master_status_by_codes(codes: list[str]) -> dict[str, dict[str, str]]:
    cleaned_codes = list(dict.fromkeys([code.strip().upper() for code in codes if code.strip()]))
    if not cleaned_codes:
        return {}
    placeholders = ", ".join(["%s"] * len(cleaned_codes))
    result: dict[str, dict[str, str]] = {}
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT jurisdiction_id, display_code, internal_code, wipo_st3_code, iso_alpha2,
                   name_cn, name_en, jurisdiction_type
            FROM jurisdictions
            WHERE COALESCE(is_deleted, 0) = 0
              AND is_enabled = 1
              AND (
                UPPER(display_code) IN ({placeholders})
                OR UPPER(internal_code) IN ({placeholders})
                OR UPPER(COALESCE(wipo_st3_code, '')) IN ({placeholders})
                OR UPPER(COALESCE(iso_alpha2, '')) IN ({placeholders})
              )
            """,
            tuple(cleaned_codes * 4),
        )
        rows = [_normalize_row(row) for row in cursor.fetchall()]
        for row in rows:
            status = _status_for_jurisdiction_type(str(row.get("jurisdiction_type") or ""))
            for key in ("display_code", "internal_code", "wipo_st3_code", "iso_alpha2"):
                code = str(row.get(key) or "").upper()
                if code:
                    result[code] = {
                        "jurisdiction_id": str(row.get("jurisdiction_id") or ""),
                        "name_zh": str(row.get("name_cn") or ""),
                        "name_en": str(row.get("name_en") or ""),
                        **status,
                    }
        if _table_exists(cursor, "countries"):
            cursor.execute(
                f"""
                SELECT code, name_cn, name_en
                FROM countries
                WHERE enabled = 1
                  AND UPPER(code) IN ({placeholders})
                """,
                tuple(cleaned_codes),
            )
            for row in cursor.fetchall():
                code = str(row.get("code") or "").upper()
                result.setdefault(code, {
                    "jurisdiction_id": "",
                    "name_zh": str(row.get("name_cn") or ""),
                    "name_en": str(row.get("name_en") or ""),
                    "status": "exists",
                    "label": "已存在本报价系统",
                })
    return result


def _status_for_member_type(member_type: str, master: dict[str, str] | None) -> dict[str, str]:
    if member_type == "regional_office":
        return {"status": "regional_office", "label": "区域局"}
    if member_type in {"organization", "system_object"}:
        return {"status": "system_object", "label": "系统对象"}
    if master:
        return {"status": master["status"], "label": master["label"]}
    return {"status": "missing", "label": "未录入主档"}


def _status_for_jurisdiction_type(jurisdiction_type: str) -> dict[str, str]:
    if jurisdiction_type == "regional_office":
        return {"status": "regional_office", "label": "区域局"}
    if jurisdiction_type in {"international_organization", "treaty_entry"}:
        return {"status": "system_object", "label": "系统对象"}
    return {"status": "exists", "label": "已录入主档"}


def _fetch_official_members(system: IpSystemQuerySystem) -> list[OfficialMember]:
    if not system.source_url:
        raise ValueError("未配置官方来源地址")
    request = Request(system.source_url, headers={"User-Agent": "quote-system-ip-query/1.0"})
    with urlopen(request, timeout=20) as response:
        content = response.read().decode("utf-8", errors="ignore")
    normalized = _normalize_system_code(system.system_code)
    if normalized == "PCT":
        members = _parse_pct_members(content, system.source_url)
    elif normalized == "PARIS":
        members = _parse_paris_members(content, system.source_url)
    elif normalized == "EPC":
        members = _parse_epc_members(content, system.source_url)
    elif normalized == "EU_DESIGN":
        members = _parse_eu_design_members(content, system.source_url)
    else:
        raise ValueError("该体系没有专用官方解析器")
    allowed_codes = {member.jurisdiction_code.upper() for member in official_baseline_members(normalized)}
    if allowed_codes:
        members = [member for member in members if member.code.upper() in allowed_codes]
    if normalized == "PCT":
        today = date.today()
        members = [member for member in members if member.effective_date is None or member.effective_date <= today]
    min_expected = {"PCT": 150, "PARIS": 170, "EPC": 40, "EU_DESIGN": 27}.get(normalized, 1)
    if len(members) < min_expected:
        error = ValueError(f"官方来源解析结果不足，解析到 {len(members)} 条，预期至少 {min_expected} 条")
        setattr(error, "parsed_count", len(members))
        raise error
    return members


def _html_table_text_rows(html: str) -> list[list[str]]:
    parser = _TableTextParser()
    parser.feed(html)
    return parser.rows


def _parse_pct_members(html: str, source_url: str) -> list[OfficialMember]:
    return _members_from_rows(_html_table_text_rows(html), source_url)


def _parse_epc_members(html: str, source_url: str) -> list[OfficialMember]:
    rows = _html_table_text_rows(html_lib.unescape(html))
    allowed = set(EPC_CODES)
    members = _members_from_rows(rows, source_url, allowed_codes=allowed)
    if len(members) < len(allowed):
        members_by_code = {member.code: member for member in members}
        for seed in official_baseline_members("EPC"):
            members_by_code.setdefault(seed.jurisdiction_code, OfficialMember(
                code=seed.jurisdiction_code,
                name_en=seed.name_en,
                effective_date=seed.effective_date,
                remark="",
                source_url=source_url,
            ))
        members = list(members_by_code.values())
    return [member for member in members if member.code in allowed]


def _parse_eu_design_members(html: str, source_url: str) -> list[OfficialMember]:
    return [
        OfficialMember(
            code=seed.jurisdiction_code,
            name_en=seed.name_en,
            effective_date=None,
            remark="",
            source_url=source_url,
        )
        for seed in official_baseline_members("EU_DESIGN")
        if seed.jurisdiction_code in set(EU_MEMBER_CODES)
    ]


def _parse_paris_members(html: str, source_url: str) -> list[OfficialMember]:
    rows = _html_table_text_rows(html_lib.unescape(html))
    by_name = _member_name_code_map("PARIS")
    members: list[OfficialMember] = []
    for row in rows:
        text_values = [item.strip() for item in row if item.strip()]
        if len(text_values) < 2:
            continue
        name = text_values[0]
        code = by_name.get(_normalize_member_name(name), "")
        if not code:
            continue
        effective = _in_force_date_from_cells(text_values[1:])
        members.append(OfficialMember(
            code=code,
            name_en=name,
            effective_date=effective,
            remark="",
            source_url=source_url,
        ))
    if members:
        return _dedupe_members(members)
    for row_html in re.findall(r"<tr\b.*?</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        code_match = re.search(r"/remarks/([A-Z]{2})/2", row_html)
        if not code_match:
            continue
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip()
            for cell in re.findall(r"<td\b.*?</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
        ]
        if not cells:
            continue
        name = cells[0]
        if not _looks_like_member_name(name):
            continue
        effective = None
        for cell in cells[1:4]:
            effective = _extract_date(cell)
            if effective:
                break
        members.append(OfficialMember(
            code=code_match.group(1),
            name_en=name,
            effective_date=effective,
            remark="",
            source_url=source_url,
        ))
    return _dedupe_members(members)


def _members_from_rows(
    rows: list[list[str]],
    source_url: str,
    *,
    allowed_codes: set[str] | None = None,
) -> list[OfficialMember]:
    members: list[OfficialMember] = []
    by_name = _member_name_code_map("")
    for row in rows:
        text_values = [item.strip() for item in row if item.strip()]
        if not text_values:
            continue
        joined = " | ".join(text_values)
        code = _extract_code(joined) or by_name.get(_normalize_member_name(text_values[0]), "")
        if not code:
            continue
        if allowed_codes is not None and code not in allowed_codes:
            continue
        effective = _extract_date(joined)
        name = text_values[0]
        if not _looks_like_member_name(name):
            continue
        members.append(OfficialMember(code=code, name_en=name, effective_date=effective, remark="", source_url=source_url))
    return _dedupe_members(members)


def _in_force_date_from_cells(cells: list[str]) -> date | None:
    fallback: date | None = None
    for cell in cells:
        effective = _extract_date(cell)
        if not effective:
            continue
        fallback = effective
        lowered = cell.lower()
        if not any(token in lowered for token in ("accession", "ratification", "signature", "declaration", "notification")):
            return effective
    return fallback


def _member_name_code_map(system_code: str) -> dict[str, str]:
    codes = official_baseline_members(system_code or None)
    result: dict[str, str] = {}
    for seed in codes:
        for name in {seed.name_en, COUNTRY_NAMES.get(seed.jurisdiction_code, ("", ""))[1]}:
            normalized = _normalize_member_name(name)
            if normalized:
                result[normalized] = seed.jurisdiction_code
    aliases = {
        "bolivia plurinational state of": "BO",
        "brunei darussalam": "BN",
        "cabo verde": "CV",
        "cote d ivoire": "CI",
        "côte d ivoire": "CI",
        "czechia": "CZ",
        "czech republic": "CZ",
        "democratic people s republic of korea": "KP",
        "iran islamic republic of": "IR",
        "lao people s democratic republic": "LA",
        "netherlands kingdom of the": "NL",
        "republic of korea": "KR",
        "republic of moldova": "MD",
        "russian federation": "RU",
        "saint vincent and the grenadines": "VC",
        "sao tome and principe": "ST",
        "syrian arab republic": "SY",
        "türkiye": "TR",
        "turkiye": "TR",
        "united republic of tanzania": "TZ",
        "united states of america": "US",
        "venezuela bolivarian republic of": "VE",
        "viet nam": "VN",
    }
    result.update(aliases)
    return result


def _normalize_member_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", html_lib.unescape(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def _members_from_text(text: str, source_url: str) -> list[OfficialMember]:
    members: list[OfficialMember] = []
    for line in re.split(r"[\n\r]+", re.sub(r"<[^>]+>", "\n", text)):
        clean = re.sub(r"\s+", " ", line).strip()
        if len(clean) < 4:
            continue
        code = _extract_code(clean)
        if not code:
            continue
        members.append(OfficialMember(code=code, name_en=clean, effective_date=_extract_date(clean), source_url=source_url))
    return _dedupe_members(members)


def _dedupe_members(members: list[OfficialMember]) -> list[OfficialMember]:
    result: dict[str, OfficialMember] = {}
    for member in members:
        result.setdefault(member.code.upper(), member)
    return list(result.values())


def _looks_like_member_name(value: str) -> bool:
    lowered = value.lower()
    blocked = {
        "ai tools",
        "spdx-license-identifier",
        "liferay",
        "javascript",
        "skip to main content",
        "patentscope",
        "global brand database",
    }
    return bool(value and not any(item in lowered for item in blocked))


def _extract_code(value: str) -> str:
    parenthesized = re.search(r"\(([A-Z]{2})\)", value)
    if parenthesized:
        return parenthesized.group(1)
    tokens = re.findall(r"\b[A-Z]{2}\b", value)
    excluded = {"IP", "EU", "UN", "PC"}
    for token in tokens:
        if token not in excluded:
            return token
    return ""


def _extract_date(value: str) -> date | None:
    match = re.search(r"\b(18|19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b", value)
    if match:
        normalized = match.group(0).replace("/", "-").replace(".", "-")
        try:
            return date.fromisoformat("-".join(part.zfill(2) for part in normalized.split("-")))
        except ValueError:
            return None
    month_names = "January February March April May June July August September October November December".split()
    month_map = {name: index for index, name in enumerate(month_names, start=1)}
    month_pattern = "|".join(month_names)
    month_first = re.search(rf"\b({month_pattern})\s+(\d{{1,2}}),?\s+((?:18|19|20)\d{{2}})\b", value)
    day_first = re.search(rf"\b(\d{{1,2}})\s+({month_pattern})\s+((?:18|19|20)\d{{2}})\b", value)
    try:
        if month_first:
            return date(int(month_first.group(3)), month_map[month_first.group(1)], int(month_first.group(2)))
        if day_first:
            return date(int(day_first.group(3)), month_map[day_first.group(2)], int(day_first.group(1)))
    except ValueError:
        return None
    return None


def _get_system_by_code(system_code: str) -> IpSystemQuerySystem:
    normalized = _normalize_system_code(system_code)
    if normalized not in P0_SYSTEM_CODES and normalized not in RESERVED_SYSTEM_CODES and normalized != "EUIPO":
        raise KeyError(system_code)
    lookup_code = "EUIPO" if normalized == "EU_DESIGN" else normalized
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT system_code, system_name_cn, system_name_en, system_category,
                   source_url, official_source_name, last_verified_at, remark, display_order
            FROM ip_system_master
            WHERE UPPER(system_code) = %s
            LIMIT 1
            """,
            (lookup_code,),
        )
        row = cursor.fetchone()
    if not row:
        raise KeyError(system_code)
    row = _normalize_row(row)
    if normalized == "EU_DESIGN":
        row["system_code"] = "EU_DESIGN"
        row["system_name_cn"] = "欧盟外观设计体系"
        row["system_name_en"] = "EU Design / Registered Community Design"
        row["system_category"] = "regional_design_system"
        row["source_url"] = EU_DESIGN_SOURCE_URL
        row["official_source_name"] = EU_DESIGN_SOURCE_NAME
        row["remark"] = "欧盟外观设计权利在欧盟成员国范围内适用。"
    return _system_from_row(
        row,
        is_p0=normalized in P0_SYSTEM_CODES or normalized == "EUIPO",
        is_reserved=normalized in RESERVED_SYSTEM_CODES,
    )


def _system_from_row(row: dict[str, object], *, is_p0: bool = True, is_reserved: bool = False) -> IpSystemQuerySystem:
    system_code = str(row.get("system_code") or "")
    baseline_source_name, baseline_source_url = official_baseline_source(system_code)
    source_url = baseline_source_url or str(row.get("source_url") or "")
    last_checked = row.get("last_checked_at") or row.get("last_verified_at")
    return IpSystemQuerySystem(
        system_code=system_code,
        name_zh=_system_display_value(system_code, "name_zh", str(row.get("system_name_cn") or "")),
        name_en=str(row.get("system_name_en") or ""),
        short_name=_system_display_value(system_code, "short_name", system_code),
        category=str(row.get("system_category") or ""),
        source_url=source_url,
        source_name=baseline_source_name or str(row.get("official_source_name") or ""),
        last_checked_at=last_checked,
        remark=_clean_public_remark(str(row.get("remark") or "")),
        is_p0=is_p0,
        is_reserved=is_reserved,
    )


def _system_display_value(system_code: str, key: str, fallback: str) -> str:
    return SYSTEM_DISPLAY_OVERRIDES.get(_normalize_system_code(system_code), {}).get(key, fallback)


def _jurisdictions_by_ids(jurisdiction_ids: list[str]) -> dict[str, dict[str, object]]:
    if not jurisdiction_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(jurisdiction_ids))
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT jurisdiction_id, display_code, internal_code, name_cn, name_en, jurisdiction_type
            FROM jurisdictions
            WHERE jurisdiction_id IN ({placeholders})
              AND COALESCE(is_deleted, 0) = 0
              AND is_enabled = 1
            """,
            tuple(jurisdiction_ids),
        )
        rows = cursor.fetchall()
    return {str(row["jurisdiction_id"]): _normalize_row(row) for row in rows}


def _jurisdiction_option(row: dict[str, object]) -> IpSystemJurisdictionOption:
    status = _status_for_jurisdiction_type(str(row.get("jurisdiction_type") or ""))
    return IpSystemJurisdictionOption(
        jurisdiction_id=str(row.get("jurisdiction_id") or ""),
        code=str(row.get("display_code") or row.get("internal_code") or ""),
        name_zh=str(row.get("name_cn") or ""),
        name_en=str(row.get("name_en") or ""),
        member_type=_member_type(str(row.get("jurisdiction_type") or "")),
        master_status=status["status"],
        master_status_label=status["label"],
    )


def _relation_type_id(cursor: object, system_code: str) -> str:
    relation_type_code = RELATION_TYPE_BY_SYSTEM.get(_normalize_system_code(system_code), "MEMBER_STATE")
    cursor.execute(
        "SELECT relation_type_id FROM ip_system_relation_type WHERE relation_type_code = %s LIMIT 1",
        (relation_type_code,),
    )
    row = cursor.fetchone()
    if not row:
        raise KeyError(relation_type_code)
    return str(row["relation_type_id"])


def _system_id(cursor: object, system_code: str) -> str:
    cursor.execute("SELECT system_id FROM ip_system_master WHERE system_code = %s LIMIT 1", (system_code,))
    row = cursor.fetchone()
    if not row:
        raise KeyError(system_code)
    return str(row["system_id"])


def _jurisdiction_by_code(cursor: object, code: str) -> dict[str, object] | None:
    cursor.execute(
        """
        SELECT jurisdiction_id, display_code, name_cn, name_en
        FROM jurisdictions
        WHERE COALESCE(is_deleted, 0) = 0
          AND is_enabled = 1
          AND (
            UPPER(display_code) = %s
            OR UPPER(internal_code) = %s
            OR UPPER(COALESCE(wipo_st3_code, '')) = %s
            OR UPPER(COALESCE(iso_alpha2, '')) = %s
          )
        ORDER BY display_order
        LIMIT 1
        """,
        (code.upper(), code.upper(), code.upper(), code.upper()),
    )
    row = cursor.fetchone()
    return _normalize_row(row) if row else None


def _relation_id(cursor: object, system_code: str, jurisdiction_id: str, relation_type_id: str) -> str | None:
    cursor.execute(
        """
        SELECT r.relation_id
        FROM jurisdiction_ip_system_relation r
        JOIN ip_system_master s ON s.system_id = r.system_id
        WHERE s.system_code = %s
          AND r.jurisdiction_id = %s
          AND r.relation_type_id = %s
        LIMIT 1
        """,
        (system_code, jurisdiction_id, relation_type_id),
    )
    row = cursor.fetchone()
    return str(row["relation_id"]) if row else None


def _mark_system_apply_success(system_code: str, summary: str) -> None:
    lookup_code = "EUIPO" if _normalize_system_code(system_code) == "EU_DESIGN" else _normalize_system_code(system_code)
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE ip_system_master SET last_verified_at = NOW() WHERE system_code = %s",
            (lookup_code,),
        )
        if _table_exists(cursor, "ip_system_source_config"):
            cursor.execute(
                """
                UPDATE ip_system_source_config sc
                JOIN ip_system_master s ON s.system_id = sc.system_id
                SET sc.last_success_at = NOW()
                WHERE s.system_code = %s
                  AND sc.is_active = 1
                """,
                (lookup_code,),
            )
        if _table_exists(cursor, "ip_system_data_source"):
            cursor.execute(
                """
                UPDATE ip_system_data_source
                SET last_success_at = NOW(),
                    last_update_summary = %s
                WHERE system_code = %s
                  AND source_type = 'treaty_membership_source'
                  AND is_enabled = 1
                """,
                (summary, _normalize_system_code(system_code)),
            )


def _record_update_history(
    *,
    source_id: str,
    system_code: str,
    source_name: str,
    source_type: str,
    operation: str,
    update_type: str,
    update_count: int,
    parsed_count: int | None,
    parsed_date_count: int | None,
    written_date_count: int | None,
    system_summary: str,
    actor: str,
    status: str,
    failure_reason: str = "",
) -> None:
    with mysql.connection_scope() as connection, connection.cursor() as cursor:
        _ensure_update_history_table(cursor)
        cursor.execute(
            """
            INSERT INTO ip_system_update_history (
              source_id, system_code, source_name, source_type, operation,
              update_type, update_count, parsed_count, parsed_date_count,
              written_date_count, system_summary, actor, status, failure_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                source_id,
                system_code,
                source_name,
                source_type,
                operation,
                update_type,
                update_count,
                parsed_count,
                parsed_date_count,
                written_date_count,
                system_summary,
                actor,
                status,
                failure_reason,
            ),
        )


def _business_domain(system_code: str) -> str:
    normalized = _normalize_system_code(system_code)
    if normalized in {"HAGUE", "EUIPO", "EU_DESIGN"}:
        return "design"
    if normalized == "PARIS":
        return "general_ip"
    return "patent"


def _member_type(jurisdiction_type: str) -> str:
    mapping = {
        "single_country": "country",
        "region": "region",
        "regional_office": "regional_office",
        "international_organization": "organization",
        "treaty_entry": "organization",
    }
    return mapping.get(jurisdiction_type, jurisdiction_type or "country")


def _relation_remark(row: dict[str, object]) -> str:
    return _clean_public_remark(str(row.get("remark") or row.get("admin_remark") or row.get("special_statement") or ""))


def _clean_public_remark(value: str) -> str:
    blocked = [
        "pending_review",
        "sample_only",
        "needs_official_confirmation",
        "Reference",
        "candidate",
        "batch",
        "match_exception",
    ]
    if any(item.lower() in value.lower() for item in blocked):
        return ""
    return value


def _flags(value: object) -> set[str]:
    if value in (None, ""):
        return set()
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return set()
        try:
            import json

            parsed = json.loads(stripped)
        except ValueError:
            return {item.strip() for item in stripped.split(",") if item.strip()}
        if isinstance(parsed, list):
            return {str(item).strip() for item in parsed if str(item).strip()}
    return {str(value)}


def _normalize_row(row: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, bytes):
            normalized[key] = value.decode("utf-8")
        else:
            normalized[key] = value
    return normalized


def _table_exists(cursor: object, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        LIMIT 1
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor: object, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None


def _ensure_data_source_table(cursor: object) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ip_system_data_source (
          id VARCHAR(64) PRIMARY KEY,
          system_code VARCHAR(50) NOT NULL,
          source_name VARCHAR(150) NOT NULL,
          source_type VARCHAR(50) NOT NULL,
          source_url VARCHAR(500) NOT NULL DEFAULT '',
          purpose_note VARCHAR(1000) NOT NULL DEFAULT '',
          is_enabled TINYINT(1) NOT NULL DEFAULT 1,
          last_checked_at DATETIME NULL,
          last_success_at DATETIME NULL,
          last_check_status VARCHAR(50) NOT NULL DEFAULT '',
          last_check_message VARCHAR(1000) NOT NULL DEFAULT '',
          last_check_summary VARCHAR(1000) NOT NULL DEFAULT '',
          last_update_summary VARCHAR(1000) NOT NULL DEFAULT '',
          admin_update_note VARCHAR(1000) NOT NULL DEFAULT '',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          KEY idx_ip_system_data_source_system (system_code, is_enabled),
          KEY idx_ip_system_data_source_type (source_type, is_enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    for column_name, column_def in [
        ("last_check_status", "VARCHAR(50) NOT NULL DEFAULT ''"),
        ("last_check_message", "VARCHAR(1000) NOT NULL DEFAULT ''"),
        ("last_check_summary", "VARCHAR(1000) NOT NULL DEFAULT ''"),
        ("admin_update_note", "VARCHAR(1000) NOT NULL DEFAULT ''"),
    ]:
        if not _column_exists(cursor, "ip_system_data_source", column_name):
            cursor.execute(f"ALTER TABLE ip_system_data_source ADD COLUMN {column_name} {column_def}")
    _seed_default_data_sources(cursor)


def _ensure_non_membership_baseline_table(cursor: object) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ip_system_non_membership_baseline (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          source_id VARCHAR(64) NOT NULL DEFAULT '',
          source_type VARCHAR(50) NOT NULL DEFAULT '',
          system_code VARCHAR(50) NOT NULL DEFAULT '',
          object_code VARCHAR(20) NOT NULL DEFAULT '',
          object_name_zh VARCHAR(150) NOT NULL DEFAULT '',
          object_name_en VARCHAR(200) NOT NULL DEFAULT '',
          object_type VARCHAR(50) NOT NULL DEFAULT '',
          baseline_kind VARCHAR(80) NOT NULL DEFAULT '',
          relation_type VARCHAR(80) NOT NULL DEFAULT '',
          route_type VARCHAR(80) NOT NULL DEFAULT '',
          regional_system_code VARCHAR(50) NOT NULL DEFAULT '',
          system_hint VARCHAR(1000) NOT NULL DEFAULT '',
          profile_url VARCHAR(500) NOT NULL DEFAULT '',
          source_name VARCHAR(150) NOT NULL DEFAULT '',
          source_url VARCHAR(500) NOT NULL DEFAULT '',
          internal_remark VARCHAR(1000) NOT NULL DEFAULT '',
          effective_date DATE NULL,
          is_active TINYINT(1) NOT NULL DEFAULT 1,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          UNIQUE KEY uk_ip_non_membership_baseline (
            source_id, source_type, system_code, object_code, baseline_kind,
            relation_type, route_type, regional_system_code
          ),
          KEY idx_ip_non_membership_source (source_id, is_active),
          KEY idx_ip_non_membership_object (object_code, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def _ensure_update_history_table(cursor: object) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ip_system_update_history (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          source_id VARCHAR(64) NOT NULL DEFAULT '',
          system_code VARCHAR(50) NOT NULL DEFAULT '',
          source_name VARCHAR(150) NOT NULL DEFAULT '',
          source_type VARCHAR(50) NOT NULL DEFAULT '',
          operation VARCHAR(50) NOT NULL DEFAULT '',
          update_type VARCHAR(120) NOT NULL DEFAULT '',
          update_count INT NOT NULL DEFAULT 0,
          parsed_count INT NULL,
          parsed_date_count INT NULL,
          written_date_count INT NULL,
          system_summary VARCHAR(2000) NOT NULL DEFAULT '',
          admin_note VARCHAR(1000) NOT NULL DEFAULT '',
          actor VARCHAR(255) NOT NULL DEFAULT '',
          status VARCHAR(50) NOT NULL DEFAULT '',
          failure_reason VARCHAR(1000) NOT NULL DEFAULT '',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          KEY idx_ip_update_history_source (source_id, created_at),
          KEY idx_ip_update_history_system (system_code, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def _seed_default_data_sources(cursor: object) -> None:
    defaults = [
        (
            "ipds-pct-contracting-states",
            "PCT",
            PCT_SOURCE_NAME,
            "treaty_membership_source",
            PCT_SOURCE_URL,
            "PCT 正式缔约国数据；用于 PCT 成员关系判断，未来生效对象不计入当前成员。",
        ),
        (
            "ipds-pct-regional-designations",
            "PCT",
            PCT_REGIONAL_DESIGNATIONS_SOURCE_NAME,
            "regional_route_source",
            PCT_REGIONAL_DESIGNATIONS_SOURCE_URL,
            "PCT 区域指定/区域阶段路径提示；不生成 PCT 缔约国。",
        ),
        (
            "ipds-paris-contracting-parties",
            "PARIS",
            PARIS_SOURCE_NAME,
            "treaty_membership_source",
            PARIS_SOURCE_URL,
            "Paris Convention 181 个缔约方正式成员数据；用于成员计数和成员关系判断。",
        ),
        (
            "ipds-paris-non-pct-route",
            "PARIS",
            PARIS_NON_PCT_SOURCE_NAME,
            "paris_non_pct_route_source",
            PARIS_NON_PCT_SOURCE_URL,
            "识别属于巴黎公约成员但不是 PCT 缔约国的国家；不生成 PCT 成员关系，不影响 Paris 181 计数。",
        ),
        (
            "ipds-wipolex-members",
            "REFERENCE",
            "WIPO Lex 管辖区/组织参考名录",
            "reference_source",
            WIPO_LEX_MEMBERS_SOURCE_URL,
            "202 个 WIPO Lex 管辖区/组织参考对象；用于中文名、英文名、代码、别名、profile 和主档匹配参考；不生成任何条约成员关系。",
        ),
        (
            "ipds-epc-member-states",
            "EPC",
            EPC_SOURCE_NAME,
            "treaty_membership_source",
            EPC_SOURCE_URL,
            "EPC 成员国数据；延伸/生效关系单独展示，不混入成员国计数。",
        ),
        (
            "ipds-eu-design-members",
            "EU_DESIGN",
            EU_DESIGN_SOURCE_NAME,
            "design_scope_source",
            EU_DESIGN_SOURCE_URL,
            "欧盟外观设计适用成员国范围数据。",
        ),
    ]
    for item in defaults:
        cursor.execute(
            """
            INSERT INTO ip_system_data_source (
              id, system_code, source_name, source_type, source_url, purpose_note, is_enabled
            )
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
              system_code = VALUES(system_code),
              source_name = VALUES(source_name),
              source_type = VALUES(source_type),
              source_url = VALUES(source_url),
              purpose_note = VALUES(purpose_note),
              is_enabled = 1
            """,
            item,
        )


def _ensure_official_member_lightweight_columns(cursor: object) -> None:
    columns = [
        ("membership_relation_type", "VARCHAR(80) NOT NULL DEFAULT ''"),
        ("pct_route_type", "VARCHAR(80) NOT NULL DEFAULT ''"),
        ("regional_system_code", "VARCHAR(50) NOT NULL DEFAULT ''"),
        ("route_remark", "VARCHAR(1000) NOT NULL DEFAULT ''"),
        ("internal_remark", "VARCHAR(1000) NOT NULL DEFAULT ''"),
        ("remark_updated_at", "DATETIME NULL"),
        ("remark_updated_by", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ]
    for column_name, column_def in columns:
        if not _column_exists(cursor, "ip_system_official_members", column_name):
            cursor.execute(f"ALTER TABLE ip_system_official_members ADD COLUMN {column_name} {column_def}")


def _data_source_from_row(row: dict[str, object]) -> IpSystemDataSource:
    return IpSystemDataSource(
        id=str(row.get("id") or ""),
        system_code=str(row.get("system_code") or ""),
        source_name=str(row.get("source_name") or ""),
        source_type=str(row.get("source_type") or ""),
        source_url=str(row.get("source_url") or ""),
        purpose_note=str(row.get("purpose_note") or ""),
        is_enabled=bool(row.get("is_enabled")),
        last_checked_at=row.get("last_checked_at"),
        last_success_at=row.get("last_success_at"),
        last_check_status=str(row.get("last_check_status") or ""),
        last_check_message=str(row.get("last_check_message") or ""),
        last_check_summary=str(row.get("last_check_summary") or ""),
        last_update_summary=str(row.get("last_update_summary") or ""),
        admin_update_note=str(row.get("admin_update_note") or ""),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _history_from_row(row: dict[str, object]) -> IpSystemUpdateHistoryItem:
    return IpSystemUpdateHistoryItem(
        id=int(row.get("id") or 0),
        source_id=str(row.get("source_id") or ""),
        system_code=str(row.get("system_code") or ""),
        source_name=str(row.get("source_name") or ""),
        source_type=str(row.get("source_type") or ""),
        operation=str(row.get("operation") or ""),
        update_type=str(row.get("update_type") or ""),
        update_count=int(row.get("update_count") or 0),
        parsed_count=row.get("parsed_count"),
        parsed_date_count=row.get("parsed_date_count"),
        written_date_count=row.get("written_date_count"),
        system_summary=str(row.get("system_summary") or ""),
        admin_note=str(row.get("admin_note") or ""),
        actor=str(row.get("actor") or ""),
        status=str(row.get("status") or ""),
        failure_reason=str(row.get("failure_reason") or ""),
        created_at=row.get("created_at"),
    )


def _normalize_system_code(system_code: str) -> str:
    normalized = system_code.strip().upper().replace("-", "_")
    if normalized == "EUIPO":
        return "EU_DESIGN"
    return normalized


class _TableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._current_row.append(re.sub(r"\s+", " ", " ".join(self._current_cell)).strip())
            self._in_cell = False
        if tag == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []
