from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, JSON, String, Text
from sqlmodel import Field, SQLModel


class IntegrationDataSourceModel(SQLModel, table=True):
    __tablename__ = "integration_data_sources"

    id: str = Field(default_factory=lambda: f"ds-{uuid.uuid4().hex[:12]}", primary_key=True)
    type: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    name: str = Field(sa_column=Column(String(255), nullable=False))
    credential_ref: str | None = Field(default=None, sa_column=Column(String(255)))
    base_config: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationBindingModel(SQLModel, table=True):
    __tablename__ = "integration_bindings"

    id: str = Field(default_factory=lambda: f"bnd-{uuid.uuid4().hex[:12]}", primary_key=True)
    presentation_id: str = Field(sa_column=Column(String(36), nullable=False, index=True))
    datasource_id: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    alias: str | None = Field(default=None, sa_column=Column(String(255)))
    binding_config: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationCredentialModel(SQLModel, table=True):
    __tablename__ = "integration_credentials"

    id: str = Field(default_factory=lambda: f"cred-{uuid.uuid4().hex[:12]}", primary_key=True)
    module: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    type: str = Field(sa_column=Column(String(64), nullable=False))
    status: str = Field(default="active", sa_column=Column(String(32)))
    label: str | None = Field(default=None, sa_column=Column(String(255)))
    key_id: str = Field(sa_column=Column(String(32), nullable=False))
    fingerprint: str = Field(sa_column=Column(String(32)))
    encrypted_secret: bytes = Field(sa_column=Column(String(4096)))
    expires_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IntegrationReportRunModel(SQLModel, table=True):
    __tablename__ = "integration_report_runs"

    id: str = Field(default_factory=lambda: f"run-{uuid.uuid4().hex[:12]}", primary_key=True)
    presentation_id: str = Field(sa_column=Column(String(36), nullable=False, index=True))
    binding_id: str | None = Field(default=None, sa_column=Column(String(64)))
    status: str = Field(default="pending", sa_column=Column(String(32)))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    result_data: dict | None = Field(default=None, sa_column=Column(JSON))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
