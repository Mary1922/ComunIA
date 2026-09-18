"""Comprobaciones de la justificación ReAct auditable."""

from app.prompts.examples import FEW_SHOT_EXAMPLES
from app.prompts.triage_prompt import build_system_prompt


def test_system_prompt_documents_auditable_react_structure():
    prompt = build_system_prompt()

    assert "FRAMEWORK REACT AUDITABLE" in prompt
    assert "Observación:" in prompt
    assert "Acción:" in prompt
    assert "Resultado:" in prompt
    assert "deliberación" in prompt
    assert "privada" in prompt


def test_few_shot_examples_use_auditable_react_labels():
    for example in FEW_SHOT_EXAMPLES:
        reasoning = example["output"]["reasoning"]
        assert "Observación:" in reasoning
        assert "Acción:" in reasoning
        assert "Resultado:" in reasoning
