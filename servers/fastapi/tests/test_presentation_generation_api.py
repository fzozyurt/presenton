import asyncio
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v1.ppt.endpoints.presentation import generate_presentation_sync
from models.generate_presentation_request import GeneratePresentationRequest
from models.presentation_and_path import PresentationPathAndEditPath


class FakeAsyncSession:
    async def get(self, *_args, **_kwargs):
        return None

    def add(self, *_args, **_kwargs):
        return None

    def add_all(self, *_args, **_kwargs):
        return None

    async def commit(self):
        return None

    async def execute(self, *_args, **_kwargs):
        class _Empty:
            def scalars(self):
                return self

            def all(self):
                return []

            def __iter__(self):
                return iter([])

        return _Empty()


def _fake_request_http():
    req = Mock()
    req.state.auth_username = None
    req.headers = {}
    return req


class TestPresentationGenerationAPI:
    def test_generate_presentation_export_as_pdf(self):
        request = GeneratePresentationRequest(
            content="Create a presentation about artificial intelligence and machine learning",
            n_slides=5,
            language="English",
            export_as="pdf",
            template="general",
        )
        response_payload = PresentationPathAndEditPath(
            presentation_id=uuid.uuid4(),
            path="/tmp/exports/test.pdf",
            edit_path="/presentation?id=test",
        )

        with (
            patch(
                "api.v1.ppt.endpoints.presentation.generate_presentation_handler",
                new=AsyncMock(return_value=response_payload),
            ) as mock_handler,
            patch(
                "api.v1.ppt.endpoints.presentation._build_export_cookie_header",
                return_value=None,
            ),
        ):
            response = asyncio.run(
                generate_presentation_sync(
                    _fake_request_http(),
                    request=request,
                    sql_session=FakeAsyncSession(),
                )
            )

        assert response == response_payload
        mock_handler.assert_awaited_once()

    def test_generate_presentation_export_as_pptx(self):
        request = GeneratePresentationRequest(
            content="Create a presentation about artificial intelligence and machine learning",
            n_slides=5,
            language="English",
            export_as="pptx",
            template="general",
        )
        response_payload = PresentationPathAndEditPath(
            presentation_id=uuid.uuid4(),
            path="/tmp/exports/test.pptx",
            edit_path="/presentation?id=test",
        )

        with (
            patch(
                "api.v1.ppt.endpoints.presentation.generate_presentation_handler",
                new=AsyncMock(return_value=response_payload),
            ) as mock_handler,
            patch(
                "api.v1.ppt.endpoints.presentation._build_export_cookie_header",
                return_value=None,
            ),
        ):
            response = asyncio.run(
                generate_presentation_sync(
                    _fake_request_http(),
                    request=request,
                    sql_session=FakeAsyncSession(),
                )
            )

        assert response == response_payload
        mock_handler.assert_awaited_once()

    def test_generate_presentation_with_no_content(self):
        with pytest.raises(ValidationError):
            GeneratePresentationRequest.model_validate(
                {
                    "n_slides": 5,
                    "language": "English",
                    "export_as": "pdf",
                    "template": "general",
                }
            )

    def test_generate_presentation_with_n_slides_less_than_one(self):
        request = GeneratePresentationRequest(
            content="Create a presentation about artificial intelligence and machine learning",
            n_slides=0,
            language="English",
            export_as="pdf",
            template="general",
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                generate_presentation_sync(
                    _fake_request_http(),
                    request=request,
                    sql_session=FakeAsyncSession(),
                )
            )

        assert exc.value.status_code == 400
        assert exc.value.detail == "Number of slides must be greater than 0"

    def test_generate_presentation_with_invalid_export_type(self):
        with pytest.raises(ValidationError):
            GeneratePresentationRequest.model_validate(
                {
                    "content": "Create a presentation about artificial intelligence and machine learning",
                    "n_slides": 5,
                    "language": "English",
                    "export_as": "invalid_type",
                    "template": "general",
                }
            )


class TestDeepAgentsValidationBeforeRunner:
    def test_deepagents_sync_still_validates_invalid_request(self):
        """Issue 1: DeepAgents mode must call check_if_api_request_is_valid before runner."""
        request = GeneratePresentationRequest(
            content="",
            n_slides=5,
            language="English",
            export_as="pptx",
            template="general",
        )

        with patch(
            "api.v1.ppt.endpoints.presentation._is_deepagents_mode",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(
                    generate_presentation_sync(
                        _fake_request_http(),
                        request=request,
                        sql_session=FakeAsyncSession(),
                    )
                )

        assert exc.value.status_code == 400
        assert "content" in exc.value.detail or "files" in exc.value.detail

    def test_deepagents_sync_still_validates_n_slides(self):
        """Issue 1: n_slides <= 0 must still be rejected in DeepAgents mode."""
        request = GeneratePresentationRequest(
            content="Test content",
            n_slides=0,
            language="English",
            export_as="pptx",
            template="general",
        )

        with patch(
            "api.v1.ppt.endpoints.presentation._is_deepagents_mode",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(
                    generate_presentation_sync(
                        _fake_request_http(),
                        request=request,
                        sql_session=FakeAsyncSession(),
                    )
                )

        assert exc.value.status_code == 400
        assert "Number of slides" in exc.value.detail

    def test_deepagents_sync_returns_500_on_empty_output_path(self):
        """Issue 3: Sync DeepAgents must not return 200 with empty output path."""
        request = GeneratePresentationRequest(
            content="Test content",
            n_slides=3,
            language="English",
            export_as="pptx",
            template="general",
        )

        mock_result = AsyncMock()
        mock_result.status = "completed"
        mock_result.presentation_path = None
        mock_result.export_path = None
        mock_result.edit_path = None
        mock_result.error = None

        with (
            patch(
                "api.v1.ppt.endpoints.presentation._is_deepagents_mode",
                return_value=True,
            ),
            patch(
                "api.v1.ppt.endpoints.presentation.check_if_api_request_is_valid",
                new=AsyncMock(return_value=(uuid.uuid4(),)),
            ),
            patch(
                "services.deepagents.runner.run_deepagents_presentation_generation",
                new=AsyncMock(return_value=mock_result),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(
                    generate_presentation_sync(
                        _fake_request_http(),
                        request=request,
                        sql_session=FakeAsyncSession(),
                    )
                )

        assert exc.value.status_code == 500
        assert "no output path" in exc.value.detail.lower()

    def test_deepagents_sync_uses_export_path_fallback(self):
        """Issue 3: export_path should be used as fallback if presentation_path is None."""
        request = GeneratePresentationRequest(
            content="Test content",
            n_slides=3,
            language="English",
            export_as="pptx",
            template="general",
        )

        mock_result = AsyncMock()
        mock_result.status = "completed"
        mock_result.presentation_path = None
        mock_result.export_path = "/tmp/exports/deck.pptx"
        mock_result.edit_path = "/edit/123"
        mock_result.error = None

        pres_id = uuid.uuid4()

        with (
            patch(
                "api.v1.ppt.endpoints.presentation._is_deepagents_mode",
                return_value=True,
            ),
            patch(
                "api.v1.ppt.endpoints.presentation.check_if_api_request_is_valid",
                new=AsyncMock(return_value=(pres_id,)),
            ),
            patch(
                "services.deepagents.runner.run_deepagents_presentation_generation",
                new=AsyncMock(return_value=mock_result),
            ),
        ):
            response = asyncio.run(
                generate_presentation_sync(
                    _fake_request_http(),
                    request=request,
                    sql_session=FakeAsyncSession(),
                )
            )

        assert response.path == "/tmp/exports/deck.pptx"
        assert response.presentation_id == pres_id
