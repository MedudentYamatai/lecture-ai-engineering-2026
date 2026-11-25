# 第6回 解答

## 演習

<!-- [tool call] の行は、表示された行をそのまま貼り付けてください。終わらなかった STEP は、空欄のままでかまいません。 -->

- STEP 1 のツールの名前：glossary_search_glossary
- STEP 2 の [tool call]：`[tool call]   glossary_search_glossary({'query': '3レベル'})`
- STEP 3 の [tool call]：`[tool call]   fetch_fetch({'url': 'https://modelcontextprotocol.io/'})`
- STEP 4 の [tool call]：
  - `[tool call]   aws_aws___search_documentation({'search_phrase': 'Amazon S3 バージョニング', 'topics': ['general']})`
  - `[tool call]   aws_aws___search_documentation({'search_phrase': 'Using versioning in S3 buckets', 'topics': ['general']})`
- 気づき・疑問：
  - STEP 1：第5回までのエージェント（`app.agent`）は `search_materials` など 3 個、MCP のエージェントは `glossary_search_glossary` の 1 個。どちらも「名前・説明文・引数」の同じ形でモデルに渡っている。MCP 側の引数には `"title": "Query"` が付いており、MCP サーバーが型ヒントから JSON Schema を作っていることが分かる。
  - STEP 3：fetch はページ本体より先に `robots.txt` を取得していた。補足にあった「robots.txt で禁止されたページは取得しない」という既定の動作を、ログで確認できた。
  - STEP 4：`aws` を足すとツールが 5 個増えて合計 7 個になった。名前は「サーバー名 `aws` + `_` + ツール名 `aws___search_documentation`」なので `aws_aws___…` と二重になる。1 回目は日本語の検索語で関係の薄い記事が返り、モデルが自分で英語の検索語に変えて再検索していた（モデル応答 3 回、入力 11,106 tokens）。ツールが増えるほど、説明文の分だけ入力トークンも増えると思われる。

## 宿題

<!-- 基礎・実装・発展のどれか1つに取り組めば完了です。 -->

- 取り組んだレベル：基礎 / 実装 / 発展（3 つすべて）

### 基礎

- やったこと：`app/mcp_server.py` の TODO の下に `server.tool()(tools.get_lecture_summary)` の 1 行を書き足した。`git status` で、変更が `app/mcp_server.py` だけであることを確認した（エージェント側の `app/mcp_servers.json` と `app/mcp_agent.py` は変えていない）。
- 結果：
  - `--list-tools` に `[glossary_get_lecture_summary]`（引数 `{"lecture": {"title": "Lecture", "type": "integer"}}`）が増えた。
  - 「第2回では何を学びますか？」の trace：`[tool call]   glossary_get_lecture_summary({'lecture': 2})`。返ってきた第2回の要点（事前学習とファインチューニング、SFT、LoRA/QLoRA、Colab での演習）をもとに回答した。モデル応答 2 回。
  - `uv run pytest -q`：32 passed
- 気づき・疑問：エージェントは起動するたびにサーバーへツール一覧を問い合わせるので、サーバー側に 1 行足すだけでエージェントのコードを変えずに使えるようになった。第3回のように関数をエージェントへ直接登録する方法だと、ツールを増やすたびにエージェント側も変える必要があり、ここが MCP で分ける利点だと実感した。
