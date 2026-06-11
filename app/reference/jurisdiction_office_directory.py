from __future__ import annotations

from dataclasses import dataclass

from app.reference.jurisdiction_field_sources import (
    OFFICE_DISPLAY_CODE_BY_COUNTRY,
    OFFICE_NAME_CN_BY_COUNTRY,
    WIPO_NATIONAL_OFFICE_ROWS,
)


SOURCE_ID = "WIPO_IP_OFFICES_DIRECTORY"
SOURCE_URL = "https://www.wipo.int/en/web/country-profiles/directory-ip-offices"
SOURCE_VERSION = "WIPO Country Profiles - Directory of IP Offices current"


@dataclass(frozen=True)
class JurisdictionOfficeDirectoryItem:
    country_code: str
    jurisdiction_code: str
    country_name_en: str
    office_role: str
    office_name_en: str
    office_name_cn: str
    office_display_code: str
    office_type: str
    source_id: str
    source_url: str
    source_version: str
    review_status: str
    is_active: bool
    source_note: str


def default_office_directory_items() -> list[JurisdictionOfficeDirectoryItem]:
    rows = [
        (
            country_code,
            country_code,
            country_name_en,
            office_role,
            office_name_en,
            OFFICE_NAME_CN_BY_COUNTRY.get(country_code, ""),
            OFFICE_DISPLAY_CODE_BY_COUNTRY.get(country_code, ""),
            "national_ip_office",
        )
        for country_code, country_name_en, office_role, office_name_en in WIPO_NATIONAL_OFFICE_ROWS
    ]
    rows.extend(
        [
            ("EP", "EP", "European Patent Organisation", "regional_office", "European Patent Office", "欧洲专利局", "EPO", "regional_office"),
            ("EM", "EM", "European Union", "regional_office", "European Union Intellectual Property Office", "欧盟知识产权局", "EUIPO", "regional_office"),
            ("WO", "WO", "World Intellectual Property Organization", "international_office", "International Bureau of WIPO", "世界知识产权组织国际局", "WIPO/IB", "international_office"),
        ]
    )
    return [
        JurisdictionOfficeDirectoryItem(
            country_code=country_code,
            jurisdiction_code=jurisdiction_code,
            country_name_en=country_name_en,
            office_role=office_role,
            office_name_en=office_name_en,
            office_name_cn=office_name_cn,
            office_display_code=office_display_code,
            office_type=office_type,
            source_id=SOURCE_ID,
            source_url=SOURCE_URL,
            source_version=SOURCE_VERSION,
            review_status="pending_review",
            is_active=True,
            source_note="Seeded from WIPO Country Profiles - Directory of IP Offices. Office display code is blank when the WIPO directory does not confirm an abbreviation.",
        )
        for (
            country_code,
            jurisdiction_code,
            country_name_en,
            office_role,
            office_name_en,
            office_name_cn,
            office_display_code,
            office_type,
        ) in rows
    ]


def office_directory_item_for_code(code: str) -> JurisdictionOfficeDirectoryItem | None:
    normalized = code.upper()
    for item in default_office_directory_items():
        if normalized in {item.country_code.upper(), item.jurisdiction_code.upper(), item.office_display_code.upper()}:
            return item
    return None
