"""第3回 宿題（発展 a）: 演習のエージェントを Google ADK で組み立て直したもの。

指示（INSTRUCTIONS）とツール（app/tools.py の関数）は Pydantic AI 版と同じものを使い、
エージェントを組み立てる部分だけを ADK で書く。

    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

root_agent = Agent(
    model=MODEL,  # 既定は gemini-3.5-flash-lite。AIE_MODEL で切り替えられるのは演習版と同じ
    name="glossary_agent",
    description="AIE2026 の用語集と各回の要点を使って質問に答える学習支援エージェント",
    instruction=INSTRUCTIONS,
    # Pydantic AI の agent.tool_plain(...) に当たる。関数を渡すと、名前・docstring・型ヒントからツールの説明が作られる
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)
