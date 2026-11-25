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

- 取り組んだレベル：基礎 / 実装 / 発展
- やったこと：
- 結果：
- 気づき・疑問：
