from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class OfficialMemberSeed:
    system_code: str
    jurisdiction_code: str
    name_zh: str
    name_en: str
    member_type: str = "country"
    effective_date: date | None = None
    source_name: str = ""
    source_url: str = ""
    remark: str = ""
    display_order: int = 1000


PCT_SOURCE_NAME = "WIPO PCT Contracting States"
PCT_SOURCE_URL = "https://www.wipo.int/en/web/pct-system/pct_contracting_states"
PARIS_SOURCE_NAME = "WIPO Lex Paris Convention Contracting Parties"
PARIS_SOURCE_URL = "https://www.wipo.int/wipolex/en/treaties/ShowResults?search_what=C&treaty_id=2"
WIPO_LEX_MEMBERS_SOURCE_NAME = "WIPO Lex Members"
WIPO_LEX_MEMBERS_SOURCE_URL = "https://www.wipo.int/wipolex/zh/members"
PARIS_NON_PCT_SOURCE_NAME = "WIPO States bound by the Paris Convention but not the PCT"
PARIS_NON_PCT_SOURCE_URL = "https://www.wipo.int/en/web/pct-system/paris_non_pct"
PCT_REGIONAL_DESIGNATIONS_SOURCE_NAME = "WIPO PCT Regional Designations"
PCT_REGIONAL_DESIGNATIONS_SOURCE_URL = "https://www.wipo.int/zh/web/pct-system/texts/reg_des"
EPC_SOURCE_NAME = "EPO Member States"
EPC_SOURCE_URL = "https://www.epo.org/en/about-us/foundation/member-states"
EU_DESIGN_SOURCE_NAME = "EUIPO / European Union member countries"
EU_DESIGN_SOURCE_URL = "https://european-union.europa.eu/principles-countries-history/eu-countries_en"


COUNTRY_NAMES: dict[str, tuple[str, str]] = {
    "AD": ("安道尔", "Andorra"),
    "AE": ("阿联酋", "United Arab Emirates"),
    "AF": ("阿富汗", "Afghanistan"),
    "AG": ("安提瓜和巴布达", "Antigua and Barbuda"),
    "AL": ("阿尔巴尼亚", "Albania"),
    "AM": ("亚美尼亚", "Armenia"),
    "AO": ("安哥拉", "Angola"),
    "AR": ("阿根廷", "Argentina"),
    "AT": ("奥地利", "Austria"),
    "AU": ("澳大利亚", "Australia"),
    "AZ": ("阿塞拜疆", "Azerbaijan"),
    "BA": ("波黑", "Bosnia and Herzegovina"),
    "BB": ("巴巴多斯", "Barbados"),
    "BD": ("孟加拉国", "Bangladesh"),
    "BE": ("比利时", "Belgium"),
    "BF": ("布基纳法索", "Burkina Faso"),
    "BG": ("保加利亚", "Bulgaria"),
    "BH": ("巴林", "Bahrain"),
    "BI": ("布隆迪", "Burundi"),
    "BJ": ("贝宁", "Benin"),
    "BN": ("文莱", "Brunei Darussalam"),
    "BO": ("玻利维亚", "Bolivia"),
    "BR": ("巴西", "Brazil"),
    "BS": ("巴哈马", "Bahamas"),
    "BT": ("不丹", "Bhutan"),
    "BW": ("博茨瓦纳", "Botswana"),
    "BY": ("白俄罗斯", "Belarus"),
    "BZ": ("伯利兹", "Belize"),
    "CA": ("加拿大", "Canada"),
    "CD": ("刚果（金）", "Democratic Republic of the Congo"),
    "CF": ("中非共和国", "Central African Republic"),
    "CG": ("刚果共和国", "Congo"),
    "CH": ("瑞士", "Switzerland"),
    "CI": ("科特迪瓦", "Cote d'Ivoire"),
    "CL": ("智利", "Chile"),
    "CM": ("喀麦隆", "Cameroon"),
    "CN": ("中国", "China"),
    "CO": ("哥伦比亚", "Colombia"),
    "CR": ("哥斯达黎加", "Costa Rica"),
    "CU": ("古巴", "Cuba"),
    "CV": ("佛得角", "Cabo Verde"),
    "CY": ("塞浦路斯", "Cyprus"),
    "CZ": ("捷克", "Czech Republic"),
    "DE": ("德国", "Germany"),
    "DJ": ("吉布提", "Djibouti"),
    "DK": ("丹麦", "Denmark"),
    "DM": ("多米尼克", "Dominica"),
    "DO": ("多米尼加共和国", "Dominican Republic"),
    "DZ": ("阿尔及利亚", "Algeria"),
    "EC": ("厄瓜多尔", "Ecuador"),
    "EE": ("爱沙尼亚", "Estonia"),
    "EG": ("埃及", "Egypt"),
    "ES": ("西班牙", "Spain"),
    "ET": ("埃塞俄比亚", "Ethiopia"),
    "FI": ("芬兰", "Finland"),
    "FJ": ("斐济", "Fiji"),
    "FR": ("法国", "France"),
    "GA": ("加蓬", "Gabon"),
    "GB": ("英国", "United Kingdom"),
    "GD": ("格林纳达", "Grenada"),
    "GE": ("格鲁吉亚", "Georgia"),
    "GH": ("加纳", "Ghana"),
    "GM": ("冈比亚", "Gambia"),
    "GN": ("几内亚", "Guinea"),
    "GQ": ("赤道几内亚", "Equatorial Guinea"),
    "GR": ("希腊", "Greece"),
    "GT": ("危地马拉", "Guatemala"),
    "GW": ("几内亚比绍", "Guinea-Bissau"),
    "GY": ("圭亚那", "Guyana"),
    "HN": ("洪都拉斯", "Honduras"),
    "HR": ("克罗地亚", "Croatia"),
    "HT": ("海地", "Haiti"),
    "HU": ("匈牙利", "Hungary"),
    "ID": ("印度尼西亚", "Indonesia"),
    "IE": ("爱尔兰", "Ireland"),
    "IL": ("以色列", "Israel"),
    "IN": ("印度", "India"),
    "IQ": ("伊拉克", "Iraq"),
    "IR": ("伊朗", "Iran"),
    "IS": ("冰岛", "Iceland"),
    "IT": ("意大利", "Italy"),
    "JM": ("牙买加", "Jamaica"),
    "JO": ("约旦", "Jordan"),
    "JP": ("日本", "Japan"),
    "KE": ("肯尼亚", "Kenya"),
    "KG": ("吉尔吉斯斯坦", "Kyrgyzstan"),
    "KH": ("柬埔寨", "Cambodia"),
    "KI": ("基里巴斯", "Kiribati"),
    "KM": ("科摩罗", "Comoros"),
    "KN": ("圣基茨和尼维斯", "Saint Kitts and Nevis"),
    "KP": ("朝鲜", "Democratic People's Republic of Korea"),
    "KR": ("韩国", "Republic of Korea"),
    "KW": ("科威特", "Kuwait"),
    "KZ": ("哈萨克斯坦", "Kazakhstan"),
    "LA": ("老挝", "Lao People's Democratic Republic"),
    "LB": ("黎巴嫩", "Lebanon"),
    "LC": ("圣卢西亚", "Saint Lucia"),
    "LI": ("列支敦士登", "Liechtenstein"),
    "LK": ("斯里兰卡", "Sri Lanka"),
    "LR": ("利比里亚", "Liberia"),
    "LS": ("莱索托", "Lesotho"),
    "LT": ("立陶宛", "Lithuania"),
    "LU": ("卢森堡", "Luxembourg"),
    "LV": ("拉脱维亚", "Latvia"),
    "LY": ("利比亚", "Libya"),
    "MA": ("摩洛哥", "Morocco"),
    "MC": ("摩纳哥", "Monaco"),
    "MD": ("摩尔多瓦", "Republic of Moldova"),
    "ME": ("黑山", "Montenegro"),
    "MG": ("马达加斯加", "Madagascar"),
    "MK": ("北马其顿", "North Macedonia"),
    "ML": ("马里", "Mali"),
    "MN": ("蒙古", "Mongolia"),
    "MR": ("毛里塔尼亚", "Mauritania"),
    "MT": ("马耳他", "Malta"),
    "MU": ("毛里求斯", "Mauritius"),
    "MV": ("马尔代夫", "Maldives"),
    "MW": ("马拉维", "Malawi"),
    "MX": ("墨西哥", "Mexico"),
    "MY": ("马来西亚", "Malaysia"),
    "MZ": ("莫桑比克", "Mozambique"),
    "NA": ("纳米比亚", "Namibia"),
    "NE": ("尼日尔", "Niger"),
    "NG": ("尼日利亚", "Nigeria"),
    "NI": ("尼加拉瓜", "Nicaragua"),
    "NL": ("荷兰", "Netherlands"),
    "NO": ("挪威", "Norway"),
    "NP": ("尼泊尔", "Nepal"),
    "NZ": ("新西兰", "New Zealand"),
    "OM": ("阿曼", "Oman"),
    "PA": ("巴拿马", "Panama"),
    "PE": ("秘鲁", "Peru"),
    "PG": ("巴布亚新几内亚", "Papua New Guinea"),
    "PH": ("菲律宾", "Philippines"),
    "PK": ("巴基斯坦", "Pakistan"),
    "PL": ("波兰", "Poland"),
    "PT": ("葡萄牙", "Portugal"),
    "PY": ("巴拉圭", "Paraguay"),
    "QA": ("卡塔尔", "Qatar"),
    "RO": ("罗马尼亚", "Romania"),
    "RS": ("塞尔维亚", "Serbia"),
    "RU": ("俄罗斯", "Russian Federation"),
    "RW": ("卢旺达", "Rwanda"),
    "SA": ("沙特阿拉伯", "Saudi Arabia"),
    "SC": ("塞舌尔", "Seychelles"),
    "SD": ("苏丹", "Sudan"),
    "SE": ("瑞典", "Sweden"),
    "SG": ("新加坡", "Singapore"),
    "SI": ("斯洛文尼亚", "Slovenia"),
    "SK": ("斯洛伐克", "Slovakia"),
    "SL": ("塞拉利昂", "Sierra Leone"),
    "SM": ("圣马力诺", "San Marino"),
    "SN": ("塞内加尔", "Senegal"),
    "SR": ("苏里南", "Suriname"),
    "ST": ("圣多美和普林西比", "Sao Tome and Principe"),
    "SV": ("萨尔瓦多", "El Salvador"),
    "SY": ("叙利亚", "Syrian Arab Republic"),
    "SZ": ("斯威士兰", "Eswatini"),
    "TD": ("乍得", "Chad"),
    "TG": ("多哥", "Togo"),
    "TH": ("泰国", "Thailand"),
    "TJ": ("塔吉克斯坦", "Tajikistan"),
    "TM": ("土库曼斯坦", "Turkmenistan"),
    "TN": ("突尼斯", "Tunisia"),
    "TO": ("汤加", "Tonga"),
    "TR": ("土耳其", "Turkiye"),
    "TT": ("特立尼达和多巴哥", "Trinidad and Tobago"),
    "TZ": ("坦桑尼亚", "United Republic of Tanzania"),
    "UA": ("乌克兰", "Ukraine"),
    "UG": ("乌干达", "Uganda"),
    "US": ("美国", "United States of America"),
    "UY": ("乌拉圭", "Uruguay"),
    "UZ": ("乌兹别克斯坦", "Uzbekistan"),
    "VA": ("梵蒂冈", "Holy See"),
    "VC": ("圣文森特和格林纳丁斯", "Saint Vincent and the Grenadines"),
    "VE": ("委内瑞拉", "Venezuela"),
    "VN": ("越南", "Viet Nam"),
    "WS": ("萨摩亚", "Samoa"),
    "YE": ("也门", "Yemen"),
    "ZA": ("南非", "South Africa"),
    "ZM": ("赞比亚", "Zambia"),
    "ZW": ("津巴布韦", "Zimbabwe"),
}


PCT_EFFECTIVE_DATES = {
    "DE": date(1978, 1, 24),
    "JP": date(1978, 10, 1),
    "US": date(1978, 1, 24),
    "CN": date(1994, 1, 1),
    "KR": date(1984, 8, 10),
    "MU": date(2023, 3, 15),
    "UY": date(2025, 1, 7),
}

PARIS_EFFECTIVE_DATES = {
    "DE": date(1903, 5, 1),
    "JP": date(1899, 7, 15),
    "US": date(1887, 5, 30),
    "CN": date(1985, 3, 19),
    "KR": date(1980, 5, 4),
}

EPC_EFFECTIVE_DATES = {
    "AL": date(2010, 5, 1),
    "AT": date(1979, 5, 1),
    "BE": date(1977, 10, 7),
    "BG": date(2002, 7, 1),
    "CH": date(1977, 10, 7),
    "CY": date(1998, 4, 1),
    "CZ": date(2002, 7, 1),
    "DE": date(1977, 10, 7),
    "DK": date(1990, 1, 1),
    "EE": date(2002, 7, 1),
    "ES": date(1986, 10, 1),
    "FI": date(1996, 3, 1),
    "FR": date(1977, 10, 7),
    "GB": date(1977, 10, 7),
    "GR": date(1986, 10, 1),
    "HR": date(2008, 1, 1),
    "HU": date(2003, 1, 1),
    "IE": date(1992, 8, 1),
    "IS": date(2004, 11, 1),
    "IT": date(1978, 12, 1),
    "LI": date(1980, 4, 1),
    "LT": date(2004, 12, 1),
    "LU": date(1977, 10, 7),
    "LV": date(2005, 7, 1),
    "MC": date(1991, 12, 1),
    "MD": date(2026, 6, 1),
    "ME": date(2022, 10, 1),
    "MK": date(2009, 1, 1),
    "MT": date(2007, 3, 1),
    "NL": date(1977, 10, 7),
    "NO": date(2008, 1, 1),
    "PL": date(2004, 3, 1),
    "PT": date(1992, 1, 1),
    "RO": date(2003, 3, 1),
    "RS": date(2010, 10, 1),
    "SE": date(1978, 5, 1),
    "SI": date(2002, 12, 1),
    "SK": date(2002, 7, 1),
    "SM": date(2009, 7, 1),
    "TR": date(2000, 11, 1),
}

PCT_CODES = tuple(
    "AE AG AL AM AO AT AU AZ BA BB BE BF BG BH BJ BN BR BW BY BZ CA CF CG CH CI CL CM "
    "CN CO CR CU CV CY CZ DE DJ DK DM DO DZ EC EE EG ES FI FR GA GB GD GE GH GM GN GQ "
    "GR GT GW HN HR HU ID IE IL IN IQ IR IS IT JM JO JP KE KG KH KM KN KP KR KW KZ LA "
    "LC LI LK LR LS LT LU LV LY MA MC MD ME MG MK ML MN MR MT MU MW MX MY MZ NA NE NG "
    "NI NL NO NZ OM PA PE PG PH PL PT QA RO RS RU RW SA SC SD SE SG SI SK SL SM SN ST "
    "SV SY SZ TD TG TH TJ TM TN TR TT TZ UA UG US UY UZ VC VN WS ZA ZM ZW"
    .split()
)

PARIS_EXTRA_CODES = tuple("AF AD AR BS BD BT BO BI CD ET FJ GY HT VA KI LB NP PK PY SR TO VE YE".split())
PARIS_CODES = tuple(dict.fromkeys([*PCT_CODES, *PARIS_EXTRA_CODES]))
EPC_CODES = tuple("AL AT BE BG CH CY CZ DE DK EE ES FI FR GB GR HR HU IE IS IT LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS SE SI SK SM TR".split())
EU_MEMBER_CODES = tuple("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())


def official_baseline_members(system_code: str | None = None) -> list[OfficialMemberSeed]:
    systems = (_normalize_system(system_code),) if system_code else ("PCT", "PARIS", "EPC", "EU_DESIGN")
    result: list[OfficialMemberSeed] = []
    for code in systems:
        if code == "PCT":
            result.extend(_build_members("PCT", PCT_CODES, PCT_SOURCE_NAME, PCT_SOURCE_URL, PCT_EFFECTIVE_DATES))
        elif code == "PARIS":
            result.extend(_build_members("PARIS", PARIS_CODES, PARIS_SOURCE_NAME, PARIS_SOURCE_URL, PARIS_EFFECTIVE_DATES))
        elif code == "EPC":
            result.extend(_build_members("EPC", EPC_CODES, EPC_SOURCE_NAME, EPC_SOURCE_URL, EPC_EFFECTIVE_DATES))
        elif code == "EU_DESIGN":
            result.extend(_build_members(
                "EU_DESIGN",
                EU_MEMBER_CODES,
                EU_DESIGN_SOURCE_NAME,
                EU_DESIGN_SOURCE_URL,
                {},
                "按欧盟成员资格适用。",
            ))
    return result


def official_baseline_count(system_code: str) -> int:
    return len(official_baseline_members(system_code))


def official_baseline_source(system_code: str) -> tuple[str, str]:
    normalized = _normalize_system(system_code)
    if normalized == "PCT":
        return PCT_SOURCE_NAME, PCT_SOURCE_URL
    if normalized == "PARIS":
        return PARIS_SOURCE_NAME, PARIS_SOURCE_URL
    if normalized == "EPC":
        return EPC_SOURCE_NAME, EPC_SOURCE_URL
    if normalized == "EU_DESIGN":
        return EU_DESIGN_SOURCE_NAME, EU_DESIGN_SOURCE_URL
    return "", ""


def _build_members(
    system_code: str,
    codes: tuple[str, ...],
    source_name: str,
    source_url: str,
    effective_dates: dict[str, date],
    remark: str = "",
) -> list[OfficialMemberSeed]:
    result: list[OfficialMemberSeed] = []
    for index, code in enumerate(codes, start=1):
        name_zh, name_en = COUNTRY_NAMES.get(code, (code, code))
        result.append(
            OfficialMemberSeed(
                system_code=system_code,
                jurisdiction_code=code,
                name_zh=name_zh,
                name_en=name_en,
                effective_date=effective_dates.get(code),
                source_name=source_name,
                source_url=source_url,
                remark=remark,
                display_order=index * 10,
            )
        )
    return result


def _normalize_system(system_code: str | None) -> str:
    return (system_code or "").strip().upper().replace("-", "_").replace("EUIPO", "EU_DESIGN")
