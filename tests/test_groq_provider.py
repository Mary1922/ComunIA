"""Tests del adaptador Groq sin realizar llamadas reales a Internet."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.llm.groq_provider import GroqProvider


@pytest.mark.asyncio
async def test_groq_provider_parses_structured_response(monkeypatch):
    settings = Settings(
        groq_api_key="test-key",
        groq_model="qwen/qwen3.8-27b",
        max_retries=1,
    )
    provider = GroqProvider(settings)

    async def fake_post(self, url, headers=None, json=None):
        assert url.endswith("/chat/completions")
        assert json["response_format"]["type"] == "json_schema"
        assert json["response_format"]["json_schema"]["strict"] is True

        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "model": "qwen/qwen3.8-27b",
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "category": "contabilidad",
                                    "priority": "low",
                                    "summary": "Solicitud de copia del último recibo comunitario",
                                    "department": "gestion_comunidad",
                                    "reasoning": "Es una gestión documental sin urgencia.",
                                }
                            )
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 40,
                },
            },
        )

    # Evita sombrear el módulo json con el argumento json de fake_post.
    json_module = json
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await provider.generate(
        system_prompt="system",
        user_prompt="user",
        json_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    )

    assert result.model == "qwen/qwen3.8-27b"
    assert result.input_tokens == 100
    assert result.output_tokens == 40
    assert '"priority": "low"' in result.content
