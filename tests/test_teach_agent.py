from genacademy_coach.teach_agent import SYSTEM_PROMPT, build_coach_agent, build_langchain_model


class FakeRagSettings:
    gen_model = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    gen_api_key = "secret"
    gen_base_url = "https://api.tokenfactory.nebius.com/v1/"


class FakeFoundation:
    rag_settings = FakeRagSettings()


def test_system_prompt_requires_grounding_and_trace_action():
    assert "retrieved citation" in SYSTEM_PROMPT
    assert "next_action" in SYSTEM_PROMPT
    assert "do not answer from model priors" in SYSTEM_PROMPT.lower()
    assert "evidence score" in SYSTEM_PROMPT.lower()
    assert "do not return confidence" in SYSTEM_PROMPT.lower()
    assert "correct=false" in SYSTEM_PROMPT
    assert "[citation_id]" in SYSTEM_PROMPT


def test_build_langchain_model_uses_week2_generation_settings():
    model = build_langchain_model(FakeFoundation())

    assert model.model_name == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    assert str(model.openai_api_base).rstrip("/") == "https://api.tokenfactory.nebius.com/v1"


def test_build_langchain_model_falls_back_when_week2_model_is_empty():
    class EmptyModelRagSettings(FakeRagSettings):
        gen_model = ""

    class EmptyModelFoundation:
        rag_settings = EmptyModelRagSettings()

    model = build_langchain_model(EmptyModelFoundation())

    assert model.model_name == "Qwen/Qwen3-30B-A3B-Instruct-2507"


def test_build_coach_agent_bounds_model_and_tool_calls(monkeypatch):
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("genacademy_coach.teach_agent.create_agent", fake_create_agent)

    build_coach_agent(object(), model=object())

    middleware_names = [type(item).__name__ for item in captured["middleware"]]
    assert middleware_names == ["ModelCallLimitMiddleware", "ToolCallLimitMiddleware"]
