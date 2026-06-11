from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from app.main import app


def test_quotation_draft_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/customers" in paths
    assert "/api/v1/customers/{customer_id}" in paths
    assert "/api/v1/customers/{customer_id}/contacts" in paths
    assert "/api/v1/customers/{customer_id}/contacts/{contact_id}" in paths
    assert "/api/v1/quotation-drafts" in paths
    assert "/api/v1/quotation-drafts/{draft_id}" in paths
    assert "/api/v1/quotation-drafts/{draft_id}/items/{item_id}" in paths
    assert "/api/v1/quotation-workbench/options" in paths
    assert "/api/v1/quote/jurisdiction-options-preview" in paths
    assert "/api/v1/jurisdiction-references" in paths
    assert "/api/v1/jurisdiction-data-sources" in paths
    assert "/api/v1/jurisdiction-data-sources/{source_id}" in paths
    assert "/api/v1/jurisdiction-region-tags" in paths
    assert "/api/v1/quotations/from-drafts" in paths
    assert "/api/v1/fee-rules" in paths
    assert "/api/v1/fee-rules/{rule_id}" in paths
    assert "/api/v1/country-path-rules" in paths
    assert "/api/v1/countries/bulk-from-reference" in paths
    assert "/api/v1/countries/{country_code}" in paths
    assert "/api/v1/country-path-rules/{rule_id}" in paths
    assert "/api/v1/entity-type-rules" in paths
    assert "/api/v1/entity-type-rules/{rule_id}" in paths
    assert "/api/v1/language-rules" in paths
    assert "/api/v1/language-rules/{rule_id}" in paths
    assert "/api/v1/fx-tax-rules" in paths
    assert "/api/v1/fx-tax-rules/{rule_id}" in paths
    assert "/api/v1/special-rules" in paths
    assert "/api/v1/special-rules/{rule_id}" in paths


@pytest.mark.anyio
async def test_country_delete_business_reference_error_is_explicit(monkeypatch) -> None:
    from app.api.v1 import router

    monkeypatch.setattr(
        router.mysql,
        "fetch_user_by_email",
        lambda email: {"id": "admin", "email": email, "role": "admin", "status": "active"},
    )

    def blocked(country_code, delete_reason, current_user):
        raise ValueError("该对象已有正式业务数据引用，请改为停用。引用明细：历史报价:1")

    monkeypatch.setattr(router, "delete_country_config", blocked)

    with pytest.raises(HTTPException) as exc_info:
        await router.delete_country_config_route(
            "NL",
            router.CountryDeleteRequest(delete_reason="test"),
            authorization=None,
            x_user_email="admin@example.com",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "COUNTRY_HAS_BUSINESS_REFERENCES"
    assert "该对象已有正式业务数据引用，请改为停用" in exc_info.value.detail["message"]


@pytest.mark.anyio
async def test_country_delete_success_returns_deleted_true(monkeypatch) -> None:
    from app.api.v1 import router

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        router.mysql,
        "fetch_user_by_email",
        lambda email: {"id": "admin", "email": email, "role": "admin", "status": "active"},
    )

    def delete(country_code, delete_reason, current_user):
        calls.append((country_code, delete_reason))

    monkeypatch.setattr(router, "delete_country_config", delete)

    response = await router.delete_country_config_route(
        "NL",
        router.CountryDeleteRequest(delete_reason="registry only"),
        authorization=None,
        x_user_email="admin@example.com",
    )

    assert response == {"deleted": True}
    assert calls == [("NL", "registry only")]


def test_soft_delete_registry_only_updates_country_and_jurisdiction(monkeypatch) -> None:
    from app.db import mysql

    class FakeCursor:
        def __init__(self) -> None:
            self.statements: list[tuple[str, tuple[object, ...]]] = []
            self._next_row: dict[str, object] | None = None

        def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
            self.statements.append((sql, params))
            if "SELECT code FROM countries" in sql:
                self._next_row = {"code": "CO"}
            elif "SELECT * FROM countries" in sql:
                self._next_row = {"code": "CO", "enabled": 1}
            else:
                self._next_row = None

        def fetchone(self) -> dict[str, object] | None:
            return self._next_row

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

    class FakeConnection:
        def __init__(self, cursor: FakeCursor) -> None:
            self.cursor_instance = cursor
            self.committed = False

        def cursor(self) -> FakeCursor:
            return self.cursor_instance

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            raise AssertionError("registry-only delete should not rollback")

        def close(self) -> None:
            pass

    cursor = FakeCursor()
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_connection_scope():
        yield connection
        connection.commit()

    delete_columns = {"is_deleted", "deleted_at", "deleted_by", "delete_reason"}
    monkeypatch.setattr(mysql, "connection_scope", fake_connection_scope)
    monkeypatch.setattr(mysql, "_jurisdiction_compat_available", lambda cursor: True)
    monkeypatch.setattr(mysql, "_country_jurisdiction_id", lambda cursor, country_code: "jur-CO")
    monkeypatch.setattr(mysql, "_country_business_reference_counts", lambda cursor, country_code, jurisdiction_id: [])
    monkeypatch.setattr(mysql, "_table_exists", lambda cursor, table_name: table_name == "jurisdictions")
    monkeypatch.setattr(mysql, "_column_exists", lambda cursor, table_name, column_name: column_name in delete_columns)

    result = mysql.soft_delete_country_config("CO", "admin@example.com", "registry only")

    assert result == {"code": "CO", "deleted": True}
    update_sql = [sql for sql, _ in cursor.statements if sql.startswith("UPDATE")]
    assert any("UPDATE countries SET" in sql and "is_deleted" in sql and "deleted_at" in sql for sql in update_sql)
    assert any("UPDATE jurisdictions SET" in sql and "is_deleted" in sql and "deleted_at" in sql for sql in update_sql)
    assert connection.committed is True


def test_soft_delete_accepts_display_code_and_blocks_business_references(monkeypatch) -> None:
    from app.db import mysql

    class FakeCursor:
        def __init__(self) -> None:
            self.statements: list[tuple[str, tuple[object, ...]]] = []
            self._next_row: dict[str, object] | None = None

        def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
            self.statements.append((sql, params))
            if "SELECT code FROM countries" in sql:
                self._next_row = None
            elif "FROM jurisdictions j" in sql:
                self._next_row = {"code": "EP"}
            elif "SELECT * FROM countries" in sql:
                self._next_row = {"code": "EP", "enabled": 1}
            else:
                self._next_row = None

        def fetchone(self) -> dict[str, object] | None:
            return self._next_row

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

    class FakeConnection:
        def __init__(self, cursor: FakeCursor) -> None:
            self.cursor_instance = cursor

        def cursor(self) -> FakeCursor:
            return self.cursor_instance

        def commit(self) -> None:
            raise AssertionError("blocked delete should not commit")

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    cursor = FakeCursor()

    @contextmanager
    def fake_connection_scope():
        connection = FakeConnection(cursor)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    monkeypatch.setattr(mysql, "connection_scope", fake_connection_scope)
    monkeypatch.setattr(mysql, "_jurisdiction_compat_available", lambda cursor: True)
    monkeypatch.setattr(mysql, "_country_jurisdiction_id", lambda cursor, country_code: "jur-EP")
    monkeypatch.setattr(
        mysql,
        "_country_business_reference_counts",
        lambda cursor, country_code, jurisdiction_id: [{"table": "country_path_rules", "count": 1}],
    )
    monkeypatch.setattr(mysql, "_column_exists", lambda cursor, table_name, column_name: column_name in {"display_code", "wipo_st3_code", "standard_code"})

    with pytest.raises(ValueError) as exc_info:
        mysql.soft_delete_country_config("EPO", "admin@example.com", "has business reference")

    assert "该对象已有正式业务数据引用，请改为停用" in str(exc_info.value)
    assert "jurisdiction_reference_registry" not in str(exc_info.value)
    assert not any(sql.startswith("UPDATE") for sql, _ in cursor.statements)
