# 第3回 解答

実行環境：ローカルの Mac（`uv run`）、モデルは既定の `gemini-3.5-flash-lite`。LLM の出力は実行ごとに揺れるので、宿題の比較は各条件2回ずつ実行した。

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
  - 質問「AIE2026の講座の宿題にある「3レベル」とは何ですか？」
  - 第1回の `app.ask`：「初級・中級・上級のような難易度区分かもしれないし、利用・カスタマイズ・開発の3階層かもしれない。指示書やTAに確認を」という一般論の推測だった。用語集の正しい意味（取り組み方の3段階で、どれか1つで完了）とは違っていた
  - 第3回の `app.agent`：「基礎（講義内容の確認）・実装（自分でコードを書く）・発展（調査や試行）の3段階で、どれか1つに取り組めば完了。原則として採点はない」と答え、`data/glossary.json` の `homework-levels` の定義と一致した。最後に「（関連：第1回）」が付いた
  - モデルは同じでも、答える前に用語集を検索して根拠を得たことで、推測ではなく講座の定義に沿った回答になった
- `--trace` で見えたツール呼び出し（ツール名と引数）：
  - 「3レベル」の質問：`search_glossary({'query': '3レベル'})` の1回。別名 `3レベル` に完全一致した
  - 「LoRAとQLoRAの違いは？」：`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` の2回。2つの呼び出しは1回目の LLM 応答の中でまとめて依頼された（並列呼び出し）。docstring の「query には調べたい用語を1つだけ入れる」に従って、用語ごとに分けて検索している
  - 「第2回の内容から確認問題を1問出して」：`make_quiz({'lecture': 2})` の1回（今回の出題は「ランク（LoRAのr）」）
- 1つの質問での LLM 呼び出し回数（`requests`）：3問とも `requests=2`。1回目でツール呼び出しを依頼し、2回目でツールの結果を読んで回答を書く。LoRA/QLoRA の質問は `tool_calls=2` だが、2つの検索を1回の応答で同時に依頼したので、`requests` は2回のまま。入力トークンは 1,438（LoRA/QLoRA）、1,025（3レベル）、967（確認問題）
- 追加したツールと、docstring に書いた説明：
  - `make_quiz(lecture: int) -> str`（`app/tools.py`）。`load_glossary()` から `lecture` が一致する用語を集め、`random.choice` で1つ選び、`{"question": "「○○」の意味は？", "answer": 定義, "lecture": N}` を JSON 文字列で返す。用語が無い回（`lecture=0` など）では、例外を出さずに「第0回の用語は用語集にありません。問題を作れる回: 第1回, 第2回, …」を返す
  - docstring：「指定した回（1始まりの整数）の用語から1つを選び、確認問題と答えを返す。『第2回の確認問題を出して』『第3回の復習クイズがほしい』のように、復習用の問題を求められたときに使う。返り値の question を出題し、answer は利用者が答えたあとの答え合わせ（または解説）に使う。」
  - `app/agent.py` の TODO の場所で `agent.tool_plain(tools.make_quiz)` と登録した。`--list-tools` に表示され、`INSTRUCTIONS` に何も足さなくても呼ばれた。モデルは返り値の answer を出さずに、問題だけを出題した（docstring の「answer は答え合わせに使う」に従っている）
  - `uv run pytest -q`：すべて passed

## 宿題

全レベル（基礎・実装・発展(a)）に取り組んだ。

### 基礎：INSTRUCTIONS と docstring を1か所ずつ変えて比べる

- 取り組んだレベル：基礎
- やったこと：次の4条件で、同じ質問を `--trace` 付きで各2回実行した。変えたのは毎回1か所だけ（B1b だけは、B1 の結果を受けて2か所）で、実行後は元に戻した

  | 条件 | 変更 |
  |---|---|
  | B0 | 変更なし（基準） |
  | B1 | `INSTRUCTIONS` から「用語や講座に固有のことを答える前に、必ず search_glossary で用語集を確認する。」の行を削除 |
  | B1b | B1 に加えて、`search_glossary` の docstring から「AIエンジニアリングの用語や、この講座（AIE2026）に固有の言葉について答える前に使うこと。」も削除 |
  | B2 | `search_glossary` の docstring の「query には調べたい用語を1つだけ入れる（例: "LoRA"）」を「まとめて入れる（例: "LoRA QLoRA"）」に変更 |
  | B3 | `INSTRUCTIONS` の「回答の最後に、関係する回（第N回）を示す。」を「回答の最後に、確認問題を1問出す。」に変更 |

- 結果：

  | 条件 | 質問 | ツール呼び出し（2回とも同じ） | `requests` / `tool_calls` | 入力トークン | 回答の変化 |
  |---|---|---|---|---|---|
  | B0 | LoRAとQLoRAの違いは？ | `search_glossary('LoRA')`, `search_glossary('QLoRA')` | 2 / 2 | 1,438 | 定義に沿った説明＋「第2回」 |
  | B0 | 3レベルとは？ | `search_glossary('3レベル')` | 2 / 1 | 1,025 | 正しい定義＋「第1回」 |
  | B1 | LoRAとQLoRAの違いは？ | B0 と同じ | 2 / 2 | 1,390 | B0 とほぼ同じ |
  | B1 | 3レベルとは？ | B0 と同じ | 2 / 1 | 977 | B0 とほぼ同じ（正しい） |
  | B1b | LoRAとQLoRAの違いは？ | B0 と同じ | 2 / 2 | 1,330 | B0 とほぼ同じ |
  | B1b | 3レベルとは？ | B0 と同じ | 2 / 1 | 917 | B0 とほぼ同じ（正しい） |
  | B2 | LoRAとQLoRAの違いは？ | `search_glossary('LoRA QLoRA')` の1回 | 2 / 1 | 1,133 | B0 と同等の内容 |
  | B3 | LoRAとQLoRAの違いは？ | B0 と同じ | 2 / 2 | 1,430 | 説明のあとに確認問題が付いた（1回目は3択、2回目は記述式）。末尾の「関係する回：第2回」の行は2回とも消え、代わりに「第2回からの確認問題です」と前置きで回に触れた。出力トークンは 358 / 244（B0 は 235 / 223） |

  - B1・B1b：「必ず検索する」という指示を消しても、さらに docstring の「答える前に使うこと」まで消しても、4回とも検索してから答えた。入力トークンは消した文の分だけ減った
  - B2：検索が1回にまとまり、`tool_calls` が 2→1、入力トークンが 1,438→1,133 に減った。それでも LoRA と QLoRA の両方が見つかった。これは `search_glossary` が空白を除いて正規化し、名前が検索語に含まれるかで部分一致を取る実装（`"loraqlora"` に `"lora"` と `"qlora"` が含まれる）だったため。`requests` は B0 も B2 も 2 で変わらなかった。B0 でも2つの検索を1回の応答で並列に依頼していたため
  - B3：指示を置き換えると、その指示どおりに回答の形が変わった。末尾の第N回の表示は、指示を消すと出なくなった。指示が回答の構成をほぼそのまま決めている
- 気づき・疑問：
  - 検索するかどうかは、「必ず使え」という指示よりも、ツールの名前と説明（「講座の用語集から用語を検索し…」）と、質問に「AIE2026」「LoRA」など用語集に載っていそうな言葉があることで決まっているように見えた。用語集に載っていなさそうな一般的な質問（例：「Pythonのリスト内包表記とは？」）なら、B1b で検索を省くかもしれない。今回は試していない
  - B2 は今回はたまたまうまくいったが、検索側の実装に依存している。「LoRA、量子化」のように区切りや表記が変わると、部分一致に失敗する可能性がある。docstring を変えるときは、ツールの実装がその使われ方に耐えるかも一緒に確認する必要がある
  - `requests`（LLM の呼び出し回数）は `tool_calls` とは別に数える。並列に呼べるかどうかで、応答時間やレート制限への効き方が変わる

### 実装：save_learning_log（保存の前に利用者の確認を挟む）

- 取り組んだレベル：実装
- やったこと：
  - `app/tools.py` に `save_learning_log(title: str, content: str) -> str` を追加した。`learning_log/YYYYMMDD-HHMMSS.md` に Markdown で保存する。同じ秒に保存しても上書きしないよう、既存ファイルがあれば `-2`, `-3` を付ける。`learning_log/` は `.gitignore` 済み
  - `app/agent.py` で `agent.tool_plain(tools.save_learning_log, requires_approval=True)` と登録し、`output_type=[str, DeferredToolRequests]` にした
  - CLI に `run_with_approval()` / `ask_approvals()` を追加した。結果が `DeferredToolRequests` なら、`approvals` の呼び出しごとにツール名と引数を表示して `[y/N]` を聞く。y なら `True`、それ以外（EOF を含む）なら `ToolDenied("利用者が保存を承認しませんでした。")` を `DeferredToolResults` に入れ、`message_history=result.all_messages()` と一緒に `run_sync` で再開する。再開時に `usage=result.usage` を渡し、承認の前後の LLM 呼び出し回数を通算するようにした
  - `tests/test_learning_log.py` を追加した（TestModel を使い、API キー不要）。確かめたのは次の4点：承認前は何も書き込まれず `DeferredToolRequests` が返る／承認すると1件保存される／拒否すると保存されない／連続保存で上書きしない。`uv run pytest -q` は 21 passed
- 結果：
  - 1回目（失敗）：docstring の最後に「保存はファイルを書き込む操作なので、実行前に利用者の承認を求める。」と書いていた。すると、モデルはツールを呼ばず、チャットで「以下の内容で保存してもよろしいでしょうか？承認いただける場合は『保存して』とお知らせください」と自分で聞き返した（ツール呼び出しは `search_glossary` 2回のみ）。承認はプログラム側が行うのに、docstring の文をモデルが「自分で確認してから呼べ」と読んだ
  - docstring を「保存の前の確認はプログラムが利用者に直接行うので、会話で『保存してよいか』を聞き返さず、頼まれたらそのまま呼ぶこと。」に直したところ、狙いどおりに動いた
  - 承認した場合（`echo y | uv run python -m app.agent --trace "今日学んだLoRAとQLoRAの違いの要点を学習ログに保存して"`）：

    ```text
    [承認待ち] save_learning_log を次の引数で実行しようとしています:
      content: LoRAとQLoRAの違いについて学習した。
        - LoRA: 元の重みを固定し、低ランク行列（AとB）を追加して効率的にファインチューニングを行う手法。
        - QLoRA: ...
      title: LoRAとQLoRAの違いの学習
    実行してよいですか？ [y/N]: 今日の学習内容（LoRAとQLoRAの違い）を学習ログに保存しました！
    --- trace ---
    [tool call]   search_glossary({'query': 'LoRA'})
    [tool call]   search_glossary({'query': 'QLoRA'})
    [tool call]   save_learning_log({'content': '...', 'title': 'LoRAとQLoRAの違いの学習'})
    [tool return] save_learning_log -> learning_log/20261109-124755.md に保存しました。…
    ```

    `learning_log/20261109-124755.md` が作られた。モデルは同じ応答の中で、検索2回と保存1回をまとめて依頼した。そのため、検索の結果を見る前に保存内容を書いており、保存内容には用語集に無い「（AとB）」が混じっていた
  - 拒否した場合（`echo n | ... "今日学んだ make_quiz の作り方を学習ログに保存して"`）：ファイルは作られなかった。`[tool return] save_learning_log -> 利用者が保存を承認しませんでした。` を受け、モデルは「保存は行いませんでした」と伝えた。`requests=2`（承認待ちで止まるまで1回＋再開後1回）
- 気づき・疑問：
  - `requires_approval=True` があると、モデルは「呼ぶ」ことしか決められず、実行するかどうかは人間が決める。ただし docstring に承認の話を書くと、モデルが会話で確認を二重に取ろうとした。「誰が確認するか」まで docstring に書く必要があった
  - 承認画面で引数（保存される本文）をそのまま見せるのが大事だと感じた。今回の保存内容には用語集に無い記述が混ざっていた。人間が中身を見てから承認できるのが、この仕組みの価値だと思う
  - 疑問：検索と保存を同じ応答で並列に依頼されると、検索結果を反映しない内容が保存されうる。「保存は検索結果を見てから」と順序を指示すべきか、`sequential=True` のような仕組みで制御すべきか

### 発展(a)：同じエージェントを Google ADK で組み立て直す

- 取り組んだレベル：発展(a)
- やったこと：`adk_agent/glossary_agent/agent.py` と `__init__.py`（`from . import agent`）を作った。`app/agent.py` の `INSTRUCTIONS` と、`app/tools.py` の `search_glossary`・`get_lecture_summary`・`make_quiz` をそのまま渡した（承認付きの `save_learning_log` は対象外）。ADK は 2.14.0（`uv run --with google-adk`）。`PYTHONPATH=. uv run --with google-adk adk run --session_service_uri memory:// adk_agent/glossary_agent "質問"` で、演習と同じ3問を実行した
- 結果（書き方の違い）：

  | | Pydantic AI（演習） | ADK |
  |---|---|---|
  | 指示 | `Agent(instructions=INSTRUCTIONS)` | `Agent(instruction=INSTRUCTIONS)`（単数形） |
  | ツール | 作ってから `agent.tool_plain(f)` で1つずつ登録（承認付きなどのオプションも登録時に指定） | 作るときに `tools=[f1, f2, f3]` とリストで渡す |
  | モデル | 実行時に `run_sync(..., model=...)` で渡す（テストでは TestModel に差し替え） | エージェント定義に `model="gemini-3.5-flash-lite"` と文字列で書く |
  | 名前 | 不要 | `name` が必須。`description` も書ける（複数エージェントで役割分担するときに使う） |
  | 実行 | 自分で書いた CLI（`python -m app.agent`、`--trace` も自作） | `adk run` が対話画面・セッション管理・ログを用意する |
  | API キー | `app/config.py` で `GEMINI_API_KEY` を読んで渡す | `GEMINI_API_KEY` を自動で読む |
  | ツールの戻り値 | 文字列のままモデルに返す | `{'result': '...'}` に包んで返す |

- 結果（回答の違い）：
  - 3問とも、Pydantic AI 版と同じツールが同じ引数で呼ばれた：`search_glossary('3レベル')`／`search_glossary('LoRA')` と `('QLoRA')`／`make_quiz(2)`。ADK のログ（`agent.log`）でも、LLM へのリクエストは各問2回で、`requests=2` と同じだった。`adk run` の画面にはツール呼び出しが出ないので、ADK の `InMemoryRunner` のイベント（`function_call` / `function_response`）を読む小さなスクリプトを手元で書いて確認した（リポジトリには入れていない）
  - 回答の内容は同等で、どれも用語集の定義に沿い、最後に第N回が付いた。「3レベル」では、ADK 版が「宿題に迷ったら、コードをそのまま書くのではなく考え方のヒントから一緒に整理しましょう」と付け加えた。これは INSTRUCTIONS の「宿題の答えそのものは書かず、考え方のヒントで導く」が表に出たもの。Pydantic AI 版でも言い回しは毎回変わるので、フレームワークの差というより出力の揺れの範囲だと思う
- 気づき・疑問：
  - 「モデル＋指示＋ツール（関数の名前・docstring・型ヒント）」という骨格はどちらも同じで、ツール関数と INSTRUCTIONS は1行も変えずに使い回せた。エージェントの動きを決めているのは主にこの3つで、フレームワークは「ループを回す部分」と「周辺機能」の違いだと分かった
  - ADK は `adk run`（や Web UI）、セッション、ログが最初から付いてくる代わりに、モデルをエージェント定義に書くので、テストでモデルを差し替える方法は Pydantic AI の `agent.override(model=TestModel())` ほど手軽には見えなかった
  - 疑問：ADK で `requires_approval` に当たる人間の承認（Human-in-the-Loop）はどう書くのか（今回は対象外）
