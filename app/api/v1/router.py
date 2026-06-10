from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pymysql.err import IntegrityError

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db import mysql
from app.schemas.quotation import (
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalRequestReview,
    BootstrapResponse,
    CustomerContactCreate,
    CustomerContactResponse,
    CustomerContactUpdate,
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
    Country,
    CountryBulkFromReferenceRequest,
    CountryBulkFromReferenceResponse,
    CountryCreate,
    CountryConfigResponse,
    CountryDeleteRequest,
    CountryPathRule,
    CountryPathRuleCreate,
    CountryPathRuleUpdate,
    CountryUpdate,
    EntityTypeRule,
    EntityTypeRuleCreate,
    EntityTypeRuleUpdate,
    FeeRule,
    FeeRuleCreate,
    FeeRuleUpdate,
    FollowupCreate,
    FollowupResponse,
    FxTaxRule,
    FxTaxRuleCreate,
    FxTaxRuleUpdate,
    GeneratedQuotation,
    JurisdictionDataSource,
    JurisdictionDataSourceCreate,
    JurisdictionDataSourceUpdate,
    JurisdictionReferenceListResponse,
    JurisdictionRegionTag,
    JurisdictionRegionTagCreate,
    LanguageRule,
    LanguageRuleCreate,
    LanguageRuleUpdate,
    LoginRequest,
    LoginResponse,
    QuoteJurisdictionOptionPreview,
    QuotationCreate,
    QuotationDraftCreate,
    QuotationDraftListResponse,
    QuotationDraftResponse,
    QuotationDraftUpdate,
    QuotationFromDraftsCreate,
    QuotationGenerateRequest,
    QuotationListResponse,
    QuotationResponse,
    QuotationStatusUpdate,
    StatisticsResponse,
    SpecialRule,
    SpecialRuleCreate,
    SpecialRuleUpdate,
    TranslationRule,
    TranslationRuleUpdate,
    User,
    UserCreate,
    UserPasswordUpdate,
    UserUpdate,
    WorkbenchOptionsResponse,
)
from app.services.customer_service import (
    create_customer,
    create_customer_contact,
    delete_customer_contact,
    get_customer,
    get_customers,
    update_customer,
    update_customer_contact,
)
from app.services.quotation_service import (
    create_approval_request,
    create_country_config,
    create_countries_from_reference_bulk,
    create_jurisdiction_data_source,
    create_jurisdiction_region_tag,
    create_country_path_rule,
    create_entity_type_rule,
    create_fee_rule,
    create_fx_tax_rule,
    create_followup as create_followup_record,
    create_language_rule,
    create_quotation,
    create_quotation_draft,
    create_quotation_from_drafts,
    create_special_rule,
    delete_country_config,
    delete_country_path_rule,
    delete_entity_type_rule,
    delete_fee_rule,
    delete_fx_tax_rule,
    delete_language_rule,
    delete_quotation_draft_item,
    delete_special_rule,
    fetch_quote_jurisdiction_options_preview,
    list_jurisdiction_data_sources,
    list_jurisdiction_references,
    list_jurisdiction_region_tags,
    generate_quotation,
    get_bootstrap,
    get_approval_requests,
    get_country_config,
    get_fee_rules,
    get_quotation,
    get_quotation_draft,
    get_quotation_drafts,
    get_quotations,
    get_statistics,
    get_translation_rules,
    get_workbench_options,
    restore_country_config,
    update_quotation_status,
    update_quotation_draft,
    review_approval_request,
    update_country_config,
    update_jurisdiction_data_source,
    update_country_path_rule,
    update_entity_type_rule,
    update_fee_rule,
    update_fx_tax_rule,
    update_language_rule,
    update_special_rule,
    update_translation_rule,
)
from app.services.export_service import build_quotation_workbook
from app.api.v1.ip_systems import router as ip_systems_router
from app.api.v1.ip_system_query import router as ip_system_query_router

api_router = APIRouter()
api_router.include_router(ip_systems_router)
api_router.include_router(ip_system_query_router)


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, object] | None:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_token(token)
        if payload:
            user = mysql.fetch_user_by_email(str(payload.get("email", "")))
            if user and user["status"] == "active":
                return user
    if x_user_email:
        user = mysql.fetch_user_by_email(x_user_email)
        if user and user["status"] == "active":
            return user
    return None


def require_admin(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, object]:
    user = get_current_user(authorization, x_user_email)
    if user is None or user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_REQUIRED", "message": "Admin permission required"},
        )
    return user


def require_consultant(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> None:
    user = get_current_user(authorization, x_user_email)
    if user is None or user["role"] != "consultant":
        raise HTTPException(
            status_code=403,
            detail={"code": "CONSULTANT_REQUIRED", "message": "Consultant permission required"},
        )


def require_quote_user(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, object]:
    user = get_current_user(authorization, x_user_email)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    if user["role"] not in {"consultant", "admin"}:
        raise HTTPException(
            status_code=403,
            detail={"code": "ROLE_FORBIDDEN", "message": "Role access forbidden"},
        )
    return user


def require_approval_user(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, object]:
    user = get_current_user(authorization, x_user_email)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    if user["role"] not in {"admin", "approver"}:
        raise HTTPException(
            status_code=403,
            detail={"code": "APPROVAL_REQUIRED", "message": "Approval permission required"},
        )
    return user


def require_quotation_access(
    quotation_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> tuple[QuotationResponse, dict[str, object]]:
    current_user = get_current_user(authorization, x_user_email)
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    try:
        quotation = get_quotation(quotation_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUOTATION_NOT_FOUND", "message": "Quotation not found"},
        ) from exc
    if current_user["role"] == "admin":
        return quotation, current_user
    if current_user["role"] == "consultant" and quotation.consultant_email == current_user["email"]:
        return quotation, current_user
    raise HTTPException(
        status_code=403,
        detail={"code": "QUOTATION_FORBIDDEN", "message": "Quotation access forbidden"},
    )


def require_draft_access(
    draft_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> tuple[QuotationDraftResponse, dict[str, object]]:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        draft = get_quotation_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRAFT_NOT_FOUND", "message": "Quotation draft not found"},
        ) from exc
    if current_user["role"] == "admin":
        return draft, current_user
    if current_user["role"] == "consultant" and draft.consultant_email == current_user["email"]:
        return draft, current_user
    raise HTTPException(
        status_code=403,
        detail={"code": "DRAFT_FORBIDDEN", "message": "Quotation draft access forbidden"},
    )


@api_router.post("/auth/login")
async def login(payload: LoginRequest) -> LoginResponse:
    user = mysql.fetch_auth_user_by_email(payload.email)
    if (
        user is None
        or user["status"] != "active"
        or not verify_password(payload.password, str(user.get("password_hash") or ""))
    ):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )
    public_user = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
    }
    return LoginResponse(token=create_token(public_user), user=public_user)


@api_router.get("/bootstrap")
async def bootstrap() -> BootstrapResponse:
    return get_bootstrap()


@api_router.get("/customers")
async def list_customers(
    keyword: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerListResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    return get_customers(current_user, keyword=keyword)


@api_router.post("/customers")
async def post_customer(
    payload: CustomerCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_customer(payload, current_user)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CONSULTANT_NOT_FOUND", "message": "Consultant not found"},
        ) from exc


@api_router.get("/customers/{customer_id}")
async def retrieve_customer(
    customer_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return get_customer(customer_id, current_user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "CUSTOMER_FORBIDDEN", "message": "Customer access forbidden"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found"},
        ) from exc


@api_router.patch("/customers/{customer_id}")
async def patch_customer(
    customer_id: str,
    payload: CustomerUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_customer(customer_id, payload, current_user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "CUSTOMER_FORBIDDEN", "message": "Customer access forbidden"},
        ) from exc
    except KeyError as exc:
        message = str(exc)
        code = "CONSULTANT_NOT_FOUND" if "CONSULTANT_NOT_FOUND" in message else "CUSTOMER_NOT_FOUND"
        raise HTTPException(
            status_code=404,
            detail={"code": code, "message": "Customer or consultant not found"},
        ) from exc


@api_router.post("/customers/{customer_id}/contacts")
async def post_customer_contact(
    customer_id: str,
    payload: CustomerContactCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerContactResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_customer_contact(customer_id, payload, current_user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "CUSTOMER_FORBIDDEN", "message": "Customer access forbidden"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found"},
        ) from exc


@api_router.patch("/customers/{customer_id}/contacts/{contact_id}")
async def patch_customer_contact(
    customer_id: str,
    contact_id: str,
    payload: CustomerContactUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerContactResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_customer_contact(customer_id, contact_id, payload, current_user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "CUSTOMER_FORBIDDEN", "message": "Customer access forbidden"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CUSTOMER_CONTACT_NOT_FOUND", "message": "Customer contact not found"},
        ) from exc


@api_router.delete("/customers/{customer_id}/contacts/{contact_id}")
async def delete_contact(
    customer_id: str,
    contact_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CustomerResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return delete_customer_contact(customer_id, contact_id, current_user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "CUSTOMER_FORBIDDEN", "message": "Customer access forbidden"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "CUSTOMER_CONTACT_NOT_FOUND", "message": "Customer contact not found"},
        ) from exc


@api_router.get("/users")
async def list_users(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[User]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return [User.model_validate(user) for user in mysql.fetch_all_users()]


@api_router.post("/users")
async def create_user(
    payload: UserCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> User:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        user = mysql.insert_user(
            {
                "name": payload.name,
                "email": payload.email,
                "password_hash": hash_password(payload.password),
                "role": payload.role,
                "status": payload.status,
            }
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "USER_EMAIL_EXISTS", "message": "Email already exists"},
        ) from exc
    return User.model_validate(user)


@api_router.patch("/users/{user_id}")
async def patch_user(
    user_id: str,
    payload: UserUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> User:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        user = mysql.update_user(user_id, payload.model_dump(exclude_unset=True))
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "USER_EMAIL_EXISTS", "message": "Email already exists"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        ) from exc
    return User.model_validate(user)


@api_router.patch("/users/{user_id}/password")
async def patch_user_password(
    user_id: str,
    payload: UserPasswordUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> User:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        user = mysql.update_user_password(user_id, hash_password(payload.password))
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        ) from exc
    return User.model_validate(user)


@api_router.post("/quotations/generate")
async def generate(payload: QuotationGenerateRequest) -> GeneratedQuotation:
    return generate_quotation(payload)


@api_router.get("/quotation-workbench/options")
async def quotation_workbench_options(
    country_code: str | None = Query(default=None),
    application_type: str | None = Query(default=None),
    filing_route: str | None = Query(default=None),
) -> WorkbenchOptionsResponse:
    return get_workbench_options(country_code, application_type, filing_route)


@api_router.get("/quote/jurisdiction-options-preview")
async def quote_jurisdiction_options_preview(
    selectable_only: bool = Query(default=False),
    business_line: str | None = Query(default=None),
    option_group: str | None = Query(default=None),
) -> list[QuoteJurisdictionOptionPreview]:
    return fetch_quote_jurisdiction_options_preview(
        selectable_only=selectable_only,
        business_line=business_line,
        option_group=option_group,
    )


@api_router.get("/jurisdiction-references")
async def jurisdiction_references(
    keyword: str = Query(default=""),
    include_hidden: bool = Query(default=False),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> JurisdictionReferenceListResponse:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return list_jurisdiction_references(keyword=keyword, include_hidden=include_hidden)


@api_router.get("/jurisdiction-data-sources")
async def jurisdiction_data_sources(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[JurisdictionDataSource]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return list_jurisdiction_data_sources()


@api_router.post("/jurisdiction-data-sources")
async def post_jurisdiction_data_source(
    payload: JurisdictionDataSourceCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> JurisdictionDataSource:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return create_jurisdiction_data_source(payload)


@api_router.patch("/jurisdiction-data-sources/{source_id}")
async def patch_jurisdiction_data_source(
    source_id: str,
    payload: JurisdictionDataSourceUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> JurisdictionDataSource:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_jurisdiction_data_source(source_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND", "message": "Data source not found"},
        ) from exc


@api_router.get("/jurisdiction-region-tags")
async def jurisdiction_region_tags(
    jurisdiction_id: str | None = Query(default=None),
    tag_code: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[JurisdictionRegionTag]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return list_jurisdiction_region_tags(jurisdiction_id=jurisdiction_id, tag_code=tag_code)


@api_router.post("/jurisdiction-region-tags")
async def post_jurisdiction_region_tag(
    payload: JurisdictionRegionTagCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> JurisdictionRegionTag:
    current_user = require_admin(authorization=authorization, x_user_email=x_user_email)
    return create_jurisdiction_region_tag(payload, current_user)


@api_router.post("/quotations")
async def create(
    payload: QuotationCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationResponse:
    require_consultant(authorization=authorization, x_user_email=x_user_email)
    return create_quotation(payload)


@api_router.post("/quotation-drafts")
async def create_draft(
    payload: QuotationDraftCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationDraftResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_quotation_draft(payload, current_user)
    except ValueError as exc:
        code = str(exc)
        message_by_code = {
            "INVALID_WORKBENCH_SELECTION": "Selected country, application type and filing route are not allowed",
            "INVALID_WORKBENCH_ROUTE_DETAIL": "Selected route detail is not allowed",
            "INVALID_WORKBENCH_ENTITY_TYPE": "Selected entity type is not allowed",
        }
        raise HTTPException(
            status_code=400,
            detail={"code": code, "message": message_by_code.get(code, "Invalid workbench selection")},
        ) from exc
    except KeyError as exc:
        message = str(exc)
        if "COUNTRY_NOT_FOUND" in message:
            raise HTTPException(
                status_code=404,
                detail={"code": "COUNTRY_NOT_FOUND", "message": "Country not found"},
            ) from exc
        if "CONSULTANT_NOT_FOUND" in message:
            raise HTTPException(
                status_code=404,
                detail={"code": "CONSULTANT_NOT_FOUND", "message": "Consultant not found"},
            ) from exc
        raise


@api_router.get("/quotation-drafts")
async def list_drafts(
    user_email: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationDraftListResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    email = None
    if current_user["role"] == "consultant":
        email = str(current_user["email"])
    elif current_user["role"] == "admin" and user_email:
        email = user_email
    return get_quotation_drafts(email)


@api_router.patch("/quotation-drafts/{draft_id}")
async def patch_draft(
    draft_id: str,
    payload: QuotationDraftUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationDraftResponse:
    require_draft_access(draft_id, authorization=authorization, x_user_email=x_user_email)
    try:
        return update_quotation_draft(draft_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRAFT_NOT_FOUND", "message": "Quotation draft not found"},
        ) from exc


@api_router.delete("/quotation-drafts/{draft_id}/items/{item_id}")
async def delete_draft_item(
    draft_id: str,
    item_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationDraftResponse:
    require_draft_access(draft_id, authorization=authorization, x_user_email=x_user_email)
    try:
        return delete_quotation_draft_item(draft_id, item_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRAFT_ITEM_NOT_FOUND", "message": "Quotation draft item not found"},
        ) from exc


@api_router.get("/quotations")
async def list_quotations(
    user_email: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationListResponse:
    current_user = get_current_user(authorization, x_user_email)
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    if current_user["role"] == "admin":
        email = None
    elif current_user["role"] == "consultant":
        email = str(current_user["email"])
    else:
        raise HTTPException(
            status_code=403,
            detail={"code": "ROLE_FORBIDDEN", "message": "Role access forbidden"},
        )
    if current_user["role"] == "admin" and user_email:
        email = user_email
    return get_quotations(email)


@api_router.post("/quotations/from-drafts")
async def create_from_drafts(
    payload: QuotationFromDraftsCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_quotation_from_drafts(payload, current_user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "DRAFT_FORBIDDEN", "message": "Quotation draft access forbidden"},
        ) from exc
    except ValueError as exc:
        code = str(exc)
        message_by_code = {
            "FORMAL_QUOTE_BLOCKED_OVERDUE_FOLLOWUP": "Formal quote creation blocked by overdue followups",
            "FORMAL_QUOTE_BLOCKED_UNCONVERTED": "Formal quote creation requires approval unlock",
        }
        raise HTTPException(
            status_code=400,
            detail={"code": code, "message": message_by_code.get(code, "Selected draft items cannot be combined")},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRAFT_ITEM_NOT_FOUND", "message": "Quotation draft item not found"},
        ) from exc


@api_router.get("/quotations/{quotation_id}")
async def retrieve_quotation(
    quotation_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationResponse:
    quotation, _ = require_quotation_access(quotation_id, authorization, x_user_email)
    return quotation


@api_router.get("/quotations/{quotation_id}/followups")
async def list_followups(
    quotation_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[FollowupResponse]:
    require_quotation_access(quotation_id, authorization, x_user_email)
    return [FollowupResponse.model_validate(row) for row in mysql.fetch_followups(quotation_id)]


@api_router.post("/quotations/{quotation_id}/followups")
async def create_followup(
    quotation_id: str,
    payload: FollowupCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> FollowupResponse:
    _, current_user = require_quotation_access(quotation_id, authorization, x_user_email)
    followup = create_followup_record(quotation_id, payload, current_user)
    return FollowupResponse.model_validate(followup)


@api_router.patch("/quotations/{quotation_id}/status")
async def patch_status(
    quotation_id: str,
    payload: QuotationStatusUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationResponse:
    try:
        require_quotation_access(quotation_id, authorization, x_user_email)
        return update_quotation_status(quotation_id, payload)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=400,
            detail={"code": code, "message": "Next follow-up date is required before this status"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUOTATION_NOT_FOUND", "message": "Quotation not found"},
        ) from exc


@api_router.get("/quotation-approval-requests")
async def list_approval_requests(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[ApprovalRequestResponse]:
    current_user = get_current_user(authorization, x_user_email)
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    return get_approval_requests(current_user)


@api_router.post("/quotation-approval-requests")
async def request_approval_unlock(
    payload: ApprovalRequestCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> ApprovalRequestResponse:
    current_user = require_quote_user(authorization=authorization, x_user_email=x_user_email)
    if current_user["role"] != "consultant":
        raise HTTPException(
            status_code=403,
            detail={"code": "CONSULTANT_REQUIRED", "message": "Consultant permission required"},
        )
    return create_approval_request(payload, current_user)


@api_router.patch("/quotation-approval-requests/{request_id}")
async def review_approval_unlock(
    request_id: str,
    payload: ApprovalRequestReview,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> ApprovalRequestResponse:
    current_user = require_approval_user(authorization=authorization, x_user_email=x_user_email)
    try:
        return review_approval_request(request_id, payload, current_user)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "APPROVAL_REQUEST_NOT_FOUND", "message": "Approval request not found"},
        ) from exc


@api_router.get("/quotations/{quotation_id}/export")
async def export_quotation(quotation_id: str) -> StreamingResponse:
    try:
        quotation = get_quotation(quotation_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUOTATION_NOT_FOUND", "message": "Quotation not found"},
        ) from exc
    stream = build_quotation_workbook(quotation)
    filename = f"{quotation.quotation_no}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.get("/statistics")
async def statistics(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> StatisticsResponse:
    current_user = get_current_user(authorization, x_user_email)
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Authentication required"},
        )
    if current_user["role"] == "admin":
        return get_statistics(None)
    if current_user["role"] == "consultant":
        return get_statistics(str(current_user["email"]))
    raise HTTPException(
        status_code=403,
        detail={"code": "ROLE_FORBIDDEN", "message": "Role access forbidden"},
    )


@api_router.get("/country-config")
async def retrieve_country_config(
    include_deleted: bool = Query(default=False),
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CountryConfigResponse:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return get_country_config(include_deleted=include_deleted)


@api_router.post("/countries")
async def post_country_config(
    payload: CountryCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> Country:
    current_user = require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_country_config(payload, current_user)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "COUNTRY_EXISTS", "message": "Country already exists"},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "JURISDICTION_REFERENCE_NOT_FOUND", "message": "Jurisdiction reference not found"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": str(exc), "message": "Reference is not available for country master"},
        ) from exc


@api_router.post("/countries/bulk-from-reference")
async def post_countries_bulk_from_reference(
    payload: CountryBulkFromReferenceRequest,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CountryBulkFromReferenceResponse:
    current_user = require_admin(authorization=authorization, x_user_email=x_user_email)
    return create_countries_from_reference_bulk(payload, current_user)


@api_router.patch("/countries/{country_code}")
async def patch_country_config(
    country_code: str,
    payload: CountryUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> Country:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_country_config(country_code, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "COUNTRY_NOT_FOUND", "message": "Country not found"},
        ) from exc


@api_router.delete("/countries/{country_code}")
async def delete_country_config_route(
    country_code: str,
    payload: CountryDeleteRequest | None = None,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    current_user = require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_country_config(country_code, payload.delete_reason if payload else "", current_user)
        return {"deleted": True}
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "COUNTRY_NOT_FOUND", "message": "Country not found"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "COUNTRY_HAS_BUSINESS_REFERENCES", "message": str(exc)},
        ) from exc


@api_router.patch("/countries/{country_code}/restore")
async def restore_country_config_route(
    country_code: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> Country:
    current_user = require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return restore_country_config(country_code, current_user)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "COUNTRY_NOT_FOUND", "message": "Country not found"},
        ) from exc


@api_router.patch("/country-path-rules/{rule_id}")
async def patch_country_path_rule(
    rule_id: str,
    payload: CountryPathRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CountryPathRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_country_path_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "COUNTRY_PATH_RULE_NOT_FOUND", "message": "Country path rule not found"},
        ) from exc


@api_router.post("/country-path-rules")
async def post_country_path_rule(
    payload: CountryPathRuleCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> CountryPathRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_country_path_rule(payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "COUNTRY_PATH_RULE_CONFLICT", "message": "Country path rule conflict"},
        ) from exc


@api_router.delete("/country-path-rules/{rule_id}")
async def remove_country_path_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_country_path_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "COUNTRY_PATH_RULE_NOT_FOUND", "message": "Country path rule not found"},
        ) from exc
    return {"deleted": True}


@api_router.patch("/entity-type-rules/{rule_id}")
async def patch_entity_type_rule(
    rule_id: str,
    payload: EntityTypeRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> EntityTypeRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_entity_type_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "ENTITY_TYPE_RULE_NOT_FOUND", "message": "Entity type rule not found"},
        ) from exc


@api_router.post("/entity-type-rules")
async def post_entity_type_rule(
    payload: EntityTypeRuleCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> EntityTypeRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_entity_type_rule(payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ENTITY_TYPE_RULE_CONFLICT", "message": "Entity type rule conflict"},
        ) from exc


@api_router.delete("/entity-type-rules/{rule_id}")
async def remove_entity_type_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_entity_type_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "ENTITY_TYPE_RULE_NOT_FOUND", "message": "Entity type rule not found"},
        ) from exc
    return {"deleted": True}


@api_router.patch("/language-rules/{rule_id}")
async def patch_language_rule(
    rule_id: str,
    payload: LanguageRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> LanguageRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_language_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "LANGUAGE_RULE_NOT_FOUND", "message": "Language rule not found"},
        ) from exc


@api_router.post("/language-rules")
async def post_language_rule(
    payload: LanguageRuleCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> LanguageRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_language_rule(payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "LANGUAGE_RULE_CONFLICT", "message": "Language rule conflict"},
        ) from exc


@api_router.delete("/language-rules/{rule_id}")
async def remove_language_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_language_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "LANGUAGE_RULE_NOT_FOUND", "message": "Language rule not found"},
        ) from exc
    return {"deleted": True}


@api_router.patch("/fx-tax-rules/{rule_id}")
async def patch_fx_tax_rule(
    rule_id: str,
    payload: FxTaxRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> FxTaxRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_fx_tax_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "FX_TAX_RULE_NOT_FOUND", "message": "FX/tax rule not found"},
        ) from exc


@api_router.post("/fx-tax-rules")
async def post_fx_tax_rule(
    payload: FxTaxRuleCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> FxTaxRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_fx_tax_rule(payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "FX_TAX_RULE_CONFLICT", "message": "FX/tax rule conflict"},
        ) from exc


@api_router.delete("/fx-tax-rules/{rule_id}")
async def remove_fx_tax_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_fx_tax_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "FX_TAX_RULE_NOT_FOUND", "message": "FX/tax rule not found"},
        ) from exc
    return {"deleted": True}


@api_router.patch("/special-rules/{rule_id}")
async def patch_special_rule(
    rule_id: str,
    payload: SpecialRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> SpecialRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_special_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SPECIAL_RULE_NOT_FOUND", "message": "Special rule not found"},
        ) from exc


@api_router.post("/special-rules")
async def post_special_rule(
    payload: SpecialRuleCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> SpecialRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_special_rule(payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "SPECIAL_RULE_CONFLICT", "message": "Special rule conflict"},
        ) from exc


@api_router.delete("/special-rules/{rule_id}")
async def remove_special_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_special_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SPECIAL_RULE_NOT_FOUND", "message": "Special rule not found"},
        ) from exc
    return {"deleted": True}


@api_router.get("/fee-rules")
async def list_fee_rules(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[FeeRule]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return get_fee_rules()


@api_router.post("/fee-rules")
async def post_fee_rule(
    payload: FeeRuleCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> FeeRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return create_fee_rule(payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "FEE_RULE_CONFLICT", "message": "Fee rule conflict"},
        ) from exc


@api_router.patch("/fee-rules/{rule_id}")
async def patch_fee_rule(
    rule_id: str,
    payload: FeeRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> FeeRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_fee_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "FEE_RULE_NOT_FOUND", "message": "Fee rule not found"},
        ) from exc


@api_router.delete("/fee-rules/{rule_id}")
async def remove_fee_rule(
    rule_id: str,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> dict[str, bool]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        delete_fee_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "FEE_RULE_NOT_FOUND", "message": "Fee rule not found"},
        ) from exc
    return {"deleted": True}


@api_router.get("/translation-rules")
async def list_translation_rules(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[TranslationRule]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return get_translation_rules()


@api_router.patch("/translation-rules/{rule_id}")
async def patch_translation_rule(
    rule_id: str,
    payload: TranslationRuleUpdate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> TranslationRule:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    try:
        return update_translation_rule(rule_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TRANSLATION_RULE_NOT_FOUND",
                "message": "Translation rule not found",
            },
        ) from exc
