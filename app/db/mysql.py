from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pymysql
from dotenv import load_dotenv
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from app.schemas.quotation import QuotationItem


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_connection() -> Connection:
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "quote_system"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


@contextmanager
def connection_scope() -> Iterator[Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all_users() -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name, email, role, status FROM users ORDER BY role, name")
        return list(cursor.fetchall())


def fetch_user_by_id(user_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, email, role, status FROM users WHERE id = %s LIMIT 1",
            (user_id,),
        )
        return cursor.fetchone()


def fetch_user_by_email(email: str | None) -> dict[str, object] | None:
    if not email:
        return None
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, email, role, status FROM users WHERE email = %s LIMIT 1",
            (email,),
        )
        return cursor.fetchone()


def insert_user(values: dict[str, object]) -> dict[str, object]:
    user_id = str(uuid.uuid4())
    record = {"id": user_id, **values}
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (id, name, email, password_hash, role, status)
            VALUES (%(id)s, %(name)s, %(email)s, %(password_hash)s, %(role)s, %(status)s)
            """,
            record,
        )
    user = fetch_user_by_id(user_id)
    if user is None:
        raise KeyError(user_id)
    return user


def update_user(user_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {"name", "email", "role", "status"}
    updates = {key: value for key, value in values.items() if key in allowed}
    if updates:
        assignments = ", ".join(f"{key} = %s" for key in updates)
        params = tuple(updates.values()) + (user_id,)
        with connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE users SET {assignments} WHERE id = %s",
                params,
            )
            if cursor.rowcount == 0:
                raise KeyError(user_id)
    user = fetch_user_by_id(user_id)
    if user is None:
        raise KeyError(user_id)
    return user


def update_user_password(user_id: str, password_hash: str) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(user_id)
    user = fetch_user_by_id(user_id)
    if user is None:
        raise KeyError(user_id)
    return user


def fetch_followups(quotation_id: str) -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT f.id, f.quotation_id, f.user_id, u.name AS user_name,
                   f.followup_date, f.method, f.content, f.next_followup_date, f.created_at
            FROM quotation_followups f
            JOIN users u ON u.id = f.user_id
            WHERE f.quotation_id = %s
            ORDER BY f.followup_date DESC, f.created_at DESC
            """,
            (quotation_id,),
        )
        return list(cursor.fetchall())


def insert_followup(values: dict[str, object]) -> dict[str, object]:
    followup_id = str(uuid.uuid4())
    record = {"id": followup_id, **values}
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO quotation_followups (
              id, quotation_id, user_id, method, content, next_followup_date
            )
            VALUES (
              %(id)s, %(quotation_id)s, %(user_id)s, %(method)s, %(content)s,
              %(next_followup_date)s
            )
            """,
            record,
        )
    followups = fetch_followups(str(values["quotation_id"]))
    for followup in followups:
        if followup["id"] == followup_id:
            return followup
    raise KeyError(followup_id)


def fetch_auth_user_by_email(email: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, email, password_hash, role, status
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email,),
        )
        return cursor.fetchone()


def fetch_countries() -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT code, name_cn, name_en, default_currency, enabled
            FROM countries
            WHERE enabled = 1
            ORDER BY code
            """
        )
        return list(cursor.fetchall())


def fetch_fee_rules(include_inactive: bool = False) -> list[dict[str, object]]:
    active_filter = "" if include_inactive else "WHERE is_active = 1"
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, country_code, application_type, filing_route, stage, item_name,
                   fee_type, amount, currency, is_default, is_active, cost_nature, remark
            FROM fee_rules
            {active_filter}
            ORDER BY country_code, application_type, filing_route, sort_order, id
            """
        )
        return list(cursor.fetchall())


def fetch_translation_rules(include_disabled: bool = False) -> list[dict[str, object]]:
    enabled_filter = "" if include_disabled else "WHERE enabled = 1"
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, item_name, unit, unit_price, currency, min_fee, enabled, is_default
            FROM translation_rules
            {enabled_filter}
            ORDER BY sort_order, id
            """
        )
        return list(cursor.fetchall())


def update_fee_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {"amount", "currency", "is_default", "is_active", "remark"}
    updates = {key: value for key, value in values.items() if key in allowed}
    if updates:
        assignments = ", ".join(f"{key} = %s" for key in updates)
        params = tuple(updates.values()) + (rule_id,)
        with connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE fee_rules SET {assignments} WHERE id = %s",
                params,
            )
            if cursor.rowcount == 0:
                raise KeyError(rule_id)
    rule = fetch_fee_rule(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    return rule


def fetch_fee_rule(rule_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, country_code, application_type, filing_route, stage, item_name,
                   fee_type, amount, currency, is_default, is_active, cost_nature, remark
            FROM fee_rules
            WHERE id = %s
            LIMIT 1
            """,
            (rule_id,),
        )
        return cursor.fetchone()


def update_translation_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {"item_name", "unit", "unit_price", "currency", "min_fee", "enabled", "is_default"}
    updates = {key: value for key, value in values.items() if key in allowed}
    if updates:
        assignments = ", ".join(f"{key} = %s" for key in updates)
        params = tuple(updates.values()) + (rule_id,)
        with connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE translation_rules SET {assignments} WHERE id = %s",
                params,
            )
            if cursor.rowcount == 0:
                raise KeyError(rule_id)
    rule = fetch_translation_rule(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    return rule


def fetch_translation_rule(rule_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, item_name, unit, unit_price, currency, min_fee, enabled, is_default
            FROM translation_rules
            WHERE id = %s
            LIMIT 1
            """,
            (rule_id,),
        )
        return cursor.fetchone()


def insert_quotation(
    record: dict[str, object],
    items: list[QuotationItem],
) -> None:
    quotation_record = {key: value for key, value in record.items() if key != "items"}
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO quotations (
              id, quotation_no, consultant_id, consultant_email, consultant_name,
              client_name, client_contact, country_code, application_type, filing_route,
              currency, has_case, case_title, applicant_count, priority_count, claim_count,
              description_pages, drawing_pages, needs_translation, translation_quantity_one,
              translation_quantity_two, current_stage_total, future_stage_total, total_amount,
              status, is_sent, is_confirmed, is_opened, opened_reference, remark,
              created_at, updated_at
            )
            VALUES (
              %(id)s, %(quotation_no)s, %(consultant_id)s, %(consultant_email)s, %(consultant_name)s,
              %(client_name)s, %(client_contact)s, %(country_code)s, %(application_type)s, %(filing_route)s,
              %(currency)s, %(has_case)s, %(case_title)s, %(applicant_count)s, %(priority_count)s, %(claim_count)s,
              %(description_pages)s, %(drawing_pages)s, %(needs_translation)s, %(translation_quantity_one)s,
              %(translation_quantity_two)s, %(current_stage_total)s, %(future_stage_total)s, %(total_amount)s,
              %(status)s, %(is_sent)s, %(is_confirmed)s, %(is_opened)s, %(opened_reference)s, %(remark)s,
              %(created_at)s, %(updated_at)s
            )
            """,
            quotation_record,
        )
        for item in items:
            cursor.execute(
                """
                INSERT INTO quotation_items (
                  id, quotation_id, stage, item_name, fee_type, amount, currency,
                  cost_nature, remark, sort_order
                )
                VALUES (
                  %(id)s, %(quotation_id)s, %(stage)s, %(item_name)s, %(fee_type)s,
                  %(amount)s, %(currency)s, %(cost_nature)s, %(remark)s, %(sort_order)s
                )
                """,
                {
                    "id": item.id,
                    "quotation_id": record["id"],
                    "stage": item.stage,
                    "item_name": item.item_name,
                    "fee_type": item.fee_type,
                    "amount": item.amount,
                    "currency": item.currency,
                    "cost_nature": item.cost_nature,
                    "remark": item.remark,
                    "sort_order": item.sort_order,
                },
            )


def fetch_quotation(quotation_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM quotations
            WHERE id = %s
            LIMIT 1
            """,
            (quotation_id,),
        )
        quotation = cursor.fetchone()
        if not quotation:
            return None
        quotation["items"] = _fetch_items(cursor, quotation_id)
        return quotation


def fetch_quotations(user_email: str | None) -> list[dict[str, object]]:
    user = fetch_user_by_email(user_email)
    params: tuple[object, ...] = ()
    where = ""
    if user and user["role"] == "consultant":
        where = "WHERE consultant_email = %s"
        params = (user["email"],)

    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM quotations
            {where}
            ORDER BY created_at DESC
            LIMIT 200
            """,
            params,
        )
        quotations = list(cursor.fetchall())
        for quotation in quotations:
            quotation["items"] = _fetch_items(cursor, str(quotation["id"]))
        return quotations


def update_quotation_status(quotation_id: str, status: str) -> None:
    is_sent = status in {"已发送客户", "跟进中", "已确认", "已开卷"}
    is_confirmed = status in {"已确认", "已开卷"}
    is_opened = status == "已开卷"
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE quotations
            SET status = %s,
                is_sent = %s,
                is_confirmed = %s,
                is_opened = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (status, is_sent, is_confirmed, is_opened, datetime.now(), quotation_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(quotation_id)


def fetch_statistics(user_email: str | None = None) -> dict[str, object]:
    user = fetch_user_by_email(user_email)
    where = ""
    params: tuple[object, ...] = ()
    if user and user["role"] == "consultant":
        where = "WHERE consultant_email = %s"
        params = (user["email"],)

    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              COUNT(*) AS quote_count,
              COALESCE(SUM(current_stage_total), 0) AS current_stage_total,
              COALESCE(SUM(future_stage_total), 0) AS future_stage_total,
              COALESCE(SUM(total_amount), 0) AS total_amount,
              COALESCE(SUM(is_sent), 0) AS sent_count,
              COALESCE(SUM(is_confirmed), 0) AS confirmed_count,
              COALESCE(SUM(is_opened), 0) AS opened_count,
              COALESCE(SUM(status = '未成交'), 0) AS lost_count
            FROM quotations
            {where}
            """
            ,
            params,
        )
        row = cursor.fetchone() or {}
        quote_count = int(row.get("quote_count") or 0)
        opened_count = int(row.get("opened_count") or 0)
        row["open_rate"] = Decimal(opened_count) / Decimal(quote_count) if quote_count else Decimal("0")
        return row


def _fetch_items(cursor: DictCursor, quotation_id: str) -> list[dict[str, object]]:
    cursor.execute(
        """
        SELECT id, stage, item_name, fee_type, amount, currency, cost_nature, remark, sort_order
        FROM quotation_items
        WHERE quotation_id = %s
        ORDER BY sort_order, id
        """,
        (quotation_id,),
    )
    return list(cursor.fetchall())
