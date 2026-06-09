from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db import mysql
from app.schemas.quotation import (
    CustomerContactCreate,
    CustomerContactResponse,
    CustomerContactUpdate,
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)


def get_customers(
    current_user: dict[str, object],
    keyword: str | None = None,
) -> CustomerListResponse:
    consultant_email = None
    if current_user["role"] == "consultant":
        consultant_email = str(current_user["email"])
    customers = [
        CustomerResponse.model_validate(row)
        for row in mysql.fetch_customers(consultant_email=consultant_email, keyword=keyword)
    ]
    return CustomerListResponse(items=customers, total=len(customers))


def get_customer(
    customer_id: str,
    current_user: dict[str, object],
) -> CustomerResponse:
    customer = mysql.fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    _ensure_customer_access(customer, current_user)
    return CustomerResponse.model_validate(customer)


def create_customer(
    payload: CustomerCreate,
    current_user: dict[str, object],
) -> CustomerResponse:
    consultant = _resolve_customer_consultant(payload.consultant_email, current_user)
    now = datetime.now(timezone.utc)
    customer_id = str(uuid4())
    record: dict[str, object] = {
        "id": customer_id,
        "customer_no": f"C{now:%Y%m%d}-ZYIP-{uuid4().hex[:5].upper()}",
        "name": payload.name.strip(),
        "customer_type": payload.customer_type,
        "consultant_id": consultant["id"],
        "consultant_email": consultant["email"],
        "consultant_name": consultant["name"],
        "department": payload.department,
        "default_currency": payload.default_currency,
        "default_quote_terms": payload.default_quote_terms,
        "customer_level": payload.customer_level,
        "status": payload.status,
        "remark": payload.remark,
        "created_at": now,
        "updated_at": now,
    }
    contacts = [
        _contact_create_values(customer_id, contact, index, now)
        for index, contact in enumerate(payload.contacts)
    ]
    _ensure_one_primary_contact(contacts)
    mysql.insert_customer(record, contacts)
    saved = mysql.fetch_customer(customer_id)
    if saved is None:
        raise KeyError(customer_id)
    return CustomerResponse.model_validate(saved)


def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    current_user: dict[str, object],
) -> CustomerResponse:
    customer = mysql.fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    _ensure_customer_access(customer, current_user)
    values = payload.model_dump(exclude_unset=True)
    consultant_email = values.pop("consultant_email", None)
    if consultant_email:
        consultant = _resolve_customer_consultant(str(consultant_email), current_user)
        values["consultant_id"] = consultant["id"]
        values["consultant_email"] = consultant["email"]
        values["consultant_name"] = consultant["name"]
    elif consultant_email == "" and current_user["role"] == "admin":
        values["consultant_id"] = None
        values["consultant_email"] = ""
        values["consultant_name"] = ""
    updated = mysql.update_customer(customer_id, values)
    return CustomerResponse.model_validate(updated)


def create_customer_contact(
    customer_id: str,
    payload: CustomerContactCreate,
    current_user: dict[str, object],
) -> CustomerContactResponse:
    customer = mysql.fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    _ensure_customer_access(customer, current_user)
    contact = _contact_create_values(customer_id, payload, 0, datetime.now(timezone.utc))
    saved = mysql.insert_customer_contact(contact)
    return CustomerContactResponse.model_validate(saved)


def update_customer_contact(
    customer_id: str,
    contact_id: str,
    payload: CustomerContactUpdate,
    current_user: dict[str, object],
) -> CustomerContactResponse:
    customer = mysql.fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    _ensure_customer_access(customer, current_user)
    values = payload.model_dump(exclude_unset=True)
    contact = mysql.update_customer_contact(customer_id, contact_id, values)
    return CustomerContactResponse.model_validate(contact)


def delete_customer_contact(
    customer_id: str,
    contact_id: str,
    current_user: dict[str, object],
) -> CustomerResponse:
    customer = mysql.fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    _ensure_customer_access(customer, current_user)
    updated = mysql.delete_customer_contact(customer_id, contact_id)
    return CustomerResponse.model_validate(updated)


def _resolve_customer_consultant(
    consultant_email: str | None,
    current_user: dict[str, object],
) -> dict[str, object]:
    if current_user["role"] == "admin" and consultant_email:
        user = mysql.fetch_user_by_email(consultant_email)
        if user is None or user["status"] != "active" or user["role"] != "consultant":
            raise KeyError(f"CONSULTANT_NOT_FOUND:{consultant_email}")
        return user
    if current_user["role"] == "admin":
        return {
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        }
    return current_user


def _ensure_customer_access(
    customer: dict[str, object],
    current_user: dict[str, object],
) -> None:
    if current_user["role"] == "admin":
        return
    if (
        current_user["role"] == "consultant"
        and customer["consultant_email"] == current_user["email"]
    ):
        return
    raise PermissionError("CUSTOMER_FORBIDDEN")


def _contact_create_values(
    customer_id: str,
    contact: CustomerContactCreate,
    index: int,
    now: datetime,
) -> dict[str, object]:
    return {
        "id": f"{customer_id}-contact-{index + 1:03d}-{uuid4().hex[:4]}",
        "customer_id": customer_id,
        "name": contact.name.strip(),
        "title": contact.title,
        "email": contact.email,
        "phone": contact.phone,
        "wechat": contact.wechat,
        "is_primary": contact.is_primary,
        "remark": contact.remark,
        "created_at": now,
        "updated_at": now,
    }


def _ensure_one_primary_contact(contacts: list[dict[str, object]]) -> None:
    if not contacts:
        return
    if any(contact["is_primary"] for contact in contacts):
        return
    contacts[0]["is_primary"] = True
