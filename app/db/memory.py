from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class UserRecord:
    id: str
    name: str
    email: str
    role: str
    status: str


@dataclass(frozen=True)
class CountryRecord:
    code: str
    name_cn: str
    name_en: str
    default_currency: str
    enabled: bool


@dataclass(frozen=True)
class FeeRuleRecord:
    id: str
    country_code: str
    application_type: str
    filing_route: str
    stage: str
    item_name: str
    fee_type: str
    amount: Decimal
    currency: str
    is_default: bool
    cost_nature: str
    remark: str = ""


@dataclass(frozen=True)
class TranslationRuleRecord:
    id: str
    item_name: str
    unit: str
    unit_price: Decimal
    currency: str
    min_fee: Decimal
    enabled: bool
    is_default: bool


@dataclass
class MemoryStore:
    users: list[UserRecord] = field(default_factory=list)
    countries: list[CountryRecord] = field(default_factory=list)
    fee_rules: list[FeeRuleRecord] = field(default_factory=list)
    translation_rules: list[TranslationRuleRecord] = field(default_factory=list)
    quotations: dict[str, dict[str, object]] = field(default_factory=dict)


store = MemoryStore(
    users=[
        UserRecord("u-consultant", "Suri", "suri@example.com", "consultant", "active"),
        UserRecord("u-admin", "管理员", "admin@example.com", "admin", "active"),
    ],
    countries=[
        CountryRecord("US", "美国", "United States", "USD", True),
        CountryRecord("EP", "欧洲", "Europe", "EUR", True),
        CountryRecord("JP", "日本", "Japan", "JPY", True),
        CountryRecord("KR", "韩国", "Korea", "KRW", True),
    ],
    fee_rules=[
        FeeRuleRecord(
            "us-official-application",
            "US",
            "发明",
            "PCT进入",
            "申请阶段",
            "官方申请费",
            "官方费",
            Decimal("1720"),
            "USD",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "us-foreign-service",
            "US",
            "发明",
            "PCT进入",
            "申请阶段",
            "外所申请服务费",
            "外所费",
            Decimal("950"),
            "USD",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "us-local-service",
            "US",
            "发明",
            "PCT进入",
            "申请阶段",
            "本所申请服务费",
            "本所费",
            Decimal("4200"),
            "CNY",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "us-exam",
            "US",
            "发明",
            "PCT进入",
            "审查阶段",
            "请求实质审查费",
            "官方费",
            Decimal("880"),
            "USD",
            True,
            "后续预估",
            "后续发生时确认",
        ),
        FeeRuleRecord(
            "us-grant",
            "US",
            "发明",
            "PCT进入",
            "授权阶段",
            "授权登记费",
            "官方费",
            Decimal("1200"),
            "USD",
            True,
            "后续预估",
            "授权时确认",
        ),
        FeeRuleRecord(
            "ep-official-application",
            "EP",
            "发明",
            "PCT进入",
            "申请阶段",
            "官方申请费",
            "官方费",
            Decimal("1495"),
            "EUR",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "ep-foreign-service",
            "EP",
            "发明",
            "PCT进入",
            "申请阶段",
            "外所申请服务费",
            "外所费",
            Decimal("1100"),
            "EUR",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "ep-local-service",
            "EP",
            "发明",
            "PCT进入",
            "申请阶段",
            "本所申请服务费",
            "本所费",
            Decimal("4800"),
            "CNY",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "ep-exam",
            "EP",
            "发明",
            "PCT进入",
            "审查阶段",
            "审查阶段预估费用",
            "官方费",
            Decimal("1915"),
            "EUR",
            True,
            "后续预估",
            "后续发生时确认",
        ),
        FeeRuleRecord(
            "jp-official-application",
            "JP",
            "发明",
            "巴黎公约",
            "申请阶段",
            "官方申请费",
            "官方费",
            Decimal("14000"),
            "JPY",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "jp-foreign-service",
            "JP",
            "发明",
            "巴黎公约",
            "申请阶段",
            "外所申请服务费",
            "外所费",
            Decimal("120000"),
            "JPY",
            True,
            "当前费用",
        ),
        FeeRuleRecord(
            "jp-local-service",
            "JP",
            "发明",
            "巴黎公约",
            "申请阶段",
            "本所申请服务费",
            "本所费",
            Decimal("3800"),
            "CNY",
            True,
            "当前费用",
        ),
    ],
    translation_rules=[
        TranslationRuleRecord(
            "translation-main",
            "申请文件翻译费",
            "词",
            Decimal("0.9"),
            "CNY",
            Decimal("800"),
            True,
            True,
        ),
        TranslationRuleRecord(
            "translation-drawing",
            "附图文字翻译/校对费",
            "页",
            Decimal("120"),
            "CNY",
            Decimal("300"),
            True,
            True,
        ),
    ],
)

