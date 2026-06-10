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
