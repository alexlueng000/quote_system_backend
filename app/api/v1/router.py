from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pymysql.err import IntegrityError

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db import mysql
from app.schemas.quotation import (
    BootstrapResponse,
    FeeRule,
    FeeRuleUpdate,
    FollowupCreate,
    FollowupResponse,
    GeneratedQuotation,
    LoginRequest,
    LoginResponse,
    QuotationCreate,
    QuotationGenerateRequest,
    QuotationListResponse,
    QuotationResponse,
    QuotationStatusUpdate,
    StatisticsResponse,
    TranslationRule,
    TranslationRuleUpdate,
    User,
    UserCreate,
    UserPasswordUpdate,
    UserUpdate,
)
from app.services.quotation_service import (
    create_quotation,
    generate_quotation,
    get_bootstrap,
    get_fee_rules,
    get_quotation,
    get_quotations,
    get_statistics,
    get_translation_rules,
    update_quotation_status,
    update_fee_rule,
    update_translation_rule,
)
from app.services.export_service import build_quotation_workbook

api_router = APIRouter()


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
) -> None:
    user = get_current_user(authorization, x_user_email)
    if user is None or user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_REQUIRED", "message": "Admin permission required"},
        )


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


@api_router.post("/quotations")
async def create(
    payload: QuotationCreate,
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> QuotationResponse:
    require_consultant(authorization=authorization, x_user_email=x_user_email)
    return create_quotation(payload)


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
    followup = mysql.insert_followup(
        {
            "quotation_id": quotation_id,
            "user_id": current_user["id"],
            "method": payload.method,
            "content": payload.content,
            "next_followup_date": payload.next_followup_date,
        }
    )
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
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUOTATION_NOT_FOUND", "message": "Quotation not found"},
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


@api_router.get("/fee-rules")
async def list_fee_rules(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> list[FeeRule]:
    require_admin(authorization=authorization, x_user_email=x_user_email)
    return get_fee_rules()


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
