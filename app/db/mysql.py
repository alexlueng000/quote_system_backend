from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import pymysql
from dotenv import load_dotenv
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from app.reference.jurisdiction_registry import default_registry_items
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
        init_command="SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
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
        return _normalize_text_records(cursor.fetchall())


def fetch_user_by_id(user_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, email, role, status FROM users WHERE id = %s LIMIT 1",
            (user_id,),
        )
        return _normalize_text_record(cursor.fetchone())


def fetch_user_by_email(email: str | None) -> dict[str, object] | None:
    if not email:
        return None
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, email, role, status FROM users WHERE email = %s LIMIT 1",
            (email,),
        )
        return _normalize_text_record(cursor.fetchone())


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
        return _normalize_text_record(cursor.fetchone())


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
            cursor.execute(f"UPDATE users SET {assignments} WHERE id = %s", params)
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


def fetch_customers(
    consultant_email: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, object]]:
    where_parts: list[str] = []
    params: list[object] = []
    if consultant_email:
        where_parts.append("consultant_email = %s")
        params.append(consultant_email)
    if keyword:
        like = f"%{keyword}%"
        where_parts.append("(customer_no LIKE %s OR name LIKE %s OR consultant_name LIKE %s)")
        params.extend([like, like, like])
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM customers
            {where}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 200
            """,
            tuple(params),
        )
        customers = _normalize_text_records(cursor.fetchall())
        for customer in customers:
            _normalize_customer(customer)
            customer["contacts"] = _fetch_customer_contacts(cursor, str(customer["id"]))
        return customers


def fetch_customer(customer_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM customers WHERE id = %s LIMIT 1", (customer_id,))
        customer = _normalize_text_record(cursor.fetchone())
        if not customer:
            return None
        _normalize_customer(customer)
        customer["contacts"] = _fetch_customer_contacts(cursor, customer_id)
        return customer


def insert_customer(
    record: dict[str, object],
    contacts: list[dict[str, object]],
) -> None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO customers (
              id, customer_no, name, customer_type, consultant_id, consultant_email,
              consultant_name, department, default_currency, default_quote_terms,
              customer_level, status, remark, created_at, updated_at
            )
            VALUES (
              %(id)s, %(customer_no)s, %(name)s, %(customer_type)s, %(consultant_id)s,
              %(consultant_email)s, %(consultant_name)s, %(department)s,
              %(default_currency)s, %(default_quote_terms)s, %(customer_level)s,
              %(status)s, %(remark)s, %(created_at)s, %(updated_at)s
            )
            """,
            record,
        )
        for contact in contacts:
            _insert_customer_contact(cursor, contact)


def update_customer(customer_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "name",
        "customer_type",
        "consultant_id",
        "consultant_email",
        "consultant_name",
        "department",
        "default_currency",
        "default_quote_terms",
        "customer_level",
        "status",
        "remark",
    }
    updates = {key: value for key, value in values.items() if key in allowed}
    with connection_scope() as connection, connection.cursor() as cursor:
        if updates:
            updates["updated_at"] = datetime.now()
            assignments = ", ".join(f"{key} = %s" for key in updates)
            params = tuple(updates.values()) + (customer_id,)
            cursor.execute(f"UPDATE customers SET {assignments} WHERE id = %s", params)
            if cursor.rowcount == 0:
                raise KeyError(customer_id)
        else:
            cursor.execute("SELECT id FROM customers WHERE id = %s LIMIT 1", (customer_id,))
            if cursor.fetchone() is None:
                raise KeyError(customer_id)
    customer = fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    return customer


def insert_customer_contact(contact: dict[str, object]) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if contact["is_primary"]:
            cursor.execute(
                """
                UPDATE customer_contacts
                SET is_primary = 0, updated_at = %s
                WHERE customer_id = %s
                """,
                (datetime.now(), contact["customer_id"]),
            )
        _insert_customer_contact(cursor, contact)
        cursor.execute(
            "UPDATE customers SET updated_at = %s WHERE id = %s",
            (datetime.now(), contact["customer_id"]),
        )
    saved = fetch_customer_contact(str(contact["customer_id"]), str(contact["id"]))
    if saved is None:
        raise KeyError(str(contact["id"]))
    return saved


def fetch_customer_contact(customer_id: str, contact_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM customer_contacts
            WHERE id = %s AND customer_id = %s
            LIMIT 1
            """,
            (contact_id, customer_id),
        )
        return cursor.fetchone()


def update_customer_contact(
    customer_id: str,
    contact_id: str,
    values: dict[str, object],
) -> dict[str, object]:
    allowed = {"name", "title", "email", "phone", "wechat", "is_primary", "remark"}
    updates = {key: value for key, value in values.items() if key in allowed}
    with connection_scope() as connection, connection.cursor() as cursor:
        if updates:
            if updates.get("is_primary"):
                cursor.execute(
                    """
                    UPDATE customer_contacts
                    SET is_primary = 0, updated_at = %s
                    WHERE customer_id = %s AND id <> %s
                    """,
                    (datetime.now(), customer_id, contact_id),
                )
            updates["updated_at"] = datetime.now()
            assignments = ", ".join(f"{key} = %s" for key in updates)
            params = tuple(updates.values()) + (contact_id, customer_id)
            cursor.execute(
                f"""
                UPDATE customer_contacts
                SET {assignments}
                WHERE id = %s AND customer_id = %s
                """,
                params,
            )
            if cursor.rowcount == 0:
                raise KeyError(contact_id)
            cursor.execute(
                "UPDATE customers SET updated_at = %s WHERE id = %s",
                (datetime.now(), customer_id),
            )
        else:
            cursor.execute(
                "SELECT id FROM customer_contacts WHERE id = %s AND customer_id = %s LIMIT 1",
                (contact_id, customer_id),
            )
            if cursor.fetchone() is None:
                raise KeyError(contact_id)
    contact = fetch_customer_contact(customer_id, contact_id)
    if contact is None:
        raise KeyError(contact_id)
    return contact


def delete_customer_contact(customer_id: str, contact_id: str) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM customer_contacts WHERE id = %s AND customer_id = %s",
            (contact_id, customer_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(contact_id)
        cursor.execute(
            "UPDATE customers SET updated_at = %s WHERE id = %s",
            (datetime.now(), customer_id),
        )
    customer = fetch_customer(customer_id)
    if customer is None:
        raise KeyError(customer_id)
    return customer


def fetch_countries() -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        deleted_filter = "AND COALESCE(is_deleted, 0) = 0" if _column_exists(cursor, "countries", "is_deleted") else ""
        cursor.execute(
            f"""
            SELECT code, name_cn, name_en, default_currency, enabled
            FROM countries
            WHERE enabled = 1
              {deleted_filter}
            ORDER BY code
            """
        )
        return _normalize_text_records(cursor.fetchall())


def fetch_country_config(include_deleted: bool = False) -> dict[str, list[dict[str, object]]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if _jurisdiction_compat_available(cursor):
            country_has_deleted = _column_exists(cursor, "countries", "is_deleted")
            jurisdiction_has_deleted = _column_exists(cursor, "jurisdictions", "is_deleted")
            if country_has_deleted and jurisdiction_has_deleted:
                deleted_filter = "COALESCE(c.is_deleted, 0) = 0 AND COALESCE(j.is_deleted, 0) = 0"
                country_deleted_expr = "CASE WHEN COALESCE(c.is_deleted, 0) = 1 OR COALESCE(j.is_deleted, 0) = 1 THEN 1 ELSE 0 END AS is_deleted"
            elif country_has_deleted:
                deleted_filter = "COALESCE(c.is_deleted, 0) = 0"
                country_deleted_expr = "COALESCE(c.is_deleted, 0) AS is_deleted"
            elif jurisdiction_has_deleted:
                deleted_filter = "COALESCE(j.is_deleted, 0) = 0"
                country_deleted_expr = "COALESCE(j.is_deleted, 0) AS is_deleted"
            else:
                deleted_filter = "c.enabled = 1 AND COALESCE(j.is_enabled, c.enabled) = 1"
                country_deleted_expr = "CASE WHEN c.enabled = 0 OR COALESCE(j.is_enabled, c.enabled) = 0 THEN 1 ELSE 0 END AS is_deleted"
            if include_deleted:
                deleted_filter = "1 = 1"
            deleted_at_expr = (
                "COALESCE(j.deleted_at, c.deleted_at) AS deleted_at"
                if _column_exists(cursor, "countries", "deleted_at") and _column_exists(cursor, "jurisdictions", "deleted_at")
                else "NULL AS deleted_at"
            )
            deleted_by_expr = (
                "COALESCE(j.deleted_by, c.deleted_by, '') AS deleted_by"
                if _column_exists(cursor, "countries", "deleted_by") and _column_exists(cursor, "jurisdictions", "deleted_by")
                else "'' AS deleted_by"
            )
            delete_reason_expr = (
                "COALESCE(j.delete_reason, c.delete_reason, '') AS delete_reason"
                if _column_exists(cursor, "countries", "delete_reason") and _column_exists(cursor, "jurisdictions", "delete_reason")
                else "'' AS delete_reason"
            )
            source_verified_expr = (
                "COALESCE(j.source_verified, 0) AS source_verified"
                if _column_exists(cursor, "jurisdictions", "source_verified")
                else "CASE WHEN j.last_verified_at IS NULL THEN 0 ELSE 1 END AS source_verified"
            )
            source_verified_at_expr = (
                "j.source_verified_at"
                if _column_exists(cursor, "jurisdictions", "source_verified_at")
                else "j.last_verified_at AS source_verified_at"
            )
            source_verified_by_expr = (
                "COALESCE(j.source_verified_by, '') AS source_verified_by"
                if _column_exists(cursor, "jurisdictions", "source_verified_by")
                else "'' AS source_verified_by"
            )
            standard_code_expr = (
                "COALESCE(j.standard_code, j.internal_code, c.code) AS standard_code"
                if _column_exists(cursor, "jurisdictions", "standard_code")
                else "COALESCE(j.internal_code, c.code) AS standard_code"
            )
            source_note_expr = (
                "COALESCE(j.source_note, '') AS source_note"
                if _column_exists(cursor, "jurisdictions", "source_note")
                else "'' AS source_note"
            )
            cursor.execute(
                f"""
                SELECT c.code, c.name_cn, c.name_en, c.default_currency,
                       c.country_type, c.enabled, c.display_order,
                       c.international_region, c.business_region, c.region_remark,
                       j.jurisdiction_id,
                       COALESCE(j.internal_code, c.code) AS internal_code,
                       {standard_code_expr},
                       COALESCE(j.display_code, c.code) AS display_code,
                       COALESCE(j.jurisdiction_type, c.country_type, '') AS jurisdiction_type,
                       COALESCE(j.is_enabled, c.enabled) AS is_enabled,
                       j.iso_alpha2, j.iso_alpha3, j.iso_numeric, j.un_m49_code,
                       j.wipo_st3_code, COALESCE(j.source_name, '') AS source_name,
                       COALESCE(j.source_url, '') AS source_url,
                       COALESCE(j.source_version, '') AS source_version,
                       {source_note_expr},
                       j.last_verified_at,
                       {source_verified_expr},
                       {source_verified_at_expr},
                       {source_verified_by_expr},
                       COALESCE(j.manual_override, 0) AS manual_override,
                       COALESCE(j.remarks, '') AS remarks,
                       {country_deleted_expr},
                       {deleted_at_expr},
                       {deleted_by_expr},
                       {delete_reason_expr}
                FROM countries c
                LEFT JOIN country_jurisdiction_map m ON m.country_code = c.code
                LEFT JOIN jurisdictions j ON j.jurisdiction_id = COALESCE(c.jurisdiction_id, m.jurisdiction_id)
                WHERE {deleted_filter}
                ORDER BY c.display_order, c.code
                """
            )
        else:
            country_has_deleted = _column_exists(cursor, "countries", "is_deleted")
            deleted_select = (
                ", code AS standard_code, '' AS source_note, COALESCE(is_deleted, 0) AS is_deleted, deleted_at, COALESCE(deleted_by, '') AS deleted_by, COALESCE(delete_reason, '') AS delete_reason"
                if country_has_deleted
                else ", code AS standard_code, '' AS source_note, CASE WHEN enabled = 0 THEN 1 ELSE 0 END AS is_deleted, NULL AS deleted_at, '' AS deleted_by, '' AS delete_reason"
            )
            if include_deleted:
                deleted_where = ""
            elif country_has_deleted:
                deleted_where = "WHERE COALESCE(is_deleted, 0) = 0"
            else:
                deleted_where = "WHERE enabled = 1"
            cursor.execute(
                f"""
                SELECT code, name_cn, name_en, default_currency, country_type, enabled,
                       display_order, international_region, business_region, region_remark
                       {deleted_select}
                FROM countries
                {deleted_where}
                ORDER BY display_order, code
                """
            )
        countries = _normalize_text_records(cursor.fetchall())
        for country in countries:
            _apply_jurisdiction_country_defaults(country)
            country["business_region"] = _loads_json_list_or_legacy(country.get("business_region"))

        cursor.execute(
            """
            SELECT id, country_code, application_type, filing_route, route_detail,
                   affects_official_fee, affects_local_service_fee, affects_inhouse_service_fee,
                   affects_questions, affects_documents, affects_deadlines, affects_translation,
                   affects_display, enabled, effective_date, remark
            FROM country_path_rules
            ORDER BY country_code, application_type, filing_route, route_detail, id
            """
        )
        path_rules = _normalize_text_records(cursor.fetchall())

        cursor.execute(
            """
            SELECT id, country_code, application_type, filing_route, enabled,
                   entity_types_json, affects_official_fee, affects_questions,
                   requires_customer_confirmation, requires_supporting_documents, remark
            FROM entity_type_rules
            ORDER BY country_code, application_type, filing_route, id
            """
        )
        entity_type_rules = _normalize_text_records(cursor.fetchall())
        for rule in entity_type_rules:
            rule["entity_types"] = _loads_json_list(rule.pop("entity_types_json", None))

        cursor.execute(
            """
            SELECT id, country_code, application_type, accepted_languages_json,
                   source_language, target_language, intermediate_language,
                   needs_second_translation, recommended_scheme_id, default_translation_fee,
                   allow_scheme_switch, enabled, remark
            FROM language_rules
            ORDER BY country_code, application_type, id
            """
        )
        language_rules = _normalize_text_records(cursor.fetchall())
        for rule in language_rules:
            rule["accepted_languages"] = _loads_json_list(rule.pop("accepted_languages_json", None))

        cursor.execute(
            """
            SELECT id, country_code, official_currency, official_quote_currency,
                   local_service_currency, local_service_currency_options_json, quote_currency,
                   fx_rate, tax_rate, tax_included, lock_on_formal_quote, version, enabled, remark
            FROM fx_tax_rules
            ORDER BY country_code, quote_currency, id
            """
        )
        fx_tax_rules = _normalize_text_records(cursor.fetchall())
        for rule in fx_tax_rules:
            rule["local_service_currency_options"] = _loads_json_list(
                rule.pop("local_service_currency_options_json", None)
            )

        cursor.execute(
            """
            SELECT id, country_code, application_type, filing_route, rule_type, enabled,
                   triggers_extra_fee, triggers_risk_warning, requires_customer_confirmation,
                   risk_summary, linked_rule_code, remark
            FROM special_rules
            ORDER BY country_code, application_type, filing_route, rule_type, id
            """
        )
        special_rules = _normalize_text_records(cursor.fetchall())

        return {
            "countries": countries,
            "path_rules": path_rules,
            "entity_type_rules": entity_type_rules,
            "language_rules": language_rules,
            "fx_tax_rules": fx_tax_rules,
            "special_rules": special_rules,
        }


def fetch_quote_jurisdiction_options_preview(
    selectable_only: bool = False,
    business_line: str | None = None,
    option_group: str | None = None,
) -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdictions"):
            return []
        where_parts = ["j.is_enabled = 1"]
        params: list[object] = []
        if _column_exists(cursor, "jurisdictions", "is_deleted"):
            where_parts.append("COALESCE(j.is_deleted, 0) = 0")
        if selectable_only:
            where_parts.append(_quote_selectable_expr(cursor) + " = 1")
        if option_group:
            where_parts.append(_quote_option_group_expr(cursor) + " = %s")
            params.append(option_group)
        if business_line:
            where_parts.append(
                f"JSON_CONTAINS(COALESCE({_quote_business_lines_expr(cursor)}, JSON_ARRAY()), JSON_QUOTE(%s))"
            )
            params.append(business_line)

        standard_code_expr = (
            "COALESCE(NULLIF(j.standard_code, ''), j.internal_code)"
            if _column_exists(cursor, "jurisdictions", "standard_code")
            else "j.internal_code"
        )
        source_geo_expr = (
            "COALESCE(c.international_region, '') AS geo_region"
            if _column_exists(cursor, "countries", "international_region")
            else "'' AS geo_region"
        )
        business_region_expr = (
            "c.business_region AS business_economic_regions"
            if _column_exists(cursor, "countries", "business_region")
            else "NULL AS business_economic_regions"
        )
        cursor.execute(
            f"""
            SELECT j.jurisdiction_id,
                   {standard_code_expr} AS standard_code,
                   j.display_code,
                   {_quote_display_name_expr(cursor)} AS quote_display_name,
                   j.jurisdiction_type,
                   {_quote_option_group_expr(cursor)} AS quote_option_group,
                   {_quote_business_lines_expr(cursor)} AS quote_business_lines,
                   m.country_code AS legacy_country_code,
                   j.is_enabled,
                   {_quote_selectable_expr(cursor)} AS quote_selectable,
                   {_not_selectable_reason_expr(cursor)} AS not_selectable_reason,
                   {source_geo_expr},
                   {business_region_expr}
            FROM jurisdictions j
            LEFT JOIN country_jurisdiction_map m ON m.jurisdiction_id = j.jurisdiction_id
            LEFT JOIN countries c ON c.code = m.country_code
            WHERE {' AND '.join(where_parts)}
            ORDER BY j.display_order, j.internal_code
            """,
            tuple(params),
        )
        rows = _normalize_text_records(cursor.fetchall())
        for row in rows:
            row["quote_business_lines"] = _loads_json_list(row.get("quote_business_lines"))
            row["business_economic_regions"] = _loads_json_list_or_legacy(row.get("business_economic_regions"))
        return rows


def fetch_jurisdiction_reference_registry(
    keyword: str = "",
    include_hidden: bool = False,
) -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_reference_registry"):
            return _fallback_reference_registry(keyword, include_hidden)
        _seed_reference_registry_if_empty(cursor)
        where_parts = ["r.is_active = 1"]
        params: list[object] = []
        if not include_hidden:
            where_parts.append("r.visibility_scope <> 'reserved_hidden'")
        normalized_keyword = keyword.strip()
        if normalized_keyword:
            where_parts.append(
                """
                (
                  LOWER(r.standard_code) LIKE LOWER(%s)
                  OR LOWER(r.display_code) LIKE LOWER(%s)
                  OR LOWER(r.name_cn) LIKE LOWER(%s)
                  OR LOWER(r.name_en) LIKE LOWER(%s)
                  OR LOWER(CAST(r.aliases_json AS CHAR)) LIKE LOWER(%s)
                )
                """
            )
            like_value = f"%{normalized_keyword}%"
            params.extend([like_value] * 5)
        cursor.execute(
            f"""
            SELECT r.*, j.jurisdiction_id AS matched_jurisdiction_id
            FROM jurisdiction_reference_registry r
            LEFT JOIN jurisdictions j ON j.jurisdiction_id = r.jurisdiction_id
            WHERE {' AND '.join(where_parts)}
            ORDER BY
              CASE r.reference_category
                WHEN 'country' THEN 1
                WHEN 'region' THEN 2
                WHEN 'regional_office' THEN 3
                WHEN 'international_organization' THEN 4
                WHEN 'treaty_route' THEN 5
                ELSE 9
              END,
              r.standard_code
            LIMIT 500
            """,
            tuple(params),
        )
        rows = _normalize_text_records(cursor.fetchall())
        return [_reference_registry_row(row) for row in rows]


def fetch_jurisdiction_reference_registry_item(reference_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_reference_registry"):
            for item in _fallback_reference_registry("", include_hidden=True):
                if item["reference_id"] == reference_id and item["is_active"]:
                    return item
            return None
        _seed_reference_registry_if_empty(cursor)
        cursor.execute(
            """
            SELECT *
            FROM jurisdiction_reference_registry
            WHERE reference_id = %s AND is_active = 1
            LIMIT 1
            """,
            (reference_id,),
        )
        row = _normalize_text_record(cursor.fetchone())
        return _reference_registry_row(row) if row else None


def fetch_jurisdiction_data_sources() -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_data_source_registry"):
            return []
        cursor.execute(
            """
            SELECT *
            FROM jurisdiction_data_source_registry
            ORDER BY is_active DESC, review_status, source_id
            """
        )
        return [_data_source_row(row) for row in _normalize_text_records(cursor.fetchall())]


def upsert_jurisdiction_data_source(values: dict[str, object]) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_data_source_registry"):
            raise RuntimeError("jurisdiction_data_source_registry is not available")
        record = dict(values)
        record["applicable_fields_json"] = json.dumps(record.pop("applicable_fields", []), ensure_ascii=False)
        columns = [
            "source_id",
            "source_name",
            "source_type",
            "source_owner",
            "source_url",
            "source_version",
            "applicable_fields_json",
            "verification_frequency",
            "source_note",
            "source_verified",
            "source_verified_at",
            "source_verified_by",
            "last_reviewed_at",
            "next_review_due_at",
            "review_status",
            "is_active",
        ]
        placeholders = ", ".join(f"%({column})s" for column in columns)
        updates = ", ".join(f"{column} = VALUES({column})" for column in columns if column != "source_id")
        cursor.execute(
            f"""
            INSERT INTO jurisdiction_data_source_registry ({', '.join(columns)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates}
            """,
            {column: record.get(column) for column in columns},
        )
    sources = fetch_jurisdiction_data_sources()
    source_id = str(values["source_id"])
    for source in sources:
        if source["source_id"] == source_id:
            return source
    raise KeyError(source_id)


def update_jurisdiction_data_source(source_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "source_name",
        "source_type",
        "source_owner",
        "source_url",
        "source_version",
        "applicable_fields",
        "verification_frequency",
        "source_note",
        "source_verified",
        "source_verified_at",
        "source_verified_by",
        "last_reviewed_at",
        "next_review_due_at",
        "review_status",
        "is_active",
    }
    updates = {key: value for key, value in values.items() if key in allowed}
    if "applicable_fields" in updates:
        updates["applicable_fields_json"] = json.dumps(updates.pop("applicable_fields"), ensure_ascii=False)
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_data_source_registry"):
            raise RuntimeError("jurisdiction_data_source_registry is not available")
        if updates:
            assignments = ", ".join(f"{key} = %s" for key in updates)
            cursor.execute(
                f"UPDATE jurisdiction_data_source_registry SET {assignments} WHERE source_id = %s",
                tuple(updates.values()) + (source_id,),
            )
            if cursor.rowcount == 0:
                raise KeyError(source_id)
    for source in fetch_jurisdiction_data_sources():
        if source["source_id"] == source_id:
            return source
    raise KeyError(source_id)


def fetch_jurisdiction_region_tags(
    jurisdiction_id: str | None = None,
    tag_code: str | None = None,
) -> list[dict[str, object]]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_region_tag_map"):
            return []
        where_parts = ["1 = 1"]
        params: list[object] = []
        if jurisdiction_id:
            where_parts.append("m.jurisdiction_id = %s")
            params.append(jurisdiction_id)
        if tag_code:
            where_parts.append("m.tag_code = %s")
            params.append(tag_code)
        cursor.execute(
            f"""
            SELECT m.*, j.internal_code AS jurisdiction_code,
                   j.name_cn AS jurisdiction_name_cn, j.name_en AS jurisdiction_name_en
            FROM jurisdiction_region_tag_map m
            JOIN jurisdictions j ON j.jurisdiction_id = m.jurisdiction_id
            WHERE {' AND '.join(where_parts)}
            ORDER BY m.tag_scheme, m.tag_code, j.internal_code
            """,
            tuple(params),
        )
        return [_region_tag_row(row) for row in _normalize_text_records(cursor.fetchall())]


def insert_jurisdiction_region_tag(values: dict[str, object], actor: str = "") -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        if not _table_exists(cursor, "jurisdiction_region_tag_map"):
            raise RuntimeError("jurisdiction_region_tag_map is not available")
        record = {
            "id": f"jrtm-{uuid.uuid4().hex[:16]}",
            **values,
            "created_by": actor,
            "updated_by": actor,
        }
        columns = [
            "id",
            "jurisdiction_id",
            "tag_scheme",
            "tag_code",
            "tag_name_cn",
            "tag_name_en",
            "source_id",
            "source_type",
            "source_name",
            "source_url",
            "source_note",
            "source_verified",
            "source_verified_at",
            "source_verified_by",
            "last_reviewed_at",
            "next_review_due_at",
            "review_status",
            "effective_from",
            "effective_to",
            "is_active",
            "reason_note",
            "created_by",
            "updated_by",
        ]
        placeholders = ", ".join(f"%({column})s" for column in columns)
        updates = ", ".join(f"{column} = VALUES({column})" for column in columns if column not in {"id", "created_by"})
        cursor.execute(
            f"""
            INSERT INTO jurisdiction_region_tag_map ({', '.join(columns)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates}
            """,
            {column: record.get(column) for column in columns},
        )
    tags = fetch_jurisdiction_region_tags(
        jurisdiction_id=str(values.get("jurisdiction_id") or ""),
        tag_code=str(values.get("tag_code") or ""),
    )
    if tags:
        return tags[0]
    raise KeyError(str(values.get("jurisdiction_id") or ""))


def update_country_config(country_code: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "name_cn",
        "name_en",
        "enabled",
        "business_region",
        "region_remark",
    }
    normalized_values = dict(values)
    if "business_region" in normalized_values:
        normalized_values["business_region"] = _business_tags_to_storage(normalized_values["business_region"])
    if any(key in values for key in ("display_code", "name_cn", "name_en")):
        normalized_values["manual_override"] = True
    legacy_values = {key: value for key, value in normalized_values.items() if key in allowed}
    _update_table_record("countries", "code", country_code, legacy_values, allowed)
    with connection_scope() as connection, connection.cursor() as cursor:
        if _jurisdiction_compat_available(cursor):
            _update_country_jurisdiction(cursor, country_code, normalized_values)
            _sync_reference_registry_link(
                cursor,
                str(normalized_values.get("standard_code") or country_code),
                str(normalized_values.get("display_code") or country_code),
            )
    rows = fetch_country_config()["countries"]
    for row in rows:
        if row["code"] == country_code:
            return row
    raise KeyError(country_code)


def insert_country_config(record: dict[str, object]) -> dict[str, object]:
    country_code = str(record["code"]).upper()
    country_type = record.get("country_type") or "单一国家"
    enabled = bool(record.get("enabled", True))
    with connection_scope() as connection, connection.cursor() as cursor:
        values = {
            "code": country_code,
            "name_cn": record["name_cn"],
            "name_en": record["name_en"],
            # Legacy compatibility only. Currency rules belong in the FX/tax module.
            "default_currency": record.get("default_currency") or "USD",
        }
        optional_country_fields = {
            "country_type": country_type,
            "enabled": enabled,
            "display_order": record.get("display_order") or _next_country_display_order(cursor),
            "international_region": record.get("international_region") or "",
            "business_region": _business_tags_to_storage(record.get("business_region") or []),
            "region_remark": record.get("region_remark") or "",
        }
        for field, value in optional_country_fields.items():
            if _column_exists(cursor, "countries", field):
                values[field] = value
        columns = ", ".join(values)
        placeholders = ", ".join(f"%({key})s" for key in values)
        cursor.execute(
            f"INSERT INTO countries ({columns}) VALUES ({placeholders})",
            values,
        )
        if _jurisdiction_compat_available(cursor):
            jurisdiction_values = {
                **record,
                "internal_code": record.get("internal_code") or country_code,
                "display_code": record.get("display_code") or country_code,
                "jurisdiction_type": record.get("jurisdiction_type") or _default_jurisdiction_type(country_code, country_type),
                "is_enabled": record.get("is_enabled") if record.get("is_enabled") is not None else enabled,
            }
            _update_country_jurisdiction(cursor, country_code, jurisdiction_values)
            _sync_reference_registry_link(
                cursor,
                str(jurisdiction_values.get("standard_code") or country_code),
                str(jurisdiction_values.get("display_code") or country_code),
            )

    rows = fetch_country_config()["countries"]
    for row in rows:
        if row["code"] == country_code:
            return row
    raise KeyError(country_code)


def country_reference_exists(standard_code: str, display_code: str) -> bool:
    return inspect_country_reference_status(standard_code, display_code)["status"] != "not_exists"


def inspect_country_reference_status(standard_code: str, display_code: str) -> dict[str, object]:
    codes = sorted({standard_code.upper(), display_code.upper()} - {""})
    if not codes:
        return {"status": "not_exists", "matched_codes": []}
    with connection_scope() as connection, connection.cursor() as cursor:
        placeholders = ", ".join(["%s"] * len(codes))
        where_parts = [f"UPPER(c.code) IN ({placeholders})"]
        params: list[object] = list(codes)
        if _jurisdiction_compat_available(cursor):
            for column in ("internal_code", "display_code", "wipo_st3_code", "standard_code"):
                if _column_exists(cursor, "jurisdictions", column):
                    where_parts.append(f"UPPER(j.{column}) IN ({placeholders})")
                    params.extend(codes)
            country_deleted_expr = (
                "COALESCE(c.is_deleted, 0)"
                if _column_exists(cursor, "countries", "is_deleted")
                else "CASE WHEN c.enabled = 0 THEN 1 ELSE 0 END"
            )
            jurisdiction_deleted_expr = (
                "COALESCE(j.is_deleted, 0)"
                if _column_exists(cursor, "jurisdictions", "is_deleted")
                else "CASE WHEN COALESCE(j.is_enabled, c.enabled) = 0 THEN 1 ELSE 0 END"
            )
            standard_code_expr = (
                "j.standard_code"
                if _column_exists(cursor, "jurisdictions", "standard_code")
                else "j.internal_code"
            )
            cursor.execute(
                f"""
                SELECT c.code AS country_code, c.enabled AS country_enabled,
                       {country_deleted_expr} AS country_deleted,
                       COALESCE(c.jurisdiction_id, m.jurisdiction_id) AS mapped_jurisdiction_id,
                       j.jurisdiction_id, j.internal_code, {standard_code_expr} AS standard_code,
                       j.display_code, j.wipo_st3_code, j.is_enabled AS jurisdiction_enabled,
                       {jurisdiction_deleted_expr} AS jurisdiction_deleted
                FROM countries c
                LEFT JOIN country_jurisdiction_map m ON m.country_code = c.code
                LEFT JOIN jurisdictions j ON j.jurisdiction_id = COALESCE(c.jurisdiction_id, m.jurisdiction_id)
                WHERE {' OR '.join(where_parts)}
                """,
                tuple(params),
            )
            rows = _normalize_text_records(cursor.fetchall())
            orphan_rows = _fetch_matching_orphan_jurisdictions(cursor, codes)
            return _classify_country_reference_status(codes, rows + orphan_rows)

        if _column_exists(cursor, "countries", "display_code"):
            where_parts.append(f"UPPER(c.display_code) IN ({placeholders})")
            params.extend(codes)
        country_deleted_expr = (
            "COALESCE(c.is_deleted, 0)"
            if _column_exists(cursor, "countries", "is_deleted")
            else "CASE WHEN c.enabled = 0 THEN 1 ELSE 0 END"
        )
        cursor.execute(
            f"""
            SELECT c.code AS country_code, c.enabled AS country_enabled,
                   {country_deleted_expr} AS country_deleted,
                   NULL AS mapped_jurisdiction_id, NULL AS jurisdiction_id,
                   NULL AS internal_code, c.code AS standard_code,
                   c.code AS display_code, NULL AS wipo_st3_code,
                   c.enabled AS jurisdiction_enabled, {country_deleted_expr} AS jurisdiction_deleted
            FROM countries c
            WHERE {' OR '.join(where_parts)}
            """,
            tuple(params),
        )
        return _classify_country_reference_status(codes, _normalize_text_records(cursor.fetchall()))


def restore_country_config_from_reference(
    record: dict[str, object],
    existence: dict[str, object] | None = None,
) -> dict[str, object]:
    country_code = str(
        (existence or {}).get("country_code")
        or record.get("code")
        or record.get("standard_code")
        or record.get("display_code")
    ).upper()
    if not country_code:
        raise KeyError("COUNTRY_CODE_REQUIRED")

    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM countries WHERE code = %s LIMIT 1", (country_code,))
        country = _normalize_text_record(cursor.fetchone())
        if country is None:
            insert_values = {
                "code": country_code,
                "name_cn": record["name_cn"],
                "name_en": record["name_en"],
                # Legacy compatibility only. Currency rules belong in the FX/tax module.
                "default_currency": record.get("default_currency") or "USD",
            }
            optional_country_fields = {
                "country_type": record.get("country_type") or "单一国家",
                "enabled": True,
                "display_order": record.get("display_order") or _next_country_display_order(cursor),
                "international_region": record.get("international_region") or "",
                "business_region": _business_tags_to_storage(record.get("business_region") or []),
                "region_remark": record.get("region_remark") or "",
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
                "delete_reason": None,
            }
            for field, value in optional_country_fields.items():
                if _column_exists(cursor, "countries", field):
                    insert_values[field] = value
            columns = ", ".join(insert_values)
            placeholders = ", ".join(f"%({key})s" for key in insert_values)
            cursor.execute(
                f"INSERT INTO countries ({columns}) VALUES ({placeholders})",
                insert_values,
            )
        else:
            updates = {
                "name_cn": record["name_cn"],
                "name_en": record["name_en"],
                # Legacy compatibility only. Currency rules belong in the FX/tax module.
                "default_currency": record.get("default_currency") or country.get("default_currency") or "USD",
                "country_type": record.get("country_type") or country.get("country_type") or "单一国家",
                "enabled": True,
                "international_region": record.get("international_region") or country.get("international_region") or "",
                "business_region": _business_tags_to_storage(record.get("business_region") or []),
                "region_remark": record.get("region_remark") or "",
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
                "delete_reason": None,
            }
            updates = {key: value for key, value in updates.items() if _column_exists(cursor, "countries", key)}
            assignments = ", ".join(f"{key} = %s" for key in updates)
            cursor.execute(
                f"UPDATE countries SET {assignments} WHERE code = %s",
                tuple(updates.values()) + (country_code,),
            )

        if _jurisdiction_compat_available(cursor):
            jurisdiction_values = {
                **record,
                "internal_code": record.get("internal_code") or country_code,
                "display_code": record.get("display_code") or country_code,
                "jurisdiction_type": record.get("jurisdiction_type") or _default_jurisdiction_type(country_code, record.get("country_type")),
                "is_enabled": True,
            }
            _update_country_jurisdiction(cursor, country_code, jurisdiction_values)
            jurisdiction_id = _country_jurisdiction_id(cursor, country_code)
            if jurisdiction_id:
                restore_updates: dict[str, object] = {"is_enabled": True}
                for field, value in {
                    "is_deleted": False,
                    "deleted_at": None,
                    "deleted_by": None,
                    "delete_reason": None,
                }.items():
                    if _column_exists(cursor, "jurisdictions", field):
                        restore_updates[field] = value
                assignments = ", ".join(f"{key} = %s" for key in restore_updates)
                cursor.execute(
                    f"UPDATE jurisdictions SET {assignments} WHERE jurisdiction_id = %s",
                    tuple(restore_updates.values()) + (jurisdiction_id,),
                )
            _sync_reference_registry_link(
                cursor,
                str(jurisdiction_values.get("standard_code") or country_code),
                str(jurisdiction_values.get("display_code") or country_code),
            )

    rows = fetch_country_config(include_deleted=True)["countries"]
    for row in rows:
        if row["code"] == country_code:
            return row
    raise KeyError(country_code)


def soft_delete_country_config(
    country_code: str,
    deleted_by: str,
    delete_reason: str = "",
) -> dict[str, object]:
    country_code = country_code.upper()
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM countries WHERE code = %s LIMIT 1", (country_code,))
        country = _normalize_text_record(cursor.fetchone())
        if country is None:
            raise KeyError(country_code)
        jurisdiction_id = _country_jurisdiction_id(cursor, country_code)
        references = _country_business_reference_counts(cursor, country_code, jurisdiction_id)
        if references:
            raise ValueError(_format_country_reference_block_message(references))

        now = datetime.now()
        country_updates: dict[str, object] = {"enabled": False}
        if _column_exists(cursor, "countries", "is_deleted"):
            country_updates.update(
                {
                    "is_deleted": True,
                    "deleted_at": now,
                    "deleted_by": deleted_by,
                    "delete_reason": delete_reason,
                }
            )
        assignments = ", ".join(f"{key} = %s" for key in country_updates)
        cursor.execute(
            f"UPDATE countries SET {assignments} WHERE code = %s",
            tuple(country_updates.values()) + (country_code,),
        )
        if jurisdiction_id and _table_exists(cursor, "jurisdictions"):
            jurisdiction_updates: dict[str, object] = {"is_enabled": False}
            if _column_exists(cursor, "jurisdictions", "is_deleted"):
                jurisdiction_updates.update(
                    {
                        "is_deleted": True,
                        "deleted_at": now,
                        "deleted_by": deleted_by,
                        "delete_reason": delete_reason,
                    }
                )
            assignments = ", ".join(f"{key} = %s" for key in jurisdiction_updates)
            cursor.execute(
                f"UPDATE jurisdictions SET {assignments} WHERE jurisdiction_id = %s",
                tuple(jurisdiction_updates.values()) + (jurisdiction_id,),
            )
    return {"code": country_code, "deleted": True}


def update_country_path_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "route_detail",
        "affects_official_fee",
        "affects_local_service_fee",
        "affects_inhouse_service_fee",
        "affects_questions",
        "affects_documents",
        "affects_deadlines",
        "affects_translation",
        "affects_display",
        "enabled",
        "effective_date",
        "remark",
    }
    _update_table_record("country_path_rules", "id", rule_id, values, allowed)
    return _find_config_record("path_rules", rule_id)


def insert_country_path_rule(record: dict[str, object]) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO country_path_rules (
              id, country_code, application_type, filing_route, route_detail,
              affects_official_fee, affects_local_service_fee, affects_inhouse_service_fee,
              affects_questions, affects_documents, affects_deadlines, affects_translation,
              affects_display, enabled, effective_date, remark
            )
            VALUES (
              %(id)s, %(country_code)s, %(application_type)s, %(filing_route)s,
              %(route_detail)s, %(affects_official_fee)s, %(affects_local_service_fee)s,
              %(affects_inhouse_service_fee)s, %(affects_questions)s, %(affects_documents)s,
              %(affects_deadlines)s, %(affects_translation)s, %(affects_display)s,
              %(enabled)s, %(effective_date)s, %(remark)s
            )
            """,
            record,
        )
    return _find_config_record("path_rules", str(record["id"]))


def delete_country_path_rule(rule_id: str) -> None:
    _delete_table_record("country_path_rules", "id", rule_id)


def update_entity_type_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    normalized = dict(values)
    if "entity_types" in normalized:
        normalized["entity_types_json"] = json.dumps(normalized.pop("entity_types"), ensure_ascii=False)
    allowed = {
        "enabled",
        "entity_types_json",
        "affects_official_fee",
        "affects_questions",
        "requires_customer_confirmation",
        "requires_supporting_documents",
        "remark",
    }
    _update_table_record("entity_type_rules", "id", rule_id, normalized, allowed)
    return _find_config_record("entity_type_rules", rule_id)


def insert_entity_type_rule(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    normalized["entity_types_json"] = json.dumps(
        normalized.pop("entity_types", []),
        ensure_ascii=False,
    )
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO entity_type_rules (
              id, country_code, application_type, filing_route, enabled,
              entity_types_json, affects_official_fee, affects_questions,
              requires_customer_confirmation, requires_supporting_documents, remark
            )
            VALUES (
              %(id)s, %(country_code)s, %(application_type)s, %(filing_route)s,
              %(enabled)s, %(entity_types_json)s, %(affects_official_fee)s,
              %(affects_questions)s, %(requires_customer_confirmation)s,
              %(requires_supporting_documents)s, %(remark)s
            )
            """,
            normalized,
        )
    return _find_config_record("entity_type_rules", str(record["id"]))


def delete_entity_type_rule(rule_id: str) -> None:
    _delete_table_record("entity_type_rules", "id", rule_id)


def update_language_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    normalized = dict(values)
    if "accepted_languages" in normalized:
        normalized["accepted_languages_json"] = json.dumps(
            normalized.pop("accepted_languages"),
            ensure_ascii=False,
        )
    allowed = {
        "accepted_languages_json",
        "source_language",
        "target_language",
        "intermediate_language",
        "needs_second_translation",
        "recommended_scheme_id",
        "default_translation_fee",
        "allow_scheme_switch",
        "enabled",
        "remark",
    }
    _update_table_record("language_rules", "id", rule_id, normalized, allowed)
    return _find_config_record("language_rules", rule_id)


def insert_language_rule(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    normalized["accepted_languages_json"] = json.dumps(
        normalized.pop("accepted_languages", []),
        ensure_ascii=False,
    )
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO language_rules (
              id, country_code, application_type, accepted_languages_json,
              source_language, target_language, intermediate_language,
              needs_second_translation, recommended_scheme_id, default_translation_fee,
              allow_scheme_switch, enabled, remark
            )
            VALUES (
              %(id)s, %(country_code)s, %(application_type)s, %(accepted_languages_json)s,
              %(source_language)s, %(target_language)s, %(intermediate_language)s,
              %(needs_second_translation)s, %(recommended_scheme_id)s,
              %(default_translation_fee)s, %(allow_scheme_switch)s, %(enabled)s, %(remark)s
            )
            """,
            normalized,
        )
    return _find_config_record("language_rules", str(record["id"]))


def delete_language_rule(rule_id: str) -> None:
    _delete_table_record("language_rules", "id", rule_id)


def update_fx_tax_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    normalized = dict(values)
    if "local_service_currency_options" in normalized:
        normalized["local_service_currency_options_json"] = json.dumps(
            normalized.pop("local_service_currency_options"),
            ensure_ascii=False,
        )
    allowed = {
        "official_currency",
        "official_quote_currency",
        "local_service_currency",
        "local_service_currency_options_json",
        "quote_currency",
        "fx_rate",
        "tax_rate",
        "tax_included",
        "lock_on_formal_quote",
        "version",
        "enabled",
        "remark",
    }
    _update_table_record("fx_tax_rules", "id", rule_id, normalized, allowed)
    return _find_config_record("fx_tax_rules", rule_id)


def insert_fx_tax_rule(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    normalized["local_service_currency_options_json"] = json.dumps(
        normalized.pop("local_service_currency_options", []),
        ensure_ascii=False,
    )
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO fx_tax_rules (
              id, country_code, official_currency, official_quote_currency,
              local_service_currency, local_service_currency_options_json, quote_currency,
              fx_rate, tax_rate, tax_included, lock_on_formal_quote, version, enabled, remark
            )
            VALUES (
              %(id)s, %(country_code)s, %(official_currency)s, %(official_quote_currency)s,
              %(local_service_currency)s, %(local_service_currency_options_json)s,
              %(quote_currency)s, %(fx_rate)s, %(tax_rate)s, %(tax_included)s,
              %(lock_on_formal_quote)s, %(version)s, %(enabled)s, %(remark)s
            )
            """,
            normalized,
        )
    return _find_config_record("fx_tax_rules", str(record["id"]))


def delete_fx_tax_rule(rule_id: str) -> None:
    _delete_table_record("fx_tax_rules", "id", rule_id)


def update_special_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "enabled",
        "triggers_extra_fee",
        "triggers_risk_warning",
        "requires_customer_confirmation",
        "risk_summary",
        "linked_rule_code",
        "remark",
    }
    _update_table_record("special_rules", "id", rule_id, values, allowed)
    return _find_config_record("special_rules", rule_id)


def insert_special_rule(record: dict[str, object]) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO special_rules (
              id, country_code, application_type, filing_route, rule_type, enabled,
              triggers_extra_fee, triggers_risk_warning, requires_customer_confirmation,
              risk_summary, linked_rule_code, remark
            )
            VALUES (
              %(id)s, %(country_code)s, %(application_type)s, %(filing_route)s,
              %(rule_type)s, %(enabled)s, %(triggers_extra_fee)s,
              %(triggers_risk_warning)s, %(requires_customer_confirmation)s,
              %(risk_summary)s, %(linked_rule_code)s, %(remark)s
            )
            """,
            record,
        )
    return _find_config_record("special_rules", str(record["id"]))


def delete_special_rule(rule_id: str) -> None:
    _delete_table_record("special_rules", "id", rule_id)


def fetch_fee_rules(include_inactive: bool = False) -> list[dict[str, object]]:
    active_filter = "" if include_inactive else "WHERE fr.is_active = 1"
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT fr.id, fr.version_id, fr.country_code, fr.application_type, fr.filing_route,
                   fr.pct_route_detail, fr.entity_type, fr.stage, fr.item_group_key, fr.item_name,
                   fr.fee_type, fr.fee_category, fr.amount, fr.currency, fr.quote_currency,
                   fr.is_multi_currency, fr.tax_included, fr.is_default, fr.is_active,
                   fr.cost_nature, fr.trigger_condition,
                   COALESCE(frv.version_name, fr.version_id, '') AS price_version,
                   fr.remark
            FROM fee_rules
            fr
            LEFT JOIN fee_rule_versions frv ON frv.id = fr.version_id
            {active_filter}
            ORDER BY fr.country_code, fr.application_type, fr.filing_route, fr.sort_order, fr.id
            """
        )
        return _normalize_text_records(cursor.fetchall())


def fetch_fee_rule(rule_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT fr.id, fr.version_id, fr.country_code, fr.application_type, fr.filing_route,
                   fr.pct_route_detail, fr.entity_type, fr.stage, fr.item_group_key, fr.item_name,
                   fr.fee_type, fr.fee_category, fr.amount, fr.currency, fr.quote_currency,
                   fr.is_multi_currency, fr.tax_included, fr.is_default, fr.is_active,
                   fr.cost_nature, fr.trigger_condition,
                   COALESCE(frv.version_name, fr.version_id, '') AS price_version,
                   fr.remark
            FROM fee_rules fr
            LEFT JOIN fee_rule_versions frv ON frv.id = fr.version_id
            WHERE fr.id = %s
            LIMIT 1
            """,
            (rule_id,),
        )
        return _normalize_text_record(cursor.fetchone())


def insert_fee_rule(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    with connection_scope() as connection, connection.cursor() as cursor:
        if not normalized.get("version_id"):
            cursor.execute(
                """
                SELECT id
                FROM fee_rule_versions
                WHERE is_current = 1
                ORDER BY effective_date DESC, id
                LIMIT 1
                """
            )
            version = cursor.fetchone()
            normalized["version_id"] = version["id"] if version else None
        cursor.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_sort_order
            FROM fee_rules
            WHERE country_code = %(country_code)s
              AND application_type = %(application_type)s
              AND filing_route = %(filing_route)s
            """,
            normalized,
        )
        normalized["sort_order"] = cursor.fetchone()["next_sort_order"]
        cursor.execute(
            """
            INSERT INTO fee_rules (
              id, version_id, country_code, application_type, filing_route,
              pct_route_detail, entity_type, stage, item_group_key, item_name,
              fee_type, fee_category, amount, currency, quote_currency,
              is_multi_currency, tax_included, is_default, is_active,
              cost_nature, trigger_condition, remark, sort_order
            )
            VALUES (
              %(id)s, %(version_id)s, %(country_code)s, %(application_type)s,
              %(filing_route)s, %(pct_route_detail)s, %(entity_type)s, %(stage)s,
              %(item_group_key)s, %(item_name)s, %(fee_type)s, %(fee_category)s,
              %(amount)s, %(currency)s, %(quote_currency)s, %(is_multi_currency)s,
              %(tax_included)s, %(is_default)s, %(is_active)s, %(cost_nature)s,
              %(trigger_condition)s, %(remark)s, %(sort_order)s
            )
            """,
            normalized,
        )
    rule = fetch_fee_rule(str(record["id"]))
    if rule is None:
        raise KeyError(str(record["id"]))
    return rule


def delete_fee_rule(rule_id: str) -> None:
    _delete_table_record("fee_rules", "id", rule_id)


def update_fee_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "amount",
        "currency",
        "quote_currency",
        "item_group_key",
        "fee_type",
        "fee_category",
        "trigger_condition",
        "tax_included",
        "is_default",
        "is_active",
        "remark",
    }
    updates = {key: value for key, value in values.items() if key in allowed}
    if updates:
        assignments = ", ".join(f"{key} = %s" for key in updates)
        params = tuple(updates.values()) + (rule_id,)
        with connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(f"UPDATE fee_rules SET {assignments} WHERE id = %s", params)
            if cursor.rowcount == 0:
                raise KeyError(rule_id)
    rule = fetch_fee_rule(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    return rule


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
        return _normalize_text_records(cursor.fetchall())


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
        return _normalize_text_record(cursor.fetchone())


def update_translation_rule(rule_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {"item_name", "unit", "unit_price", "currency", "min_fee", "enabled", "is_default"}
    updates = {key: value for key, value in values.items() if key in allowed}
    if updates:
        assignments = ", ".join(f"{key} = %s" for key in updates)
        params = tuple(updates.values()) + (rule_id,)
        with connection_scope() as connection, connection.cursor() as cursor:
            cursor.execute(f"UPDATE translation_rules SET {assignments} WHERE id = %s", params)
            if cursor.rowcount == 0:
                raise KeyError(rule_id)
    rule = fetch_translation_rule(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    return rule


def insert_quotation_draft(
    record: dict[str, object],
    items: list[dict[str, object]],
) -> None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO quotation_drafts (
              id, draft_no, consultant_id, consultant_email, consultant_name,
              client_name, client_contact, has_case, case_title, applicant_count,
              priority_count, claim_count, description_pages, drawing_pages,
              needs_translation, translation_quantity_one, translation_quantity_two,
              status, remark, created_at, updated_at
            )
            VALUES (
              %(id)s, %(draft_no)s, %(consultant_id)s, %(consultant_email)s, %(consultant_name)s,
              %(client_name)s, %(client_contact)s, %(has_case)s, %(case_title)s, %(applicant_count)s,
              %(priority_count)s, %(claim_count)s, %(description_pages)s, %(drawing_pages)s,
              %(needs_translation)s, %(translation_quantity_one)s, %(translation_quantity_two)s,
              %(status)s, %(remark)s, %(created_at)s, %(updated_at)s
            )
            """,
            record,
        )
        for item in items:
            cursor.execute(
                """
                INSERT INTO quotation_draft_items (
                  id, draft_id, country_code, application_type, filing_route,
                  pct_route_detail, entity_type, case_title, quote_currency,
                  current_stage_total, future_stage_total, total_amount,
                  status, sort_order, created_at, updated_at
                )
                VALUES (
                  %(id)s, %(draft_id)s, %(country_code)s, %(application_type)s, %(filing_route)s,
                  %(pct_route_detail)s, %(entity_type)s, %(case_title)s, %(quote_currency)s,
                  %(current_stage_total)s, %(future_stage_total)s, %(total_amount)s,
                  %(status)s, %(sort_order)s, %(created_at)s, %(updated_at)s
                )
                """,
                item,
            )


def fetch_quotation_draft(draft_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM quotation_drafts WHERE id = %s LIMIT 1", (draft_id,))
        draft = cursor.fetchone()
        if not draft:
            return None
        draft["items"] = _fetch_draft_items(cursor, draft_id)
        return draft


def fetch_quotation_drafts(user_email: str | None) -> list[dict[str, object]]:
    params: tuple[object, ...] = ()
    where = ""
    if user_email:
        where = "WHERE consultant_email = %s"
        params = (user_email,)

    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM quotation_drafts
            {where}
            ORDER BY created_at DESC
            LIMIT 200
            """,
            params,
        )
        drafts = list(cursor.fetchall())
        for draft in drafts:
            draft["items"] = _fetch_draft_items(cursor, str(draft["id"]))
        return drafts


def update_quotation_draft(draft_id: str, values: dict[str, object]) -> dict[str, object]:
    allowed = {
        "client_name",
        "client_contact",
        "has_case",
        "case_title",
        "applicant_count",
        "priority_count",
        "claim_count",
        "description_pages",
        "drawing_pages",
        "needs_translation",
        "translation_quantity_one",
        "translation_quantity_two",
        "remark",
    }
    updates = {key: value for key, value in values.items() if key in allowed}
    with connection_scope() as connection, connection.cursor() as cursor:
        if updates:
            updates["updated_at"] = datetime.now()
            assignments = ", ".join(f"{key} = %s" for key in updates)
            params = tuple(updates.values()) + (draft_id,)
            cursor.execute(
                f"UPDATE quotation_drafts SET {assignments} WHERE id = %s",
                params,
            )
            if cursor.rowcount == 0:
                raise KeyError(draft_id)
            if "case_title" in updates:
                cursor.execute(
                    """
                    UPDATE quotation_draft_items
                    SET case_title = %s, updated_at = %s
                    WHERE draft_id = %s AND status <> '已删除'
                    """,
                    (updates["case_title"], datetime.now(), draft_id),
                )
        else:
            cursor.execute("SELECT id FROM quotation_drafts WHERE id = %s LIMIT 1", (draft_id,))
            if cursor.fetchone() is None:
                raise KeyError(draft_id)
    draft = fetch_quotation_draft(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    return draft


def delete_quotation_draft_item(draft_id: str, item_id: str) -> dict[str, object]:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE quotation_draft_items
            SET status = '已删除', updated_at = %s
            WHERE id = %s AND draft_id = %s AND status <> '已删除'
            """,
            (datetime.now(), item_id, draft_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(item_id)
    draft = fetch_quotation_draft(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    return draft


def fetch_draft_items_for_formal_quote(item_ids: list[str]) -> list[dict[str, object]]:
    if not item_ids:
        return []
    placeholders = ", ".join(["%s"] * len(item_ids))
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              i.id, i.draft_id, i.country_code, i.application_type, i.filing_route,
              i.pct_route_detail, i.entity_type, i.case_title, i.quote_currency,
              i.current_stage_total, i.future_stage_total, i.total_amount,
              i.status, i.sort_order,
              d.draft_no, d.consultant_id, d.consultant_email, d.consultant_name,
              d.client_name, d.client_contact, d.has_case, d.applicant_count,
              d.priority_count, d.claim_count, d.description_pages, d.drawing_pages,
              d.needs_translation, d.translation_quantity_one, d.translation_quantity_two,
              d.remark AS draft_remark
            FROM quotation_draft_items i
            JOIN quotation_drafts d ON d.id = i.draft_id
            WHERE i.id IN ({placeholders})
              AND i.status NOT IN ('已删除', '已合并正式报价')
            ORDER BY d.created_at, i.sort_order, i.id
            """,
            tuple(item_ids),
        )
        return list(cursor.fetchall())


def insert_quotation_from_drafts(
    record: dict[str, object],
    items: list[dict[str, object]],
    draft_ids: list[str],
    draft_item_ids: list[str],
) -> None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO quotations (
              id, quotation_no, source_draft_ids_json, consultant_id, consultant_email,
              consultant_name, client_name, client_contact, country_code, country_codes_json,
              application_type, filing_route, currency, has_case, case_title,
              applicant_count, priority_count, claim_count, description_pages, drawing_pages,
              needs_translation, translation_quantity_one, translation_quantity_two,
              current_stage_total, future_stage_total, total_amount, status,
              is_sent, is_confirmed, is_opened, opened_reference, remark,
              created_at, updated_at
            )
            VALUES (
              %(id)s, %(quotation_no)s, %(source_draft_ids_json)s, %(consultant_id)s,
              %(consultant_email)s, %(consultant_name)s, %(client_name)s, %(client_contact)s,
              %(country_code)s, %(country_codes_json)s, %(application_type)s, %(filing_route)s,
              %(currency)s, %(has_case)s, %(case_title)s, %(applicant_count)s,
              %(priority_count)s, %(claim_count)s, %(description_pages)s, %(drawing_pages)s,
              %(needs_translation)s, %(translation_quantity_one)s, %(translation_quantity_two)s,
              %(current_stage_total)s, %(future_stage_total)s, %(total_amount)s, %(status)s,
              %(is_sent)s, %(is_confirmed)s, %(is_opened)s, %(opened_reference)s, %(remark)s,
              %(created_at)s, %(updated_at)s
            )
            """,
            record,
        )
        for item in items:
            cursor.execute(
                """
                INSERT INTO quotation_items (
                  id, quotation_id, draft_item_id, country_code, application_type, filing_route,
                  pct_route_detail, entity_type, case_title, stage, item_group_key,
                  item_name, fee_type, fee_category, amount, currency, quote_currency,
                  tax_included, cost_nature, opening_status, not_opened_reason,
                  remark, sort_order
                )
                VALUES (
                  %(id)s, %(quotation_id)s, %(draft_item_id)s, %(country_code)s,
                  %(application_type)s, %(filing_route)s, %(pct_route_detail)s,
                  %(entity_type)s, %(case_title)s, %(stage)s, %(item_group_key)s,
                  %(item_name)s, %(fee_type)s, %(fee_category)s, %(amount)s,
                  %(currency)s, %(quote_currency)s, %(tax_included)s, %(cost_nature)s,
                  %(opening_status)s, %(not_opened_reason)s, %(remark)s, %(sort_order)s
                )
                """,
                item,
            )
        if draft_item_ids:
            placeholders = ", ".join(["%s"] * len(draft_item_ids))
            cursor.execute(
                f"""
                UPDATE quotation_draft_items
                SET status = '已合并正式报价', updated_at = %s
                WHERE id IN ({placeholders})
                """,
                (datetime.now(), *draft_item_ids),
            )
        if draft_ids:
            placeholders = ", ".join(["%s"] * len(draft_ids))
            cursor.execute(
                f"""
                UPDATE quotation_drafts
                SET status = '已合并正式报价', updated_at = %s
                WHERE id IN ({placeholders})
                  AND NOT EXISTS (
                    SELECT 1
                    FROM quotation_draft_items i
                    WHERE i.draft_id = quotation_drafts.id
                      AND i.status NOT IN ('已删除', '已合并正式报价')
                  )
                """,
                (datetime.now(), *draft_ids),
            )


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
    refresh_quotation_followup_statuses()
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT * FROM quotations WHERE id = %s LIMIT 1", (quotation_id,))
        quotation = cursor.fetchone()
        if not quotation:
            return None
        quotation["items"] = _fetch_items(cursor, quotation_id)
        return quotation


def fetch_quotations(user_email: str | None) -> list[dict[str, object]]:
    refresh_quotation_followup_statuses()
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
    is_sent = status in {
        "已发送客户",
        "待跟进",
        "跟进中",
        "跟进逾期",
        "需价格调整",
        "已确认",
        "部分开卷",
        "已开卷",
        "框架协议",
    }
    is_confirmed = status in {"已确认", "部分开卷", "已开卷", "框架协议"}
    is_opened = status in {"部分开卷", "已开卷"}
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


def refresh_quotation_followup_statuses() -> None:
    active_statuses = ("已发送客户", "待跟进", "跟进中", "跟进逾期", "需价格调整")
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE quotations
            SET status = CASE
                    WHEN next_followup_date < CURDATE() THEN '跟进逾期'
                    WHEN next_followup_date = CURDATE() THEN '待跟进'
                    ELSE status
                END,
                is_sent = 1,
                updated_at = %s
            WHERE next_followup_date IS NOT NULL
              AND status IN %s
              AND next_followup_date <= CURDATE()
            """,
            (datetime.now(), active_statuses),
        )


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
              id, quotation_id, user_id, consultant_email, method, content, next_followup_date
            )
            VALUES (
              %(id)s, %(quotation_id)s, %(user_id)s, %(consultant_email)s, %(method)s,
              %(content)s, %(next_followup_date)s
            )
            """,
            record,
        )
        cursor.execute(
            """
            UPDATE quotations
            SET last_followup_at = %s,
                next_followup_date = %s,
                status = CASE
                    WHEN status IN ('已发送客户', '待跟进', '跟进逾期', '需价格调整') THEN '跟进中'
                    ELSE status
                END,
                is_sent = CASE
                    WHEN status IN ('已发送客户', '待跟进', '跟进中', '跟进逾期', '需价格调整') THEN 1
                    ELSE is_sent
                END,
                updated_at = %s
            WHERE id = %s
            """,
            (datetime.now(), values.get("next_followup_date"), datetime.now(), values["quotation_id"]),
        )
    followups = fetch_followups(str(values["quotation_id"]))
    for followup in followups:
        if followup["id"] == followup_id:
            return followup
    raise KeyError(followup_id)


def count_overdue_followup_quotations(consultant_email: str, overdue_days: int) -> int:
    cutoff = datetime.now().date() - timedelta(days=overdue_days)
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM quotations
            WHERE consultant_email = %s
              AND status = '跟进逾期'
              AND next_followup_date IS NOT NULL
              AND next_followup_date <= %s
            """,
            (consultant_email, cutoff),
        )
        row = cursor.fetchone() or {}
        return int(row.get("count") or 0)


def count_open_unconverted_quotations(consultant_email: str) -> int:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM quotations
            WHERE consultant_email = %s
              AND is_opened = 0
              AND status NOT IN ('未成交', '已作废')
            """,
            (consultant_email,),
        )
        row = cursor.fetchone() or {}
        return int(row.get("count") or 0)


def has_valid_quote_unlock(consultant_email: str) -> bool:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM quotation_approval_requests
            WHERE consultant_email = %s
              AND request_type = '超过10条未转化继续报价'
              AND status = '已通过'
              AND (valid_until IS NULL OR valid_until > %s)
            ORDER BY reviewed_at DESC, created_at DESC
            LIMIT 1
            """,
            (consultant_email, datetime.now()),
        )
        return cursor.fetchone() is not None


def insert_approval_request(values: dict[str, object]) -> dict[str, object]:
    request_id = str(uuid.uuid4())
    record = {"id": request_id, **values}
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO quotation_approval_requests (
              id, consultant_id, consultant_email, request_type, open_unconverted_count,
              status, reason
            )
            VALUES (
              %(id)s, %(consultant_id)s, %(consultant_email)s, %(request_type)s,
              %(open_unconverted_count)s, '待审批', %(reason)s
            )
            """,
            record,
        )
    request = fetch_approval_request(request_id)
    if request is None:
        raise KeyError(request_id)
    return request


def fetch_approval_request(request_id: str) -> dict[str, object] | None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM quotation_approval_requests WHERE id = %s LIMIT 1",
            (request_id,),
        )
        return cursor.fetchone()


def fetch_approval_requests(consultant_email: str | None = None) -> list[dict[str, object]]:
    where = ""
    params: tuple[object, ...] = ()
    if consultant_email:
        where = "WHERE consultant_email = %s"
        params = (consultant_email,)
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM quotation_approval_requests
            {where}
            ORDER BY created_at DESC
            LIMIT 100
            """,
            params,
        )
        return list(cursor.fetchall())


def review_approval_request(
    request_id: str,
    reviewer_id: str,
    status: str,
    reviewer_comment: str,
    valid_days: int,
) -> dict[str, object]:
    valid_until = datetime.now() + timedelta(days=valid_days) if status == "已通过" else None
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE quotation_approval_requests
            SET status = %s,
                reviewer_id = %s,
                reviewer_comment = %s,
                reviewed_at = %s,
                valid_until = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (status, reviewer_id, reviewer_comment, datetime.now(), valid_until, datetime.now(), request_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(request_id)
    request = fetch_approval_request(request_id)
    if request is None:
        raise KeyError(request_id)
    return request


def fetch_statistics(user_email: str | None = None) -> dict[str, object]:
    refresh_quotation_followup_statuses()
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
            """,
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


def _fetch_draft_items(cursor: DictCursor, draft_id: str) -> list[dict[str, object]]:
    cursor.execute(
        """
        SELECT id, draft_id, country_code, application_type, filing_route,
               pct_route_detail, entity_type, case_title, quote_currency,
               current_stage_total, future_stage_total, total_amount,
               status, sort_order, created_at, updated_at
        FROM quotation_draft_items
        WHERE draft_id = %s AND status <> '已删除'
        ORDER BY sort_order, id
        """,
        (draft_id,),
    )
    return list(cursor.fetchall())


def _fetch_customer_contacts(cursor: DictCursor, customer_id: str) -> list[dict[str, object]]:
    cursor.execute(
        """
        SELECT *
        FROM customer_contacts
        WHERE customer_id = %s
        ORDER BY is_primary DESC, created_at, id
        """,
        (customer_id,),
    )
    return _normalize_text_records(cursor.fetchall())


def _normalize_customer(customer: dict[str, object]) -> None:
    customer["customer_type"] = _normalize_customer_choice(
        customer.get("customer_type"),
        {"企业", "个人", "律所", "代理机构", "其他"},
        "企业",
    )
    customer["customer_level"] = _normalize_customer_choice(
        customer.get("customer_level"),
        {"普通", "重点", "战略", "暂停"},
        "普通",
    )
    customer["default_quote_terms"] = customer.get("default_quote_terms") or ""
    customer["remark"] = customer.get("remark") or ""
    customer["department"] = customer.get("department") or ""
    customer["consultant_email"] = customer.get("consultant_email") or ""
    customer["consultant_name"] = customer.get("consultant_name") or ""


def _normalize_customer_choice(
    value: object,
    allowed_values: set[str],
    default: str,
) -> str:
    if value is None:
        return default
    text = str(value)
    if text in allowed_values:
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return default
    return repaired if repaired in allowed_values else default


def _normalize_text_records(records: object) -> list[dict[str, object]]:
    return [_normalize_text_record(record) for record in records]


def _normalize_text_record(record: dict[str, object] | None) -> dict[str, object] | None:
    if record is None:
        return None
    for key, value in list(record.items()):
        if isinstance(value, str):
            record[key] = _repair_mojibake_text(value)
    return record


def _repair_mojibake_text(value: str) -> str:
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value
    return repaired if _looks_like_chinese_mojibake(value, repaired) else value


def _looks_like_chinese_mojibake(original: str, repaired: str) -> bool:
    if original == repaired:
        return False
    original_has_cjk = any("\u4e00" <= char <= "\u9fff" for char in original)
    repaired_has_cjk = any("\u4e00" <= char <= "\u9fff" for char in repaired)
    mojibake_markers = ("å", "æ", "ç", "è", "é", "ã", "\x80", "\x81", "\x82", "\x83", "\x84")
    return repaired_has_cjk and (not original_has_cjk or any(marker in original for marker in mojibake_markers))


def _loads_json_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [_repair_mojibake_text(str(item)) for item in value]
    try:
        loaded = json.loads(_repair_mojibake_text(str(value)))
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [_repair_mojibake_text(str(item)) for item in loaded]


def _loads_json_list_or_legacy(value: object) -> list[str]:
    if value in (None, ""):
        return ["OTHER"]
    if isinstance(value, list):
        return [_repair_mojibake_text(str(item)) for item in value if str(item).strip()] or ["OTHER"]
    text = _repair_mojibake_text(str(value)).strip()
    if not text:
        return ["OTHER"]
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        aliases = {
            "Europe": "EUROPE",
            "North America": "NORTH_AMERICA",
            "Latin America": "LATIN_AMERICA",
            "South America": "SOUTH_AMERICA",
            "Southeast Asia": "SOUTHEAST_ASIA",
            "Middle East": "MIDDLE_EAST",
            "Africa": "AFRICA",
            "Japan and Korea": "NORTHEAST_ASIA_JP_KR",
            "Hong Kong Macao Taiwan": "GREATER_CHINA",
            "Other": "OTHER",
        }
        items = [aliases.get(item.strip(), item.strip()) for item in text.replace("，", ",").split(",")]
        return [item for item in items if item] or ["OTHER"]
    if not isinstance(loaded, list):
        return ["OTHER"]
    return [_repair_mojibake_text(str(item)) for item in loaded if str(item).strip()] or ["OTHER"]


def _business_tags_to_storage(value: object) -> str:
    return json.dumps(_loads_json_list_or_legacy(value), ensure_ascii=False)


def _next_country_display_order(cursor: DictCursor) -> int:
    if not _column_exists(cursor, "countries", "display_order"):
        return 0
    cursor.execute("SELECT COALESCE(MAX(display_order), 0) + 10 AS next_display_order FROM countries")
    row = cursor.fetchone() or {}
    return int(row.get("next_display_order") or 10)


def _jurisdiction_compat_available(cursor: DictCursor) -> bool:
    return (
        _table_exists(cursor, "jurisdictions")
        and _table_exists(cursor, "country_jurisdiction_map")
        and _column_exists(cursor, "countries", "jurisdiction_id")
    )


def _table_exists(cursor: DictCursor, table_name: str) -> bool:
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


def _column_exists(cursor: DictCursor, table_name: str, column_name: str) -> bool:
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


def _quote_selectable_expr(cursor: DictCursor) -> str:
    if _column_exists(cursor, "jurisdictions", "quote_selectable"):
        return "j.quote_selectable"
    return """
    CASE
      WHEN j.jurisdiction_type = 'single_country' THEN 1
      WHEN UPPER(j.internal_code) IN ('EP', 'EM', 'WO') THEN 1
      ELSE 0
    END
    """


def _quote_business_lines_expr(cursor: DictCursor) -> str:
    if _column_exists(cursor, "jurisdictions", "quote_business_lines_json"):
        return "j.quote_business_lines_json"
    return """
    CASE
      WHEN j.jurisdiction_type = 'single_country' THEN JSON_ARRAY('patent', 'trademark', 'design')
      WHEN UPPER(j.internal_code) = 'EP' THEN JSON_ARRAY('patent')
      WHEN UPPER(j.internal_code) = 'EM' THEN JSON_ARRAY('trademark', 'design')
      WHEN UPPER(j.internal_code) IN ('WO', 'PCT') THEN JSON_ARRAY('patent')
      WHEN UPPER(j.internal_code) = 'MADRID' THEN JSON_ARRAY('trademark')
      WHEN UPPER(j.internal_code) = 'HAGUE' THEN JSON_ARRAY('design')
      ELSE JSON_ARRAY()
    END
    """


def _quote_option_group_expr(cursor: DictCursor) -> str:
    if _column_exists(cursor, "jurisdictions", "quote_option_group"):
        return "j.quote_option_group"
    return """
    CASE
      WHEN j.jurisdiction_type = 'single_country' THEN 'single_country'
      WHEN UPPER(j.internal_code) IN ('EP', 'EM') THEN 'regional_office'
      WHEN UPPER(j.internal_code) = 'WO' THEN 'international_organization'
      WHEN UPPER(j.internal_code) IN ('PCT', 'MADRID', 'HAGUE') THEN 'treaty_route'
      WHEN UPPER(j.internal_code) IN ('EUROPE', 'EUR') OR j.name_cn = '欧洲' OR LOWER(j.name_en) = 'europe' THEN 'non_quote_region'
      ELSE j.jurisdiction_type
    END
    """


def _quote_display_name_expr(cursor: DictCursor) -> str:
    if _column_exists(cursor, "jurisdictions", "quote_display_name"):
        return "COALESCE(NULLIF(j.quote_display_name, ''), CONCAT(j.name_cn, ' (', j.display_code, ')'))"
    return """
    CASE
      WHEN UPPER(j.internal_code) = 'EP' OR UPPER(j.display_code) = 'EPO' THEN '欧洲专利局 (EPO)'
      WHEN UPPER(j.internal_code) = 'EM' OR UPPER(j.display_code) = 'EUIPO' THEN '欧盟知识产权局 (EUIPO)'
      WHEN UPPER(j.internal_code) = 'WO' OR UPPER(j.display_code) = 'WIPO' THEN '世界知识产权组织 / WIPO'
      WHEN UPPER(j.internal_code) = 'PCT' THEN 'PCT 国际阶段'
      WHEN UPPER(j.internal_code) = 'MADRID' THEN '马德里商标国际注册'
      WHEN UPPER(j.internal_code) = 'HAGUE' THEN '海牙外观设计国际注册'
      ELSE CONCAT(j.name_cn, ' (', j.display_code, ')')
    END
    """


def _not_selectable_reason_expr(cursor: DictCursor) -> str:
    if _column_exists(cursor, "jurisdictions", "not_selectable_reason"):
        return "j.not_selectable_reason"
    return """
    CASE
      WHEN UPPER(j.internal_code) = 'PCT' THEN 'PCT 国际阶段报价入口，待申请路径模块启用'
      WHEN UPPER(j.internal_code) = 'MADRID' THEN '商标国际注册路径入口，待申请路径模块启用'
      WHEN UPPER(j.internal_code) = 'HAGUE' THEN '外观设计国际注册路径入口，待申请路径模块启用'
      WHEN UPPER(j.internal_code) IN ('EUROPE', 'EUR') OR j.name_cn = '欧洲' OR LOWER(j.name_en) = 'europe' THEN '欧洲仅作为地理区域或商务/经济区域，不作为报价对象'
      ELSE NULL
    END
    """


def _seed_reference_registry_if_empty(cursor: DictCursor) -> None:
    if not _table_exists(cursor, "jurisdiction_reference_registry"):
        return
    columns = [
        "reference_id",
        "standard_code",
        "display_code",
        "name_cn",
        "name_en",
        "aliases_json",
        "jurisdiction_type",
        "reference_category",
        "business_scope_json",
        "visibility_scope",
        "candidate_status",
        "quote_selectable_default",
        "not_selectable_reason",
        "reserved_reason",
        "geo_region",
        "default_business_economic_regions_json",
        "source_id",
        "source_name",
        "source_url",
        "source_version",
        "source_note",
        "source_verified",
        "review_status",
        "is_active",
        "default_currency_legacy",
    ]
    placeholders = ", ".join(f"%({column})s" for column in columns)
    updates = ", ".join(
        f"{column} = IF({column} = '' OR {column} IS NULL, VALUES({column}), {column})"
        for column in columns
        if column not in {"reference_id", "standard_code"}
    )
    for item in default_registry_items():
        record = {
            "reference_id": item.reference_id,
            "standard_code": item.standard_code,
            "display_code": item.display_code,
            "name_cn": item.name_cn,
            "name_en": item.name_en,
            "aliases_json": json.dumps(list(item.aliases), ensure_ascii=False),
            "jurisdiction_type": item.jurisdiction_type,
            "reference_category": item.reference_category,
            "business_scope_json": json.dumps(list(item.business_scope), ensure_ascii=False),
            "visibility_scope": item.visibility_scope,
            "candidate_status": item.candidate_status,
            "quote_selectable_default": item.quote_selectable_default,
            "not_selectable_reason": item.not_selectable_reason,
            "reserved_reason": item.reserved_reason,
            "geo_region": item.geo_region,
            "default_business_economic_regions_json": json.dumps(list(item.default_business_economic_regions), ensure_ascii=False),
            "source_id": item.source_id,
            "source_name": item.source_name,
            "source_url": item.source_url,
            "source_version": item.source_version,
            "source_note": item.source_note,
            "source_verified": item.source_verified,
            "review_status": item.review_status,
            "is_active": item.is_active,
            "default_currency_legacy": item.default_currency_legacy,
        }
        cursor.execute(
            f"""
            INSERT INTO jurisdiction_reference_registry ({', '.join(columns)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {updates}
            """,
            record,
        )
    standard_code_match = (
        "OR UPPER(COALESCE(j.standard_code, '')) = UPPER(r.standard_code)"
        if _column_exists(cursor, "jurisdictions", "standard_code")
        else ""
    )
    cursor.execute(
        f"""
        UPDATE jurisdiction_reference_registry r
        JOIN jurisdictions j ON UPPER(j.internal_code) = UPPER(r.standard_code)
          OR UPPER(j.display_code) = UPPER(r.display_code)
          {standard_code_match}
        SET r.jurisdiction_id = j.jurisdiction_id,
            r.candidate_status = CASE
              WHEN r.candidate_status = 'candidate' THEN 'linked_formal_master'
              ELSE r.candidate_status
            END
        WHERE r.jurisdiction_id IS NULL
        """
    )


def _sync_reference_registry_link(cursor: DictCursor, standard_code: str, display_code: str) -> None:
    if not _table_exists(cursor, "jurisdiction_reference_registry"):
        return
    codes = sorted({standard_code.upper(), display_code.upper()} - {""})
    if not codes:
        return
    placeholders = ", ".join(["%s"] * len(codes))
    standard_code_match = (
        f"OR UPPER(COALESCE(j.standard_code, '')) IN ({placeholders})"
        if _column_exists(cursor, "jurisdictions", "standard_code")
        else ""
    )
    cursor.execute(
        f"""
        UPDATE jurisdiction_reference_registry r
        JOIN jurisdictions j ON (
          UPPER(j.internal_code) IN ({placeholders})
          OR UPPER(j.display_code) IN ({placeholders})
          {standard_code_match}
        )
        SET r.jurisdiction_id = j.jurisdiction_id,
            r.candidate_status = CASE
              WHEN r.candidate_status = 'candidate' THEN 'linked_formal_master'
              ELSE r.candidate_status
            END
        WHERE r.is_active = 1
          AND (
            UPPER(r.standard_code) IN ({placeholders})
            OR UPPER(r.display_code) IN ({placeholders})
          )
        """,
        tuple(codes + codes + (codes if standard_code_match else []) + codes + codes),
    )


def _fallback_reference_registry(keyword: str, include_hidden: bool) -> list[dict[str, object]]:
    normalized = keyword.strip().lower()
    rows: list[dict[str, object]] = []
    for item in default_registry_items():
        if not item.is_active:
            continue
        if not include_hidden and item.visibility_scope == "reserved_hidden":
            continue
        values = [item.name_cn, item.name_en, item.standard_code, item.display_code, *item.aliases]
        if normalized and not any(normalized in str(value).lower() for value in values):
            continue
        rows.append(_reference_registry_row({
            "reference_id": item.reference_id,
            "jurisdiction_id": None,
            "standard_code": item.standard_code,
            "display_code": item.display_code,
            "name_cn": item.name_cn,
            "name_en": item.name_en,
            "aliases_json": json.dumps(list(item.aliases), ensure_ascii=False),
            "jurisdiction_type": item.jurisdiction_type,
            "reference_category": item.reference_category,
            "business_scope_json": json.dumps(list(item.business_scope), ensure_ascii=False),
            "visibility_scope": item.visibility_scope,
            "candidate_status": item.candidate_status,
            "quote_selectable_default": item.quote_selectable_default,
            "not_selectable_reason": item.not_selectable_reason,
            "reserved_reason": item.reserved_reason,
            "geo_region": item.geo_region,
            "default_business_economic_regions_json": json.dumps(list(item.default_business_economic_regions), ensure_ascii=False),
            "source_id": item.source_id,
            "source_name": item.source_name,
            "source_url": item.source_url,
            "source_version": item.source_version,
            "source_note": item.source_note,
            "source_verified": item.source_verified,
            "source_verified_at": None,
            "source_verified_by": None,
            "last_reviewed_at": None,
            "next_review_due_at": None,
            "review_status": item.review_status,
            "is_active": item.is_active,
            "default_currency_legacy": item.default_currency_legacy,
        }))
    return rows[:500]


def _reference_registry_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["jurisdiction_id"] = normalized.get("jurisdiction_id") or normalized.get("matched_jurisdiction_id")
    normalized["aliases"] = _loads_json_list(normalized.pop("aliases_json", None))
    normalized["business_scope"] = _loads_json_list(normalized.pop("business_scope_json", None))
    normalized["default_business_economic_regions"] = _loads_json_list(
        normalized.pop("default_business_economic_regions_json", None)
    )
    normalized["quote_selectable_default"] = _truthy(normalized.get("quote_selectable_default"))
    normalized["source_verified"] = _truthy(normalized.get("source_verified"))
    normalized["is_active"] = _truthy(normalized.get("is_active"), default=True)
    return normalized


def _data_source_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["applicable_fields"] = _loads_json_list(normalized.pop("applicable_fields_json", None))
    normalized["source_verified"] = _truthy(normalized.get("source_verified"))
    normalized["is_active"] = _truthy(normalized.get("is_active"), default=True)
    return normalized


def _region_tag_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["source_verified"] = _truthy(normalized.get("source_verified"))
    normalized["is_active"] = _truthy(normalized.get("is_active"), default=True)
    return normalized


def _apply_jurisdiction_country_defaults(country: dict[str, object]) -> None:
    code = str(country.get("code") or "")
    country["jurisdiction_id"] = country.get("jurisdiction_id") or None
    country["internal_code"] = country.get("internal_code") or code
    country["display_code"] = country.get("display_code") or code
    country["jurisdiction_type"] = country.get("jurisdiction_type") or country.get("country_type") or ""
    country["is_enabled"] = country.get("is_enabled") if country.get("is_enabled") is not None else country.get("enabled")
    for key in ("source_name", "source_url", "source_version"):
        country[key] = country.get(key) or ""
    country["standard_code"] = country.get("standard_code") or country["internal_code"]
    country["source_note"] = country.get("source_note") or ""
    country["source_verified"] = bool(country.get("source_verified") or False)
    country["source_verified_at"] = country.get("source_verified_at") or country.get("last_verified_at")
    country["source_verified_by"] = country.get("source_verified_by") or ""
    country["manual_override"] = bool(country.get("manual_override") or False)
    country["remarks"] = country.get("remarks") or ""
    country["is_deleted"] = bool(country.get("is_deleted") or False)
    country["deleted_at"] = country.get("deleted_at") or None
    country["deleted_by"] = country.get("deleted_by") or ""
    country["delete_reason"] = country.get("delete_reason") or ""


def _fetch_matching_orphan_jurisdictions(cursor: DictCursor, codes: list[str]) -> list[dict[str, object]]:
    if not _table_exists(cursor, "jurisdictions") or not codes:
        return []
    placeholders = ", ".join(["%s"] * len(codes))
    where_parts: list[str] = []
    params: list[object] = []
    for column in ("internal_code", "display_code", "wipo_st3_code", "standard_code"):
        if _column_exists(cursor, "jurisdictions", column):
            where_parts.append(f"UPPER(j.{column}) IN ({placeholders})")
            params.extend(codes)
    if not where_parts:
        return []
    standard_code_expr = (
        "j.standard_code"
        if _column_exists(cursor, "jurisdictions", "standard_code")
        else "j.internal_code"
    )
    jurisdiction_deleted_expr = (
        "COALESCE(j.is_deleted, 0)"
        if _column_exists(cursor, "jurisdictions", "is_deleted")
        else "CASE WHEN j.is_enabled = 0 THEN 1 ELSE 0 END"
    )
    map_join = (
        "LEFT JOIN country_jurisdiction_map m ON m.jurisdiction_id = j.jurisdiction_id"
        if _table_exists(cursor, "country_jurisdiction_map")
        else ""
    )
    map_filter = "AND m.jurisdiction_id IS NULL" if map_join else ""
    cursor.execute(
        f"""
        SELECT NULL AS country_code, NULL AS country_enabled, 0 AS country_deleted,
               NULL AS mapped_jurisdiction_id,
               j.jurisdiction_id, j.internal_code, {standard_code_expr} AS standard_code,
               j.display_code, j.wipo_st3_code, j.is_enabled AS jurisdiction_enabled,
               {jurisdiction_deleted_expr} AS jurisdiction_deleted
        FROM jurisdictions j
        {map_join}
        WHERE ({' OR '.join(where_parts)})
          {map_filter}
        """,
        tuple(params),
    )
    return _normalize_text_records(cursor.fetchall())


def _classify_country_reference_status(
    codes: list[str],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    if not rows:
        return {"status": "not_exists", "matched_codes": codes}

    active_row: dict[str, object] | None = None
    deleted_row: dict[str, object] | None = None
    legacy_row: dict[str, object] | None = None
    matched_fields: set[str] = set()
    normalized_codes = {code.upper() for code in codes}
    for row in rows:
        for field in ("country_code", "internal_code", "standard_code", "display_code", "wipo_st3_code"):
            value = str(row.get(field) or "").upper()
            if value in normalized_codes:
                matched_fields.add(field)

        country_exists = bool(row.get("country_code"))
        jurisdiction_exists = bool(row.get("jurisdiction_id") or row.get("mapped_jurisdiction_id"))
        country_deleted = _truthy(row.get("country_deleted"))
        jurisdiction_deleted = _truthy(row.get("jurisdiction_deleted"))
        country_enabled = _truthy(row.get("country_enabled"), default=True)
        jurisdiction_enabled = _truthy(row.get("jurisdiction_enabled"), default=True)

        if country_exists and jurisdiction_exists and country_enabled and jurisdiction_enabled and not country_deleted and not jurisdiction_deleted:
            active_row = row
            break
        if country_deleted or jurisdiction_deleted:
            deleted_row = deleted_row or row
        else:
            legacy_row = legacy_row or row

    selected = active_row or deleted_row or legacy_row or rows[0]
    if active_row:
        status = "active_exists"
    elif deleted_row:
        status = "soft_deleted_exists"
    else:
        status = "legacy_exists_only"

    return {
        "status": status,
        "matched_codes": codes,
        "matched_fields": sorted(matched_fields),
        "country_code": selected.get("country_code"),
        "jurisdiction_id": selected.get("jurisdiction_id") or selected.get("mapped_jurisdiction_id"),
        "rows": rows,
    }


def _truthy(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _country_jurisdiction_id(cursor: DictCursor, country_code: str) -> str | None:
    if not _table_exists(cursor, "country_jurisdiction_map"):
        return None
    cursor.execute(
        """
        SELECT COALESCE(c.jurisdiction_id, m.jurisdiction_id) AS jurisdiction_id
        FROM countries c
        LEFT JOIN country_jurisdiction_map m ON m.country_code = c.code
        WHERE c.code = %s
        LIMIT 1
        """,
        (country_code,),
    )
    row = cursor.fetchone()
    return str(row["jurisdiction_id"]) if row and row.get("jurisdiction_id") else None


def _country_business_reference_counts(
    cursor: DictCursor,
    country_code: str,
    jurisdiction_id: str | None,
) -> list[dict[str, object]]:
    excluded_tables = {"countries", "jurisdictions", "country_jurisdiction_map"}
    reference_counts: dict[str, int] = {}
    cursor.execute(
        """
        SELECT DISTINCT TABLE_NAME AS table_name
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND COLUMN_NAME IN ('country_code', 'jurisdiction_id')
        """
    )
    table_names = [
        str(row["table_name"])
        for row in cursor.fetchall()
        if str(row["table_name"]) not in excluded_tables
    ]
    for table_name in table_names:
        where_parts: list[str] = []
        params: list[object] = []
        if _column_exists(cursor, table_name, "country_code"):
            where_parts.append("country_code = %s")
            params.append(country_code)
        if jurisdiction_id and _column_exists(cursor, table_name, "jurisdiction_id"):
            where_parts.append("jurisdiction_id = %s")
            params.append(jurisdiction_id)
        if not where_parts:
            continue
        where_sql = " OR ".join(where_parts)
        cursor.execute(
            f"SELECT COUNT(*) AS count_value FROM `{table_name}` WHERE {where_sql}",
            tuple(params),
        )
        count = int(cursor.fetchone()["count_value"] or 0)
        if count:
            reference_counts[table_name] = count

    ordered = sorted(reference_counts.items(), key=lambda item: item[0])
    return [{"table": table, "count": count} for table, count in ordered]


def _format_country_reference_block_message(references: list[dict[str, object]]) -> str:
    summary = "，".join(f"{item['table']}:{item['count']}" for item in references[:8])
    if len(references) > 8:
        summary = f"{summary}，等 {len(references)} 个表"
    return f"该对象已有业务数据引用，请改为停用。引用明细：{summary}"


def _update_country_jurisdiction(
    cursor: DictCursor,
    country_code: str,
    values: dict[str, object],
) -> None:
    cursor.execute(
        """
        SELECT code, name_cn, name_en, country_type, enabled, display_order
        FROM countries
        WHERE code = %s
        LIMIT 1
        """,
        (country_code,),
    )
    country = cursor.fetchone()
    if country is None:
        raise KeyError(country_code)

    jurisdiction_id = _ensure_country_jurisdiction(cursor, country)
    updates = _jurisdiction_updates_from_country_values(cursor, country, values)
    if not updates:
        return
    assignments = ", ".join(f"{key} = %s" for key in updates)
    params = tuple(updates.values()) + (jurisdiction_id,)
    cursor.execute(
        f"UPDATE jurisdictions SET {assignments} WHERE jurisdiction_id = %s",
        params,
    )


def _ensure_country_jurisdiction(cursor: DictCursor, country: dict[str, object]) -> str:
    country_code = str(country["code"])
    default_jurisdiction_id = f"jur-{country_code}"
    cursor.execute(
        """
        SELECT m.jurisdiction_id
        FROM country_jurisdiction_map m
        WHERE m.country_code = %s
        LIMIT 1
        """,
        (country_code,),
    )
    mapped = cursor.fetchone()
    if mapped:
        return str(mapped["jurisdiction_id"])

    cursor.execute(
        """
        INSERT INTO jurisdictions (
          jurisdiction_id, internal_code, display_code, name_cn, name_en,
          jurisdiction_type, is_enabled, display_order, wipo_st3_code,
          source_name, source_version, manual_override, remarks
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'legacy_countries',
                'phase_1_jurisdiction_compat', 1, %s)
        ON DUPLICATE KEY UPDATE
          name_cn = VALUES(name_cn),
          name_en = VALUES(name_en)
        """,
        (
            default_jurisdiction_id,
            country_code,
            "EPO" if country_code == "EP" else country_code,
            country["name_cn"],
            country["name_en"],
            _default_jurisdiction_type(country_code, country.get("country_type")),
            country["enabled"],
            country.get("display_order") or 100,
            "EP" if country_code == "EP" else country_code,
            f"Backfilled from legacy countries.code={country_code}",
        ),
    )
    cursor.execute(
        """
        INSERT INTO country_jurisdiction_map (
          country_code, jurisdiction_id, mapping_type, is_primary, remarks
        )
        VALUES (%s, %s, 'legacy_country_code', 1,
                'Phase 1 compatibility bridge; legacy country_code remains the active runtime key.')
        """,
        (country_code, default_jurisdiction_id),
    )
    cursor.execute(
        "UPDATE countries SET jurisdiction_id = %s WHERE code = %s AND jurisdiction_id IS NULL",
        (default_jurisdiction_id, country_code),
    )
    return default_jurisdiction_id


def _jurisdiction_updates_from_country_values(
    cursor: DictCursor,
    country: dict[str, object],
    values: dict[str, object],
) -> dict[str, object]:
    country_code = str(country["code"])
    field_map = {
        "name_cn": "name_cn",
        "name_en": "name_en",
        "display_order": "display_order",
        "internal_code": "internal_code",
        "display_code": "display_code",
        "standard_code": "standard_code",
        "jurisdiction_type": "jurisdiction_type",
        "is_enabled": "is_enabled",
        "iso_alpha2": "iso_alpha2",
        "iso_alpha3": "iso_alpha3",
        "iso_numeric": "iso_numeric",
        "un_m49_code": "un_m49_code",
        "wipo_st3_code": "wipo_st3_code",
        "source_name": "source_name",
        "source_url": "source_url",
        "source_version": "source_version",
        "source_note": "source_note",
        "last_verified_at": "last_verified_at",
        "source_verified": "source_verified",
        "source_verified_at": "source_verified_at",
        "source_verified_by": "source_verified_by",
        "manual_override": "manual_override",
        "remarks": "remarks",
        "quote_selectable": "quote_selectable",
        "quote_business_lines_json": "quote_business_lines_json",
        "quote_option_group": "quote_option_group",
        "quote_display_name": "quote_display_name",
        "not_selectable_reason": "not_selectable_reason",
    }
    updates = {
        target: _normalize_nullable_code_value(value)
        for source, target in field_map.items()
        if source in values
        for value in [values[source]]
        if _column_exists(cursor, "jurisdictions", target)
    }
    if "enabled" in values and "is_enabled" not in updates:
        updates["is_enabled"] = values["enabled"]
    if "country_type" in values and "jurisdiction_type" not in updates:
        updates["jurisdiction_type"] = values["country_type"]
    updates.setdefault("internal_code", country_code)
    if "display_code" in updates and not updates["display_code"]:
        updates["display_code"] = country_code
    if "internal_code" in updates and not updates["internal_code"]:
        updates["internal_code"] = country_code
    return updates


def _normalize_nullable_code_value(value: object) -> object:
    return None if value == "" else value


def _default_jurisdiction_type(country_code: str, country_type: object) -> str:
    if country_code.upper() in {"HK", "MO", "TW"} or str(country_type or "") in {"特殊地区", "地区"}:
        return "special_region"
    if country_code == "EP" or str(country_type or "") == "区域局":
        return "regional_office"
    return "single_country"


def _update_table_record(
    table: str,
    key_column: str,
    key_value: str,
    values: dict[str, object],
    allowed: set[str],
) -> None:
    updates = {key: value for key, value in values.items() if key in allowed}
    with connection_scope() as connection, connection.cursor() as cursor:
        if updates:
            assignments = ", ".join(f"{key} = %s" for key in updates)
            params = tuple(updates.values()) + (key_value,)
            cursor.execute(f"UPDATE {table} SET {assignments} WHERE {key_column} = %s", params)
            if cursor.rowcount == 0:
                raise KeyError(key_value)
        else:
            cursor.execute(f"SELECT {key_column} FROM {table} WHERE {key_column} = %s LIMIT 1", (key_value,))
            if cursor.fetchone() is None:
                raise KeyError(key_value)


def _delete_table_record(table: str, key_column: str, key_value: str) -> None:
    with connection_scope() as connection, connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE {key_column} = %s", (key_value,))
        if cursor.rowcount == 0:
            raise KeyError(key_value)


def _find_config_record(section: str, record_id: str) -> dict[str, object]:
    rows = fetch_country_config()[section]
    for row in rows:
        if row["id"] == record_id:
            return row
    raise KeyError(record_id)


def _insert_customer_contact(cursor: DictCursor, contact: dict[str, object]) -> None:
    cursor.execute(
        """
        INSERT INTO customer_contacts (
          id, customer_id, name, title, email, phone, wechat, is_primary,
          remark, created_at, updated_at
        )
        VALUES (
          %(id)s, %(customer_id)s, %(name)s, %(title)s, %(email)s, %(phone)s,
          %(wechat)s, %(is_primary)s, %(remark)s, %(created_at)s, %(updated_at)s
        )
        """,
        contact,
    )
