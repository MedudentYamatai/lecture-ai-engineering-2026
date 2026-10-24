from types import SimpleNamespace
from unittest.mock import Mock

from app import ask as ask_module


def test_ask_prints_latency_and_token_counts(monkeypatch, capsys):
    response = SimpleNamespace(
        text="answer",
        usage_metadata=SimpleNamespace(prompt_token_count=12, candidates_token_count=7),
    )
    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=Mock(return_value=response))
    )
    monkeypatch.setattr(ask_module.genai, "Client", Mock(return_value=client))
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module, "perf_counter", Mock(side_effect=[1.0, 2.234]))

    assert ask_module.ask("question") == "answer"

    output = capsys.readouterr().out
    assert "[latency] 1.23s" in output
    assert "input_tokens=12 output_tokens=7" in output


def test_interactive_chat_keeps_conversation_for_follow_up_questions(monkeypatch):
    chat = Mock()
    chat.send_message.side_effect = [
        SimpleNamespace(text="first answer", usage_metadata=None),
        SimpleNamespace(text="follow-up answer", usage_metadata=None),
    ]
    client = SimpleNamespace(chats=SimpleNamespace(create=Mock(return_value=chat)))
    monkeypatch.setattr(ask_module.genai, "Client", Mock(return_value=client))
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    questions = iter(["最初の質問", "続きの質問", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(questions))

    ask_module.run_interactive()

    client.chats.create.assert_called_once_with(model=ask_module.MODEL)
    assert [call.args[0] for call in chat.send_message.call_args_list] == [
        "最初の質問",
        "続きの質問",
    ]