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
  - 全体：演習の時点で、ツールはエージェントではなく MCP サーバー（`app/mcp_server.py`）の側にある。第3回はツールの関数をエージェントに直接登録していたが、第6回はツールを別のプログラム（サーバー）に分けて、エージェントがそこに接続して使う形になっている。分けても、モデルから見た使い方は変わらなかった。
  - 自作（`command: uv`）・公開（`command: uvx`）・外部（`url`）の 3 種類とも、設定ファイルに数行書くだけでつながった。エージェントのコードは一度も変えていない。
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
- 気づき・疑問：
  - ツールの置き場所は演習と同じ MCP サーバーで、そこにツールを 1 つ増やしただけ。エージェントは起動するたびにサーバーへ「今どんなツールがある？」と問い合わせるので、サーバー側に 1 行足すだけで、エージェントを変えずに新しいツールが使えた。
  - 第3回のようにエージェントへ直接登録する方法では、ツールを増やすたびにエージェント側も変える必要がある。ツールを持つ側と使う側を分けておくと、ツールの追加がサーバーの中だけで済む。ここが MCP に分ける利点だと実感した。

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
  - 3 つのうちダメだったのは `raise ValueError` だけで、`return` と `ToolError` はどちらもメッセージがモデルに届いた。MCP の Python SDK（`mcp/server/mcpserver/tools/base.py`）を読むと理由が分かった。`ValueError` のような普通の例外は「プログラムが壊れた（クラッシュ）」とみなされ、内部の情報が外に出ないよう、メッセージはサーバーのログにだけ残る。モデルには定型文しか返らない。`ToolError` は「ツールがわざと出したエラー」とみなされ、メッセージがそのまま伝わる。
  - `return` と `ToolError` の違いは、「正常な結果」として返すか、「失敗」として返すか。`return` は `[tool return]` として普通の結果になる。`ToolError` は `[tool error]` として失敗の印が付き、モデルには「呼び直す」扱いで渡り、サーバーのログにも失敗として残る。
  - 今回は `return` を選んだ。理由は 2 つ。「第99回は作れません。作れるのは第1〜4回・第6回です」は、壊れたのではなく想定内の正しい答えであること。また、`tools.py` は MCP を使わない第5回までのエージェント（`app/agent.py`）からも呼ばれるので、MCP 専用の `ToolError` を入れると MCP に依存してしまうこと。使い分けとしては、「想定内の『できません』は `return`、外部 API が落ちていたなど本当の失敗で記録したり呼び直してほしいときは `ToolError`、普通の例外は使わない」がよいと考えた。
  - `raise ValueError` 版では、「第99回のクイズを作って」と聞いても、2 回続けてモデルがツールを呼ばずに「第99回はありません」と答えた（モデル応答 1 回）。ツールを呼ぶかどうかはモデルが毎回決めるので、範囲外のテストでは「make_quiz ツールで」と明示する必要があった。
  - 疑問：`return` で返すと、ログの上では成功と区別がつかない。運用で「できませんでした」の回数を数えたい場合は、返す文章とは別に、サーバー側で記録を残す工夫が必要になりそう。

### 発展

- やったこと：普段使っている **Claude Code**（v2.1.332）の MCP サーバーの設定方法を公式ドキュメントで調べ、演習の `app/mcp_servers.json` と比べた。あわせて、`claude mcp --help` と、`--mcp-config` で演習の設定ファイルをそのまま読ませる方法で、手元でも確かめた。
  - 調べた日付：2026-11-25
  - 参照した公式ドキュメント：https://code.claude.com/docs/en/mcp
- 結果：

  | 調べること | Claude Code | 演習の `app/mcp_servers.json` |
  |---|---|---|
  | 設定を書く場所 | ① コマンドで登録：`claude mcp add` / `claude mcp add-json`（確認は `claude mcp list`、`/mcp`）<br>② ファイル：プロジェクト共有用はリポジトリ直下の `.mcp.json`。自分だけの設定（local / user）は `~/.claude.json` に保存される | `app/` の中の専用ファイル 1 つ。手で編集する |
  | コマンドで起動する書き方 | `claude mcp add glossary -- uv run python -m app.mcp_server`（`--` のあとが起動コマンド）。JSON では `{"type": "stdio", "command": "uv", "args": [...], "env": {...}}` | `{"command": "uv", "args": [...]}`（`type` なし） |
  | URL で接続する書き方 | `claude mcp add --transport http aws https://knowledge-mcp.global.api.aws`。JSON では `{"type": "http", "url": "…"}`。認証用のヘッダーは `--header`、OAuth は `/mcp` から。SSE は非推奨 | `{"url": "…"}`（`type` なし） |
  | 有効になる範囲 | `--scope` で 3 つから選ぶ。`local`（既定。自分だけ・このプロジェクトだけ）、`project`（`.mcp.json` に書かれ、Git で共有される。使う前に承認を求められる）、`user`（自分だけ・すべてのプロジェクト） | このリポジトリの `app.mcp_agent` を動かしたときだけ |

  - 手元での確認：`claude -p --mcp-config app/mcp_servers.json --strict-mcp-config` で演習の設定をそのまま読ませた。`glossary`（3 ツール）と `fetch` は使えたが、**`aws` だけ読み込まれなかった**。写しに `"type": "http"` を足すと、`mcp__aws__aws___search_documentation` など 5 個が増えた。ドキュメントにも「`type` がなく `url` だけの項目は stdio として読まれ、エラーになる」とある。
  - ツールの名前の付け方：Claude Code は `mcp__glossary__search_glossary`（`mcp__` + サーバー名 + `__` + ツール名）、演習のエージェントは `glossary_search_glossary`（サーバー名 + `_` + ツール名）。サーバー名を前に付けて区別する考え方は同じだが、区切り文字が違う。
- 気づき・疑問：
  - 用語集・fetch・AWS の MCP サーバーは、一切変えずに Claude Code からも使えた。どのアプリからでも同じサーバーを使えるように、つなぎ方を共通にしたのが MCP だと実感した。
  - 違ったのはサーバーではなく、使う側（各アプリ）の設定ファイルの書き方。設定ファイルの形は MCP の決まりに含まれず、アプリごとに決めている。`mcpServers` の下にサーバー名を並べて `command` / `args` / `url` を書く基本の形は同じだった。一方で、URL で接続するサーバーに `"type": "http"` が必要なこと、設定の置き場所が有効範囲（scope）ごとに分かれていることが違った。サーバーは使い回せるが、つなぐ設定は使うアプリのドキュメントに合わせる必要がある。
  - `project` 範囲の `.mcp.json` は Git で共有されるので、他の人が足したサーバーが自分の環境で起動する可能性がある。Claude Code が使う前に承認を求めるのは、補足の「信頼できるサーバーか確認する」を仕組みにしたものだと理解した。ドキュメントにも「外部の内容を取得するサーバーはプロンプトインジェクションのリスクがある」とあり、fetch のようなサーバーは特に注意が要る。
  - API キーは `-e KEY=value` や `.mcp.json` の `${VAR}` 展開で渡せる。共有する `.mcp.json` にはキーを直接書かず、環境変数で渡すのがよさそうだと思った。
