from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSourceRegistry:
    source_id: str
    source_name: str
    source_type: str
    source_owner: str
    source_url: str
    source_version: str
    applicable_fields: tuple[str, ...]
    verification_frequency: str
    source_note: str


@dataclass(frozen=True)
class JurisdictionReference:
    reference_id: str
    standard_code: str
    display_code: str
    name_cn: str
    name_en: str
    aliases: tuple[str, ...]
    jurisdiction_type: str
    geo_region: str
    default_business_economic_regions: tuple[str, ...]
    source_name: str
    source_url: str
    source_version: str
    source_note: str
    is_active: bool
    # Legacy compatibility only. Currency rules belong in the FX/tax module.
    default_currency_legacy: str


DATA_SOURCE_REGISTRY = [
    DataSourceRegistry(
        source_id="ISO_3166",
        source_name="ISO 3166 Country Codes Collection",
        source_type="official_standard",
        source_owner="International Organization for Standardization",
        source_url="https://www.iso.org/obp/ui/#search",
        source_version="Current online collection",
        applicable_fields=("standard_code", "name_en", "aliases"),
        verification_frequency="semi_annual_or_on_major_change",
        source_note="普通国家/地区名称辅助来源；专利业务标准代码以 WIPO ST.3 为准。",
    ),
    DataSourceRegistry(
        source_id="UN_M49",
        source_name="UNSD Standard Country or Area Codes for Statistical Use",
        source_type="official_standard",
        source_owner="United Nations Statistics Division",
        source_url="https://unstats.un.org/unsd/methodology/m49/",
        source_version="Current online table",
        applicable_fields=("geo_region",),
        verification_frequency="semi_annual",
        source_note="用于国际地理区域口径；不作为商务/经济区域或政治立场判断。",
    ),
    DataSourceRegistry(
        source_id="WIPO_ST3",
        source_name="WIPO Standard ST.3",
        source_type="official_standard",
        source_owner="World Intellectual Property Organization",
        source_url="https://www.wipo.int/standards/en/part_03_standards.html",
        source_version="WIPO ST.3 December 2025",
        applicable_fields=("standard_code", "jurisdiction_type", "display_code", "aliases"),
        verification_frequency="annual_or_on_standard_update",
        source_note="专利业务国家/地区、其他实体和组织标准代码来源；普通国家代码也以 ST.3 为准。",
    ),
    DataSourceRegistry(
        source_id="WIPO_TREATIES",
        source_name="WIPO Treaty Portals",
        source_type="official_reference",
        source_owner="World Intellectual Property Organization",
        source_url="https://www.wipo.int/treaties/en/",
        source_version="Current WIPO treaty pages",
        applicable_fields=("name_cn", "name_en", "jurisdiction_type", "source_note"),
        verification_frequency="annual_or_before_treaty_data_change",
        source_note="用于 PCT、Madrid、Hague 等条约体系入口的名称和说明核验。",
    ),
    DataSourceRegistry(
        source_id="EPO_OFFICIAL",
        source_name="European Patent Office",
        source_type="official_reference",
        source_owner="European Patent Organisation",
        source_url="https://www.epo.org/",
        source_version="Current official website",
        applicable_fields=("name_en", "display_code", "aliases"),
        verification_frequency="annual",
        source_note="用于 EPO 名称、简称和业务展示代码核验。",
    ),
    DataSourceRegistry(
        source_id="EUIPO_OFFICIAL",
        source_name="European Union Intellectual Property Office",
        source_type="official_reference",
        source_owner="European Union Intellectual Property Office",
        source_url="https://www.euipo.europa.eu/",
        source_version="Current official website",
        applicable_fields=("name_en", "display_code", "aliases"),
        verification_frequency="annual",
        source_note="用于 EUIPO 名称、简称和业务展示代码核验。",
    ),
    DataSourceRegistry(
        source_id="OAPI_OFFICIAL",
        source_name="Organisation Africaine de la Propriete Intellectuelle",
        source_type="official_reference",
        source_owner="OAPI",
        source_url="https://www.oapi.int/",
        source_version="Current official website",
        applicable_fields=("name_en", "display_code", "aliases"),
        verification_frequency="annual",
        source_note="用于 OAPI 名称、简称和业务展示代码核验。",
    ),
    DataSourceRegistry(
        source_id="ARIPO_OFFICIAL",
        source_name="African Regional Intellectual Property Organization",
        source_type="official_reference",
        source_owner="ARIPO",
        source_url="https://www.aripo.org/",
        source_version="Current official website",
        applicable_fields=("name_en", "display_code", "aliases"),
        verification_frequency="annual",
        source_note="用于 ARIPO 名称、简称和业务展示代码核验。",
    ),
    DataSourceRegistry(
        source_id="EAPO_OFFICIAL",
        source_name="Eurasian Patent Organization",
        source_type="official_reference",
        source_owner="EAPO",
        source_url="https://www.eapo.org/",
        source_version="Current official website",
        applicable_fields=("name_en", "display_code", "aliases"),
        verification_frequency="annual",
        source_note="用于 EAPO 名称、简称和业务展示代码核验。",
    ),
    DataSourceRegistry(
        source_id="BUSINESS_REGION_SOURCE",
        source_name="Internal business and market tag source",
        source_type="internal_policy",
        source_owner="internal",
        source_url="internal://business-region-tags",
        source_version="internal tag policy 2026-06",
        applicable_fields=("default_business_economic_regions",),
        verification_frequency="annual_or_internal_policy_change",
        source_note="商务/市场标签来源；经济组织与合作标签应单独展示，不作为国际地理区域来源。不确定时保持未配置，不强制 OTHER。",
    ),
]


def _country(
    code: str,
    name_cn: str,
    name_en: str,
    geo_region: str,
    tags: tuple[str, ...],
    currency: str,
    aliases: tuple[str, ...] = (),
    source_note: str = "普通国家/地区的专利业务标准代码以 WIPO ST.3 为准；地理区域以 UN M49 为准。",
) -> JurisdictionReference:
    return JurisdictionReference(
        reference_id=f"ref-{code.lower()}",
        standard_code=code,
        display_code=code,
        name_cn=name_cn,
        name_en=name_en,
        aliases=(code, name_cn, name_en, *aliases),
        jurisdiction_type="single_country",
        geo_region=geo_region,
        default_business_economic_regions=tags,
        source_name="WIPO ST.3 / UN M49",
        source_url="https://www.wipo.int/standards/en/part_03_standards.html",
        source_version="WIPO ST.3 current; UN M49 current",
        source_note=source_note,
        is_active=True,
        default_currency_legacy=currency,
    )


JURISDICTION_REFERENCES = [
    _country("CN", "中国", "China", "Asia", ("GREATER_CHINA", "APEC"), "CNY", ("CHN", "People's Republic of China", "中国大陆", "中國")),
    _country("US", "美国", "United States", "North America", ("NORTH_AMERICA", "APEC"), "USD", ("USA", "United States of America", "America", "美國")),
    _country("JP", "日本", "Japan", "Asia", ("NORTHEAST_ASIA_JP_KR", "APEC"), "JPY", ("JPN", "日本国")),
    _country("KR", "韩国", "South Korea", "Asia", ("NORTHEAST_ASIA_JP_KR", "APEC"), "KRW", ("KOR", "Republic of Korea", "Korea", "韓國")),
    _country("DE", "德国", "Germany", "Europe", ("EUROPE", "EU"), "EUR", ("DEU", "Deutschland", "德國")),
    _country("FR", "法国", "France", "Europe", ("EUROPE", "EU"), "EUR", ("FRA", "法國")),
    _country("GB", "英国", "United Kingdom", "Europe", ("EUROPE",), "GBP", ("GBR", "UK", "Great Britain", "Britain", "英國")),
    _country("IT", "意大利", "Italy", "Europe", ("EUROPE", "EU"), "EUR", ("ITA", "Italia", "義大利")),
    _country("ES", "西班牙", "Spain", "Europe", ("EUROPE", "EU"), "EUR", ("ESP", "España")),
    _country("CA", "加拿大", "Canada", "North America", ("NORTH_AMERICA", "APEC"), "CAD", ("CAN",)),
    _country("AU", "澳大利亚", "Australia", "Oceania", ("ANZ_OCEANIA", "APEC"), "AUD", ("AUS", "澳洲")),
    _country("NZ", "新西兰", "New Zealand", "Oceania", ("ANZ_OCEANIA", "APEC"), "NZD", ("NZL", "紐西蘭")),
    _country("SG", "新加坡", "Singapore", "Asia", ("SOUTHEAST_ASIA", "ASEAN", "APEC"), "SGD", ("SGP",)),
    _country("IN", "印度", "India", "Asia", ("SOUTH_ASIA", "BRICS"), "INR", ("IND",)),
    _country("BR", "巴西", "Brazil", "South America", ("LATIN_AMERICA", "BRICS"), "BRL", ("BRA", "Brasil")),
    _country("CO", "哥伦比亚", "Colombia", "Latin America and the Caribbean", ("LATIN_AMERICA",), "COP", ("COL",)),
    _country("MX", "墨西哥", "Mexico", "Latin America and the Caribbean", ("LATIN_AMERICA",), "MXN", ("MEX", "México")),
    _country("TH", "泰国", "Thailand", "Asia", ("SOUTHEAST_ASIA", "ASEAN", "APEC"), "THB", ("THA", "泰國")),
    _country("VN", "越南", "Viet Nam", "Asia", ("SOUTHEAST_ASIA", "ASEAN", "APEC"), "VND", ("VNM", "Vietnam")),
    _country("ID", "印度尼西亚", "Indonesia", "Asia", ("SOUTHEAST_ASIA", "ASEAN", "APEC"), "IDR", ("IDN", "印尼")),
    _country("MY", "马来西亚", "Malaysia", "Asia", ("SOUTHEAST_ASIA", "ASEAN", "APEC"), "MYR", ("MYS", "馬來西亞")),
    _country("PH", "菲律宾", "Philippines", "Asia", ("SOUTHEAST_ASIA", "ASEAN", "APEC"), "PHP", ("PHL", "the Philippines", "菲律賓")),
    _country("TW", "中国台湾", "Taiwan", "Asia", ("GREATER_CHINA", "APEC"), "TWD", ("TWN", "Taiwan, Province of China", "台湾", "臺灣")),
    _country("HK", "中国香港", "Hong Kong", "Asia", ("GREATER_CHINA", "APEC"), "HKD", ("HKG", "Hong Kong SAR", "香港")),
    _country("MO", "中国澳门", "Macao", "Asia", ("GREATER_CHINA",), "MOP", ("MAC", "Macau", "澳门", "澳門")),
    JurisdictionReference(
        reference_id="ref-ep",
        standard_code="EP",
        display_code="EPO",
        name_cn="欧洲专利局",
        name_en="European Patent Office",
        aliases=("EP", "EPO", "European Patent Organisation", "European Patent Organization", "欧洲专利组织", "欧洲专利局", "Europe patent"),
        jurisdiction_type="regional_office",
        geo_region="Europe",
        default_business_economic_regions=("EUROPE",),
        source_name="WIPO ST.3 / EPO official website",
        source_url="https://www.epo.org/",
        source_version="WIPO ST.3 December 2025; EPO current official website",
        source_note="区域专利受理局，不是普通国家；可作为独立申请/进入对象维护。",
        is_active=True,
        default_currency_legacy="EUR",
    ),
    JurisdictionReference(
        reference_id="ref-em",
        standard_code="EM",
        display_code="EUIPO",
        name_cn="欧盟知识产权局",
        name_en="European Union Intellectual Property Office",
        aliases=("EM", "EUIPO", "OHIM", "European Union Intellectual Property Office", "欧盟知识产权局", "EU trade mark", "European Union trade mark"),
        jurisdiction_type="regional_office",
        geo_region="Europe",
        default_business_economic_regions=("EUROPE", "EU"),
        source_name="WIPO ST.3 / EUIPO official website",
        source_url="https://www.euipo.europa.eu/",
        source_version="WIPO ST.3 December 2025; EUIPO current official website",
        source_note="欧盟知识产权区域对象，不是普通国家；业务展示代码使用 EUIPO。",
        is_active=True,
        default_currency_legacy="EUR",
    ),
    JurisdictionReference(
        reference_id="ref-oa",
        standard_code="OA",
        display_code="OAPI",
        name_cn="非洲知识产权组织",
        name_en="African Intellectual Property Organization",
        aliases=("OA", "OAPI", "Organisation Africaine de la Propriete Intellectuelle", "非洲知识产权组织"),
        jurisdiction_type="regional_office",
        geo_region="Africa",
        default_business_economic_regions=("AFRICA",),
        source_name="WIPO ST.3 / OAPI official website",
        source_url="https://www.oapi.int/",
        source_version="WIPO ST.3 December 2025; OAPI current official website",
        source_note="区域知识产权组织，不作为普通国家处理。",
        is_active=True,
        default_currency_legacy="XAF",
    ),
    JurisdictionReference(
        reference_id="ref-ap",
        standard_code="AP",
        display_code="ARIPO",
        name_cn="非洲地区知识产权组织",
        name_en="African Regional Intellectual Property Organization",
        aliases=("AP", "ARIPO", "African Regional Industrial Property Organization", "非洲地区知识产权组织"),
        jurisdiction_type="regional_office",
        geo_region="Africa",
        default_business_economic_regions=("AFRICA",),
        source_name="WIPO ST.3 / ARIPO official website",
        source_url="https://www.aripo.org/",
        source_version="WIPO ST.3 December 2025; ARIPO current official website",
        source_note="区域知识产权组织，不作为普通国家处理。",
        is_active=True,
        default_currency_legacy="USD",
    ),
    JurisdictionReference(
        reference_id="ref-ea",
        standard_code="EA",
        display_code="EAPO",
        name_cn="欧亚专利组织",
        name_en="Eurasian Patent Organization",
        aliases=("EA", "EAPO", "Eurasian Patent Office", "欧亚专利局", "欧亚专利组织"),
        jurisdiction_type="regional_office",
        geo_region="Europe",
        default_business_economic_regions=("EUROPE",),
        source_name="WIPO ST.3 / EAPO official website",
        source_url="https://www.eapo.org/",
        source_version="WIPO ST.3 December 2025; EAPO current official website",
        source_note="区域专利组织，不作为普通国家处理。",
        is_active=True,
        default_currency_legacy="USD",
    ),
    JurisdictionReference(
        reference_id="ref-wo",
        standard_code="WO",
        display_code="WIPO",
        name_cn="世界知识产权组织",
        name_en="World Intellectual Property Organization",
        aliases=("WO", "WIPO", "World Intellectual Property Organisation", "世界知识产权组织"),
        jurisdiction_type="international_organization",
        geo_region="Other",
        default_business_economic_regions=("OTHER",),
        source_name="WIPO ST.3 / WIPO official website",
        source_url="https://www.wipo.int/",
        source_version="WIPO ST.3 December 2025; WIPO current official website",
        source_note="国际组织，不作为普通国家处理。",
        is_active=True,
        default_currency_legacy="CHF",
    ),
    JurisdictionReference(
        reference_id="ref-pct",
        standard_code="PCT",
        display_code="PCT",
        name_cn="专利合作条约入口",
        name_en="Patent Cooperation Treaty",
        aliases=("PCT", "Patent Cooperation Treaty", "PCT 入口", "专利合作条约", "国际阶段"),
        jurisdiction_type="treaty_entry",
        geo_region="Other",
        default_business_economic_regions=("OTHER",),
        source_name="WIPO PCT",
        source_url="https://www.wipo.int/pct/en/",
        source_version="WIPO PCT current official page",
        source_note="条约体系入口，不作为普通国家处理；成员关系和进入路径规则另行维护。",
        is_active=True,
        default_currency_legacy="CHF",
    ),
    JurisdictionReference(
        reference_id="ref-madrid",
        standard_code="MADRID",
        display_code="MADRID",
        name_cn="马德里商标国际注册入口",
        name_en="Madrid System",
        aliases=("MADRID", "Madrid Protocol", "Madrid Agreement", "Madrid System", "马德里体系", "马德里商标国际注册"),
        jurisdiction_type="treaty_entry",
        geo_region="Other",
        default_business_economic_regions=("OTHER",),
        source_name="WIPO Madrid System",
        source_url="https://www.wipo.int/madrid/en/",
        source_version="WIPO Madrid current official page",
        source_note="商标国际注册条约体系入口，不作为普通国家处理。",
        is_active=True,
        default_currency_legacy="CHF",
    ),
    JurisdictionReference(
        reference_id="ref-hague",
        standard_code="HAGUE",
        display_code="HAGUE",
        name_cn="海牙外观设计国际注册入口",
        name_en="Hague System",
        aliases=("HAGUE", "Hague Agreement", "Hague System", "海牙体系", "海牙外观设计"),
        jurisdiction_type="treaty_entry",
        geo_region="Other",
        default_business_economic_regions=("OTHER",),
        source_name="WIPO Hague System",
        source_url="https://www.wipo.int/hague/en/",
        source_version="WIPO Hague current official page",
        source_note="外观设计国际注册条约体系入口，不作为普通国家处理。",
        is_active=True,
        default_currency_legacy="CHF",
    ),
]


def get_jurisdiction_reference(reference_id: str) -> JurisdictionReference | None:
    return next(
        (item for item in JURISDICTION_REFERENCES if item.reference_id == reference_id and item.is_active),
        None,
    )
