"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --interactive  # 会話履歴を保って続けて質問する

ツールを持たない「素の」呼び出し。
対話モードでは同じ Chat を使い続け、会話履歴を次の質問にも渡す。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
from time import perf_counter

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def _print_metrics(response, elapsed_seconds: float) -> None:
    print(f"[latency] {elapsed_seconds:.2f}s")
    usage = response.usage_metadata
    if usage is None:
        print("[usage] token counts unavailable")
    else:
        print(
            f"[usage] input_tokens={usage.prompt_token_count} "
            f"output_tokens={usage.candidates_token_count}"
        )


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    started_at = perf_counter()
    response = client.models.generate_content(model=MODEL, contents=question)
    _print_metrics(response, perf_counter() - started_at)
    return response.text


def _send_chat_message(chat, question: str) -> str:
    started_at = perf_counter()
    response = chat.send_message(question)
    _print_metrics(response, perf_counter() - started_at)
    return response.text


def run_interactive(initial_question: str | None = None) -> None:
    client = genai.Client(api_key=get_api_key())
    chat = client.chats.create(model=MODEL)
    print("対話モードです。終了するには exit または Ctrl+D を入力してください。")

    question = initial_question
    while True:
        if question is None:
            try:
                question = input("あなた> ").strip()
            except EOFError:
                print()
                break
        if question.lower() in {"exit", "quit"} or question == "終了":
            break
        if question:
            print(f"[質問] {question}")
            print(_send_chat_message(chat, question))
        question = None


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--interactive", "-i", action="store_true", help="会話履歴を保って続けて質問する")
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        if args.interactive:
            run_interactive(args.question)
        else:
            question = args.question or DEFAULT_QUESTION
            print(f"[質問] {question}\n")
            print(ask(question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
