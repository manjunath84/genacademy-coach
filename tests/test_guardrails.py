from pathlib import Path


def test_coach_code_does_not_import_langgraph_directly():
    src = Path("src/genacademy_coach")
    offenders = []
    for path in src.rglob("*.py"):
        text = path.read_text()
        if "import langgraph" in text or "from langgraph" in text:
            offenders.append(str(path))
    assert offenders == []
