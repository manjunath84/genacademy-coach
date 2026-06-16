from pathlib import Path


def test_coach_code_does_not_import_langgraph_directly():
    src = Path("src/genacademy_coach")
    offenders = []
    for path in src.rglob("*.py"):
        text = path.read_text()
        if "import langgraph" in text or "from langgraph" in text:
            offenders.append(str(path))
    assert offenders == []


def test_teach_agent_uses_create_agent_boundary():
    text = Path("src/genacademy_coach/teach_agent.py").read_text(encoding="utf-8")

    assert "from langchain.agents import create_agent" in text
    assert "create_agent(" in text
