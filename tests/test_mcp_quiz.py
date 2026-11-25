"""第6回 宿題（実装）: make_quiz を MCP で公開し、範囲外の回には案内のメッセージを返す。"""

import json

from pydantic_ai.models.test import TestModel

from app import tools
from app.mcp_agent import MCP_CONFIG, build_mcp_agent


def _glossary_only_config(tmp_path):
    config = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"mcpServers": {"glossary": config["mcpServers"]["glossary"]}}), encoding="utf-8")
    return path


def test_mcp_server_exposes_make_quiz(tmp_path):
    model = TestModel(call_tools=[])
    build_mcp_agent(_glossary_only_config(tmp_path)).run_sync("ツール一覧", model=model)
    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert {"glossary_get_lecture_summary", "glossary_make_quiz"} <= offered


def test_make_quiz_out_of_range_returns_guidance():
    for lecture in (99, 5, 0, -1):  # 存在しない回・用語のない回・1 未満
        message = tools.make_quiz(lecture)
        assert "問題を作れる回: 第1回" in message  # 例外にせず、選べる回を文章で返す


def test_make_quiz_in_range_returns_question():
    quiz = json.loads(tools.make_quiz(2))
    assert quiz["lecture"] == 2 and quiz["question"] and quiz["answer"]
