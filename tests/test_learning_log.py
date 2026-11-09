"""第3回 宿題（実装）: save_learning_log と承認フローのテスト（LLMもAPIキーも使わない）。"""

from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolDenied
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent


def _run_until_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = agent.run_sync("今日の学習を記録して")
    return model, result


def test_save_waits_for_approval(monkeypatch, tmp_path):
    _, result = _run_until_approval(monkeypatch, tmp_path)
    assert isinstance(result.output, DeferredToolRequests)
    assert [c.tool_name for c in result.output.approvals] == ["save_learning_log"]
    assert not (tmp_path / "learning_log").exists()  # 承認前は何も書き込まない


def test_save_runs_after_approval(monkeypatch, tmp_path):
    model, result = _run_until_approval(monkeypatch, tmp_path)
    call = result.output.approvals[0]
    with agent.override(model=model):
        agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=DeferredToolResults(approvals={call.tool_call_id: True}),
        )
    assert len(list((tmp_path / "learning_log").glob("*.md"))) == 1


def test_save_is_skipped_when_denied(monkeypatch, tmp_path):
    model, result = _run_until_approval(monkeypatch, tmp_path)
    call = result.output.approvals[0]
    with agent.override(model=model):
        agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=DeferredToolResults(approvals={call.tool_call_id: ToolDenied("いいえ")}),
        )
    assert not (tmp_path / "learning_log").exists()


def test_save_does_not_overwrite(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    tools.save_learning_log("a", "1つ目")
    tools.save_learning_log("b", "2つ目")
    assert len(list(tmp_path.glob("*.md"))) == 2
