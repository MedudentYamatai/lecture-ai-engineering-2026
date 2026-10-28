"""第2回 宿題（発展）: 用語集から SFT 用の Q&A データ（JSONL）を作る。

使い方:
    uv run python scripts/make_sft_dataset.py > glossary_sft.jsonl

できたファイルを Colab にアップロードし、LoRA 学習のデータとして使う。
質問の言い回しを増やす、別名でも質問を作る、検証用に一部を分ける、などを工夫してみよう。

出力は演習と同じ {"answer": 文字列, "needs_review": 真偽値} の JSON 1 行。
用語集に無い語の質問も混ぜ、「確認が必要」と答える例も学習させる。
別名（aliases）での質問は、言い回しへの強さを評価で確かめるため学習には入れない。
"""

import json
import sys
from pathlib import Path

GLOSSARY = Path(__file__).resolve().parent.parent / "data" / "glossary.json"
TEMPLATES = ["「{term}」とは何ですか？", "{term}について簡単に説明してください。"]
SYSTEM = (
    "あなたは AIE2026 講座の用語集の回答係です。用語集に載っている用語は、その定義を答えてください。"
    "必ず JSON 1 行で答えます。形式: {\"answer\": 文字列, \"needs_review\": 真偽値}。"
    "用語集に載っていない用語は answer に『確認が必要』と書き、needs_review を true にします。"
)
# 用語集に無い語（評価で使う語とは重ねない）
UNKNOWN_TERMS = [
    "RAG", "蒸留", "ベクトルデータベース", "プロンプトインジェクション",
    "強化学習", "トランスフォーマー", "埋め込み", "Few-shotプロンプト",
]
UNKNOWN_ANSWER = "この用語は用語集に記載がありません。確認が必要です。"


def record(question: str, answer: str, needs_review: bool) -> dict:
    target = json.dumps({"answer": answer, "needs_review": needs_review}, ensure_ascii=False)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"質問: {question}"},
            {"role": "assistant", "content": target},
        ]
    }


def main() -> None:
    terms = json.loads(GLOSSARY.read_text(encoding="utf-8"))["terms"]
    records = [record(tpl.format(term=t["term"]), t["definition"], False) for t in terms for tpl in TEMPLATES]
    records += [record(tpl.format(term=u), UNKNOWN_ANSWER, True) for u in UNKNOWN_TERMS for tpl in TEMPLATES]
    for r in records:
        sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
