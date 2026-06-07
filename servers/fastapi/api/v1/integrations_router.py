from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

from models.sql.integration_credential import (
    IntegrationBindingModel,
    IntegrationCredentialModel,
    IntegrationDataSourceModel,
    IntegrationReportRunModel,
)
from identity.provider import is_oidc_enabled
from identity.tokens import get_oidc_session_token_from_request, validate_oidc_session_token
from services.database import get_async_session
from services.integrations.credentials.resolver import CredentialEncryptionService

INTEGRATIONS_ROUTER = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


def _get_current_user_id(request: Request) -> str | None:
    if not is_oidc_enabled():
        return None
    token = get_oidc_session_token_from_request(request)
    payload = validate_oidc_session_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return payload["uid"]


def _require_owner(owner_field: str | None, user_id: str | None):
    if user_id and owner_field and owner_field != user_id:
        raise HTTPException(status_code=403, detail="Not your resource")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DataSourceCreate(BaseModel):
    type: str = Field(..., max_length=64, examples=["rest", "grafana", "prometheus"])
    name: str = Field(..., max_length=255)
    credential_ref: str | None = Field(None, max_length=255)
    base_config: dict | None = None


class DataSourceUpdate(BaseModel):
    type: str | None = Field(None, max_length=64)
    name: str | None = Field(None, max_length=255)
    credential_ref: str | None = Field(None, max_length=255)
    base_config: dict | None = None


class DataSourceResponse(BaseModel):
    id: str
    type: str
    name: str
    credential_ref: str | None
    base_config: dict | None
    created_at: str
    updated_at: str


class CredentialCreate(BaseModel):
    module: str = Field(..., max_length=64, examples=["rest", "grafana"])
    type: str = Field(..., max_length=64, examples=["api_key", "bearer", "basic"])
    label: str | None = Field(None, max_length=255)
    secret: dict[str, object] = Field(..., examples=[{"api_key": "sk-xxx"}])

    class Config:
        json_schema_extra = {
            "example": {
                "module": "rest",
                "type": "bearer",
                "label": "Production API Token",
                "secret": {"token": "eyJhbGciOiJIUzI1NiIs..."},
            }
        }


class CredentialResponse(BaseModel):
    id: str
    module: str
    type: str
    status: str
    label: str | None
    fingerprint: str
    expires_at: str | None
    created_at: str
    updated_at: str


class BindingCreate(BaseModel):
    presentation_id: str = Field(..., max_length=36)
    datasource_id: str = Field(..., max_length=64)
    alias: str | None = Field(None, max_length=255)
    binding_config: dict | None = None


class BindingResponse(BaseModel):
    id: str
    presentation_id: str
    datasource_id: str
    alias: str | None
    binding_config: dict | None
    created_at: str


class ReportRunResponse(BaseModel):
    id: str
    presentation_id: str
    binding_id: str | None
    status: str
    error_message: str | None
    result_data: dict | None
    started_at: str | None
    completed_at: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ds_to_response(ds: IntegrationDataSourceModel) -> DataSourceResponse:
    return DataSourceResponse(
        id=ds.id,
        type=ds.type,
        name=ds.name,
        credential_ref=ds.credential_ref,
        base_config=ds.base_config,
        created_at=ds.created_at.isoformat(),
        updated_at=ds.updated_at.isoformat(),
    )


def _cred_to_response(cred: IntegrationCredentialModel) -> CredentialResponse:
    return CredentialResponse(
        id=cred.id,
        module=cred.module,
        type=cred.type,
        status=cred.status,
        label=cred.label,
        fingerprint=cred.fingerprint,
        expires_at=cred.expires_at.isoformat() if cred.expires_at else None,
        created_at=cred.created_at.isoformat(),
        updated_at=cred.updated_at.isoformat(),
    )


def _bnd_to_response(bnd: IntegrationBindingModel) -> BindingResponse:
    return BindingResponse(
        id=bnd.id,
        presentation_id=bnd.presentation_id,
        datasource_id=bnd.datasource_id,
        alias=bnd.alias,
        binding_config=bnd.binding_config,
        created_at=bnd.created_at.isoformat(),
    )


def _run_to_response(run: IntegrationReportRunModel) -> ReportRunResponse:
    return ReportRunResponse(
        id=run.id,
        presentation_id=run.presentation_id,
        binding_id=run.binding_id,
        status=run.status,
        error_message=run.error_message,
        result_data=run.result_data,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        created_at=run.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------

@INTEGRATIONS_ROUTER.get("/data-sources", response_model=list[DataSourceResponse])
async def list_data_sources(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    user_id = _get_current_user_id(request)
    stmt = select(IntegrationDataSourceModel).order_by(IntegrationDataSourceModel.created_at.desc())
    if user_id:
        stmt = stmt.where((IntegrationDataSourceModel.created_by == user_id) | (IntegrationDataSourceModel.created_by.is_(None)))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_ds_to_response(r) for r in rows]


@INTEGRATIONS_ROUTER.get("/data-sources/{ds_id}", response_model=DataSourceResponse)
async def get_data_source(
    ds_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    ds = await session.get(IntegrationDataSourceModel, ds_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return _ds_to_response(ds)


@INTEGRATIONS_ROUTER.post("/data-sources", response_model=DataSourceResponse, status_code=201)
async def create_data_source(
    request: Request,
    body: DataSourceCreate,
    session: AsyncSession = Depends(get_async_session),
):
    ds = IntegrationDataSourceModel(
        id=f"ds-{uuid.uuid4().hex[:12]}",
        type=body.type,
        name=body.name,
        credential_ref=body.credential_ref,
        base_config=body.base_config,
        created_by=_get_current_user_id(request),
    )
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return _ds_to_response(ds)


@INTEGRATIONS_ROUTER.put("/data-sources/{ds_id}", response_model=DataSourceResponse)
async def update_data_source(
    request: Request,
    ds_id: str,
    body: DataSourceUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    ds = await session.get(IntegrationDataSourceModel, ds_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    _require_owner(ds.created_by, _get_current_user_id(request))

    if body.type is not None:
        ds.type = body.type
    if body.name is not None:
        ds.name = body.name
    if body.credential_ref is not None:
        ds.credential_ref = body.credential_ref
    if body.base_config is not None:
        ds.base_config = body.base_config

    ds.updated_at = datetime.now(UTC)
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return _ds_to_response(ds)


@INTEGRATIONS_ROUTER.delete("/data-sources/{ds_id}", status_code=204)
async def delete_data_source(
    request: Request,
    ds_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    ds = await session.get(IntegrationDataSourceModel, ds_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    _require_owner(ds.created_by, _get_current_user_id(request))
    await session.delete(ds)
    await session.commit()


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

@INTEGRATIONS_ROUTER.get("/credentials", response_model=list[CredentialResponse])
async def list_credentials(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    user_id = _get_current_user_id(request)
    stmt = select(IntegrationCredentialModel).order_by(IntegrationCredentialModel.created_at.desc())
    if user_id:
        stmt = stmt.where((IntegrationCredentialModel.created_by == user_id) | (IntegrationCredentialModel.created_by.is_(None)))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_cred_to_response(r) for r in rows]


@INTEGRATIONS_ROUTER.post("/credentials", response_model=CredentialResponse, status_code=201)
async def create_credential(
    request: Request,
    body: CredentialCreate,
    session: AsyncSession = Depends(get_async_session),
):
    encryption = CredentialEncryptionService()
    key_id, fingerprint, encrypted_blob = encryption.encrypt(body.secret)

    cred = IntegrationCredentialModel(
        id=f"cred-{uuid.uuid4().hex[:12]}",
        module=body.module,
        type=body.type,
        status="active",
        label=body.label,
        key_id=key_id,
        fingerprint=fingerprint,
        encrypted_secret=encrypted_blob,
        created_by=_get_current_user_id(request),
    )
    session.add(cred)
    await session.commit()
    await session.refresh(cred)
    return _cred_to_response(cred)


@INTEGRATIONS_ROUTER.delete("/credentials/{cred_id}", status_code=204)
async def delete_credential(
    request: Request,
    cred_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    cred = await session.get(IntegrationCredentialModel, cred_id)
    if cred is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    _require_owner(cred.created_by, _get_current_user_id(request))
    await session.delete(cred)
    await session.commit()


# ---------------------------------------------------------------------------
# Bindings
# ---------------------------------------------------------------------------

@INTEGRATIONS_ROUTER.get("/bindings", response_model=list[BindingResponse])
async def list_bindings(
    presentation_id: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(IntegrationBindingModel).order_by(IntegrationBindingModel.created_at.desc())
    if presentation_id:
        stmt = stmt.where(IntegrationBindingModel.presentation_id == presentation_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_bnd_to_response(r) for r in rows]


@INTEGRATIONS_ROUTER.post("/bindings", response_model=BindingResponse, status_code=201)
async def create_binding(
    body: BindingCreate,
    session: AsyncSession = Depends(get_async_session),
):
    binding = IntegrationBindingModel(
        id=f"bnd-{uuid.uuid4().hex[:12]}",
        presentation_id=body.presentation_id,
        datasource_id=body.datasource_id,
        alias=body.alias,
        binding_config=body.binding_config,
    )
    session.add(binding)
    await session.commit()
    await session.refresh(binding)
    return _bnd_to_response(binding)


@INTEGRATIONS_ROUTER.delete("/bindings/{bnd_id}", status_code=204)
async def delete_binding(
    bnd_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    binding = await session.get(IntegrationBindingModel, bnd_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="Binding not found")
    await session.delete(binding)
    await session.commit()


# ---------------------------------------------------------------------------
# Report Runs
# ---------------------------------------------------------------------------

@INTEGRATIONS_ROUTER.get("/report-runs", response_model=list[ReportRunResponse])
async def list_report_runs(
    presentation_id: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(IntegrationReportRunModel).order_by(IntegrationReportRunModel.created_at.desc()).limit(limit)
    if presentation_id:
        stmt = stmt.where(IntegrationReportRunModel.presentation_id == presentation_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_run_to_response(r) for r in rows]
