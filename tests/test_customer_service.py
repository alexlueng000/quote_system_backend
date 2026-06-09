from datetime import datetime, timezone

import pytest

from app.schemas.quotation import CustomerContactCreate, CustomerCreate
from app.services.customer_service import create_customer, get_customer


def test_create_customer_assigns_current_consultant_and_primary_contact(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    current_user = {
        "id": "u-consultant",
        "name": "Suri",
        "email": "suri@example.com",
        "role": "consultant",
        "status": "active",
    }
    saved: dict[str, object] = {}

    def fake_insert(record: dict[str, object], contacts: list[dict[str, object]]) -> None:
        saved["record"] = record
        saved["contacts"] = contacts

    def fake_fetch(customer_id: str) -> dict[str, object]:
        record = dict(saved["record"])  # type: ignore[arg-type]
        record["created_at"] = now
        record["updated_at"] = now
        record["contacts"] = saved["contacts"]
        return record

    monkeypatch.setattr("app.services.customer_service.mysql.insert_customer", fake_insert)
    monkeypatch.setattr("app.services.customer_service.mysql.fetch_customer", fake_fetch)

    customer = create_customer(
        CustomerCreate(
            name="测试客户",
            contacts=[CustomerContactCreate(name="Lina", email="lina@example.com")],
        ),
        current_user,
    )

    assert customer.customer_no.startswith("C")
    assert customer.consultant_email == "suri@example.com"
    assert customer.contacts[0].name == "Lina"
    assert customer.contacts[0].is_primary is True


def test_get_customer_blocks_other_consultant(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    current_user = {
        "id": "u-other",
        "name": "Other",
        "email": "other@example.com",
        "role": "consultant",
        "status": "active",
    }
    monkeypatch.setattr(
        "app.services.customer_service.mysql.fetch_customer",
        lambda customer_id: {
            "id": customer_id,
            "customer_no": "C20260606-ZYIP-TEST",
            "name": "测试客户",
            "customer_type": "企业",
            "consultant_id": "u-consultant",
            "consultant_email": "suri@example.com",
            "consultant_name": "Suri",
            "department": "",
            "default_currency": "CNY",
            "default_quote_terms": "",
            "customer_level": "普通",
            "status": "active",
            "remark": "",
            "created_at": now,
            "updated_at": now,
            "contacts": [],
        },
    )

    with pytest.raises(PermissionError):
        get_customer("customer-1", current_user)
