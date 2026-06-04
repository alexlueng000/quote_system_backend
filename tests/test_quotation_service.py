from decimal import Decimal

from app.schemas.quotation import QuotationCreate, QuotationGenerateRequest
from app.services.quotation_service import create_quotation, generate_quotation


def test_generate_quotation_contains_translation_in_application_stage() -> None:
    payload = QuotationGenerateRequest(
        client_name="测试客户",
        consultant_email="suri@example.com",
        country_code="US",
        application_type="发明",
        filing_route="PCT进入",
        currency="USD",
        needs_translation=True,
        translation_quantity_one=Decimal("1200"),
        translation_quantity_two=Decimal("3"),
    )

    generated = generate_quotation(payload)

    translation_items = [item for item in generated.items if item.fee_type == "翻译费"]
    assert translation_items
    assert all(item.stage == "申请阶段" for item in translation_items)


def test_create_quotation_generates_stable_number(monkeypatch) -> None:
    payload = QuotationCreate(
        client_name="测试客户",
        consultant_email="suri@example.com",
        country_code="US",
        application_type="发明",
        filing_route="PCT进入",
        currency="USD",
    )

    monkeypatch.setattr(
        "app.services.quotation_service.mysql.fetch_user_by_email",
        lambda email: {
            "id": "u-consultant",
            "name": "Suri",
            "email": email,
            "role": "consultant",
            "status": "active",
        },
    )
    monkeypatch.setattr(
        "app.services.quotation_service.mysql.insert_quotation",
        lambda record, items: None,
    )

    quotation = create_quotation(payload)

    assert quotation.quotation_no.endswith(quotation.quotation_no.split("-")[-1])
    assert quotation.status == "已生成报价"
