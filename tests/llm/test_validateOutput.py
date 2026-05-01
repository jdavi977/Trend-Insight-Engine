import json

from app.llm.validateOutput import validateOutput
from app.schemas.llm_insights import LLMExtraction


def _payload(problems):
    return json.dumps({"source": "youtube", "title": "Vid", "problems": problems})


def test_validateOutput_returns_LLMExtraction_for_well_formed_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw = _payload([
        {
            "problem": "battery drains fast",
            "type": "complaint",
            "total_likes": 42,
            "severity": 4,
            "frequency": 3,
        },
    ])

    result = validateOutput(raw)

    assert isinstance(result, LLMExtraction)
    assert len(result.problems) == 1
    assert result.problems[0]["problem"] == "battery drains fast"
    assert result.problems[0]["severity"] == 4


def test_validateOutput_drops_malformed_problem_items_and_keeps_valid_ones(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw = _payload([
        {
            "problem": "good problem here",
            "type": "complaint",
            "total_likes": 10,
            "severity": 3,
            "frequency": 2,
        },
        {
            "problem": "bad",
            "type": "complaint",
            "total_likes": 1,
            "severity": 9,
            "frequency": 1,
        },
    ])

    result = validateOutput(raw)

    assert isinstance(result, LLMExtraction)
    assert len(result.problems) == 1
    assert result.problems[0]["problem"] == "good problem here"
    assert (tmp_path / "data" / "invalid_data").exists()


def test_validateOutput_returns_raw_dict_when_problems_list_is_empty():
    raw = json.dumps({"source": "youtube", "title": "Vid", "problems": []})
    result = validateOutput(raw)
    assert result == {"source": "youtube", "title": "Vid", "problems": []}
