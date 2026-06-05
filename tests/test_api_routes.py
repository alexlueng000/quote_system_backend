from app.main import app


def test_quotation_draft_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/quotation-drafts" in paths
    assert "/api/v1/quotation-drafts/{draft_id}" in paths
    assert "/api/v1/quotation-drafts/{draft_id}/items/{item_id}" in paths
    assert "/api/v1/quotations/from-drafts" in paths
