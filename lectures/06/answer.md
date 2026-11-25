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

### 実装

- やったこと：
  - 第3回で作った `make_quiz` を、`app/mcp_server.py` に `server.tool()(tools.make_quiz)` を足して公開した。
  - `app/tools.py` の `make_quiz` で、範囲外の引数のときのメッセージを整えた。1 未満の回（0 や -1）は「回は1始まりの整数」と伝え、用語のない回（99、用語集にない 5 など）は理由と「問題を作れる回: 第1回、第2回、第3回、第4回、第6回」を `return` で返す。
  - `tests/test_mcp_quiz.py` を追加した。MCP 経由で `glossary_make_quiz` が公開されていること、範囲外で案内のメッセージが返ること、正常な回で問題が返ることを確かめる（API キー不要）。
  - 比べるために、一時的に `raise ValueError(同じ文言)` と `raise ToolError(同じ文言)` に変えて試し、最後は `return` 版に戻した。
- 結果（「第99回のクイズを作って」）：

  | 返し方 | trace に出た行 | モデルに渡った内容 | 回答 |
  |---|---|---|---|
  | `return`（採用） | `[tool return] glossary_make_quiz -> 第99回の用語は用語集にないため、問題を作れません。問題を作れる回: 第1回、第2回、第3回、第4回、第6回。…` | 自分で書いた文言そのまま | 作れる回（第1〜4回・第6回）を箇条書きで示し、どれにするか聞き返した |
  | `raise ValueError` | `[tool error]  glossary_make_quiz -> Error executing tool make_quiz` | **「Error executing tool make_quiz」だけ**（自分で書いた文言は届かない） | 「第1回〜各回の範囲」のようにあいまいで、作れる回を言えなかった |
  | `raise ToolError`（MCP SDK の例外） | `[tool error]  glossary_make_quiz -> Error executing tool make_quiz: 第99回の用語は…問題を作れる回: 第1回、…` | 前置き + 自分で書いた文言 | `return` と同じく、作れる回を示して聞き返した |

  - 正常な回（「第2回のクイズを作って」）：`[tool call]   glossary_make_quiz({'lecture': 2})` が呼ばれ、「量子化」の問題を答えを伏せて出題した。
  - `uv run pytest -q`：35 passed
- 気づき・疑問：
  - 例外の種類によって、モデルに届く内容が変わった。MCP の Python SDK（`mcp/server/mcpserver/tools/base.py`）を読むと、`ToolError` は「ツールがわざと出したエラー」としてメッセージをモデルに返す。一方、`ValueError` などそれ以外の例外は「クラッシュ」として扱われ、メッセージはサーバーのログにだけ残り、モデルには定型文しか返さない（内部の情報を外に出さないため）。利用者に伝えたい範囲外の案内は、`return`（または `ToolError`）で返す必要がある。
  - `raise ValueError` 版では、「第99回のクイズを作って」と聞いても、2 回続けてモデルがツールを呼ばずに「第99回はありません」と答えた（モデル応答 1 回）。ツールを呼ぶかどうかはモデルが毎回決めるので、範囲外のテストでは「make_quiz ツールで」と明示する必要があった。
  - `return` で返すと trace の行は `[tool return]` になり、エラーかどうかの区別は文章でしか分からない。ログで失敗を数えたいなら `ToolError`（`is_error` が付く）のほうがよいかもしれない。どちらを標準にするのがよいかは疑問として残った。
