from __future__ import annotations

from dataclasses import dataclass

from app.reference.ip_system_official_baseline import COUNTRY_NAMES
from app.reference.jurisdiction_field_sources import (
    BUSINESS_TAGS_BY_CODE,
    OFFICE_ALIASES_BY_COUNTRY,
    UN_M49_REGION_BY_CODE,
    WIPO_LEX_CANDIDATE_SOURCE_NOTE,
)
from app.reference.jurisdictions import JURISDICTION_REFERENCES


@dataclass(frozen=True)
class JurisdictionReferenceRegistryItem:
    reference_id: str
    standard_code: str
    display_code: str
    name_cn: str
    name_en: str
    aliases: tuple[str, ...]
    jurisdiction_type: str
    reference_category: str
    business_scope: tuple[str, ...]
    visibility_scope: str
    candidate_status: str
    quote_selectable_default: bool
    not_selectable_reason: str
    reserved_reason: str
    geo_region: str
    default_business_economic_regions: tuple[str, ...]
    source_id: str
    source_name: str
    source_url: str
    source_version: str
    source_note: str
    source_verified: bool
    review_status: str
    is_active: bool
    default_currency_legacy: str


TRADEMARK_RESERVED_CODES = {"MADRID", "NICE"}
DESIGN_RESERVED_CODES = {"HAGUE"}
PATENT_TREATY_CODES = {"PCT"}
REGIONAL_OFFICE_CODES = {"EP", "EM", "OA", "AP", "EA", "BX"}
INTERNATIONAL_ORG_CODES = {"WO", "EU", "IB", "GC"}
SPECIAL_REGION_CODES = {"HK", "MO", "TW", "FO", "GL", "GI", "IM", "JE", "PS", "XK"}
DISPLAY_CODE_OVERRIDES = {
    "EP": "EPO",
    "EM": "EUIPO",
    "OA": "OAPI",
    "AP": "ARIPO",
    "EA": "EAPO",
    "WO": "WIPO",
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


def default_registry_items() -> list[JurisdictionReferenceRegistryItem]:
    items: dict[str, JurisdictionReferenceRegistryItem] = {}
    for reference in JURISDICTION_REFERENCES:
        items[reference.reference_id] = _from_static_reference(reference)

    for code, names in COUNTRY_NAMES.items():
        key = f"ref-{code.lower()}"
        if key not in items:
            items[key] = _country_candidate(code, names[0], names[1])

    for code, name_cn, name_en, object_type, _object_type_label in REFERENCE_EXTRA_OBJECTS:
        key = f"ref-{code.lower()}"
        if key not in items:
            items[key] = _extra_candidate(code, name_cn, name_en, object_type)

    for code, name_cn, name_en, business_scope, reserved_reason in (
        ("NICE", "尼斯分类 / 尼斯协定预留", "Nice Classification / Nice Agreement", ("trademark",), "trademark_reserved"),
    ):
        key = f"ref-{code.lower()}"
        if key not in items:
            items[key] = JurisdictionReferenceRegistryItem(
                reference_id=key,
                standard_code=code,
                display_code=code,
                name_cn=name_cn,
                name_en=name_en,
                aliases=(code, name_cn, name_en, "Nice", "尼斯", "商标分类"),
                jurisdiction_type="treaty_entry",
                reference_category="treaty_route",
                business_scope=business_scope,
                visibility_scope="reserved_hidden",
                candidate_status="reserved",
                quote_selectable_default=False,
                not_selectable_reason="商标体系预留，当前专利报价系统不启用",
                reserved_reason=reserved_reason,
                geo_region="Other",
                default_business_economic_regions=("OTHER",),
                source_id="WIPO_TREATIES",
                source_name="WIPO Treaty Portals",
                source_url="https://www.wipo.int/treaties/en/",
                source_version="Current WIPO treaty pages",
                source_note="商标相关体系预留；当前专利报价入口隐藏。",
                source_verified=False,
                review_status="pending_review",
                is_active=True,
                default_currency_legacy="CHF",
            )

    return sorted(items.values(), key=lambda item: (item.reference_category, item.standard_code))


def _from_static_reference(reference: object) -> JurisdictionReferenceRegistryItem:
    code = str(getattr(reference, "standard_code"))
    normalized_code = code.upper()
    jurisdiction_type = str(getattr(reference, "jurisdiction_type"))
    if normalized_code in SPECIAL_REGION_CODES:
        jurisdiction_type = "special_region"
    business_scope = _business_scope_for_code(code, jurisdiction_type)
    visibility_scope = "country_master_reference"
    candidate_status = "candidate"
    not_selectable_reason = "未纳入当前报价范围"
    reserved_reason = ""
    if normalized_code in TRADEMARK_RESERVED_CODES:
        visibility_scope = "reserved_hidden"
        candidate_status = "reserved"
        not_selectable_reason = "商标体系预留，当前专利报价系统不启用"
        reserved_reason = "trademark_reserved"
    elif normalized_code in DESIGN_RESERVED_CODES:
        candidate_status = "reserved"
        not_selectable_reason = "外观设计国际注册路径预留，当前正式报价不启用"
        reserved_reason = "design_reserved"
    elif normalized_code in PATENT_TREATY_CODES:
        candidate_status = "reserved"
        not_selectable_reason = "条约路径入口预留，当前不作为报价台可选国家"
        reserved_reason = "treaty_route_reserved"

    return JurisdictionReferenceRegistryItem(
        reference_id=str(getattr(reference, "reference_id")),
        standard_code=code,
        display_code=str(getattr(reference, "display_code")),
        name_cn=str(getattr(reference, "name_cn")),
        name_en=str(getattr(reference, "name_en")),
        aliases=tuple(getattr(reference, "aliases")),
        jurisdiction_type=jurisdiction_type,
        reference_category=_reference_category(jurisdiction_type, code),
        business_scope=business_scope,
        visibility_scope=visibility_scope,
        candidate_status=candidate_status,
        quote_selectable_default=False,
        not_selectable_reason=not_selectable_reason,
        reserved_reason=reserved_reason,
        geo_region=str(getattr(reference, "geo_region")),
        default_business_economic_regions=tuple(getattr(reference, "default_business_economic_regions")),
        source_id=_source_id_for_code(code),
        source_name=str(getattr(reference, "source_name")),
        source_url=str(getattr(reference, "source_url")),
        source_version=str(getattr(reference, "source_version")),
        source_note=str(getattr(reference, "source_note")),
        source_verified=False,
        review_status="pending_review",
        is_active=bool(getattr(reference, "is_active")),
        default_currency_legacy=str(getattr(reference, "default_currency_legacy")),
    )


def _country_candidate(code: str, name_cn: str, name_en: str) -> JurisdictionReferenceRegistryItem:
    geo_region = UN_M49_REGION_BY_CODE.get(code, "Other")
    business_tags = BUSINESS_TAGS_BY_CODE.get(code, ())
    aliases = (code, name_cn, name_en, *OFFICE_ALIASES_BY_COUNTRY.get(code, ()))
    return JurisdictionReferenceRegistryItem(
        reference_id=f"ref-{code.lower()}",
        standard_code=code,
        display_code=DISPLAY_CODE_OVERRIDES.get(code, code),
        name_cn=name_cn,
        name_en=name_en,
        aliases=aliases,
        jurisdiction_type="special_region" if code in SPECIAL_REGION_CODES else "single_country",
        reference_category="region" if code in SPECIAL_REGION_CODES else "country",
        business_scope=("patent", "design"),
        visibility_scope="country_master_reference",
        candidate_status="candidate",
        quote_selectable_default=False,
        not_selectable_reason="未纳入当前报价范围",
        reserved_reason="",
        geo_region=geo_region,
        default_business_economic_regions=business_tags,
        source_id="WIPO_ST3",
        source_name="WIPO ST.3 / UN M49 / BUSINESS_REGION_SOURCE field baseline",
        source_url="https://www.wipo.int/standards/en/part_03_standards.html; https://unstats.un.org/unsd/methodology/m49/",
        source_version="WIPO ST.3 current; UN M49 current",
        source_note="普通国家/地区候选：standard_code/display_code=WIPO_ST3；international_region=UN_M49；business_region=BUSINESS_REGION_SOURCE。WIPO Lex 不作为国家主档字段来源。",
        source_verified=False,
        review_status="pending_review",
        is_active=True,
        default_currency_legacy="USD",
    )


def _extra_candidate(code: str, name_cn: str, name_en: str, object_type: str) -> JurisdictionReferenceRegistryItem:
    if object_type == "regional_office":
        jurisdiction_type = "regional_office"
        category = "regional_office"
        business_scope = ("patent", "design")
    elif object_type == "intergovernmental_org":
        jurisdiction_type = "international_organization"
        category = "international_organization"
        business_scope = ("patent", "design")
    elif object_type == "region":
        jurisdiction_type = "special_region"
        category = "region"
        business_scope = ("patent", "design")
    else:
        jurisdiction_type = "special_region"
        category = "reference_object"
        business_scope = ("patent", "design")

    return JurisdictionReferenceRegistryItem(
        reference_id=f"ref-{code.lower()}",
        standard_code=code,
        display_code=DISPLAY_CODE_OVERRIDES.get(code, code),
        name_cn=name_cn,
        name_en=name_en,
        aliases=(code, name_cn, name_en, DISPLAY_CODE_OVERRIDES.get(code, code)),
        jurisdiction_type=jurisdiction_type,
        reference_category=category,
        business_scope=business_scope,
        visibility_scope="country_master_reference",
        candidate_status="candidate",
        quote_selectable_default=False,
        not_selectable_reason="未纳入当前报价范围",
        reserved_reason="",
        geo_region="Other",
        default_business_economic_regions=("OTHER",),
        source_id="WIPO_LEX_REFERENCE",
        source_name="WIPO Lex Members / treaty reference baseline",
        source_url="https://www.wipo.int/wipolex/zh/members",
        source_version="P0 WIPO Lex reference object baseline",
        source_note=f"由条约/组织查询侧 WIPO Lex reference 对象池补入候选；不等于已启用报价对象。{WIPO_LEX_CANDIDATE_SOURCE_NOTE}",
        source_verified=False,
        review_status="pending_review",
        is_active=True,
        default_currency_legacy="USD",
    )


def _business_scope_for_code(code: str, jurisdiction_type: str) -> tuple[str, ...]:
    normalized = code.upper()
    if normalized in TRADEMARK_RESERVED_CODES:
        return ("trademark",)
    if normalized in DESIGN_RESERVED_CODES or normalized == "EM":
        return ("design",)
    if normalized == "PCT" or normalized in {"EP", "EA"}:
        return ("patent",)
    if jurisdiction_type == "treaty_entry":
        return ("patent", "design")
    return ("patent", "design")


def _reference_category(jurisdiction_type: str, code: str) -> str:
    if jurisdiction_type == "single_country":
        return "country"
    if jurisdiction_type == "special_region":
        return "region"
    if jurisdiction_type == "regional_office":
        return "regional_office"
    if jurisdiction_type == "international_organization":
        return "international_organization"
    if jurisdiction_type == "treaty_entry":
        return "treaty_route"
    return "reference_object"


def _source_id_for_code(code: str) -> str:
    normalized = code.upper()
    if normalized in {"PCT", "MADRID", "HAGUE", "NICE"}:
        return "WIPO_TREATIES"
    if normalized in REGIONAL_OFFICE_CODES | INTERNATIONAL_ORG_CODES:
        return "WIPO_ST3"
    return "WIPO_ST3"
