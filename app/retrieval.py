"""第5回: ページ単位のベクトル検索。"""

import argparse
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from collections import defaultdict, deque
from pathlib import Path

from google import genai
from google.genai import types
from pydantic_ai.exceptions import ModelHTTPError
import sqlite_vec

from app.config import (
    EMBEDDING_DIMENSIONS, EMBEDDING_MAX_TOKENS, EMBEDDING_MODEL,
    RAG_DB, RAG_DOCUMENT_IDS, RAG_SOURCE, RAG_TOP_K, RAG_TREE, get_api_key,
    RAG_GRAPH, GRAPH_START_K, GRAPH_HOPS, GRAPH_MAX_RESULTS, NEIGHBOR_WINDOW,
    HYBRID_CANDIDATES, HYBRID_RRF_K, HYBRID_TOP_K, HYBRID_EXPAND_TOP, HYBRID_MAX_RESULTS,
)


def get_all_materials() -> str:
    """全資料を、講義・章・ページの情報付きで1つの文字列にまとめる。"""
    documents = json.loads(RAG_SOURCE.read_text(encoding="utf-8"))
    return "\n\n".join(
        f"資料: {document['id']} / {document['title']}\n"
        f"章: {section['section']}\n"
        f"ページ: PDF p.{page['page']} / {page['title']}\n{page['content']}"
        for document in documents
        for section in document["content"]
        for page in section["content"]
    )

def load_pages(source: Path = RAG_SOURCE) -> list[dict]:
    """資料→章→ページのJSONを、対象資料のページ一覧に変換する。"""
    documents = json.loads(source.read_text(encoding="utf-8"))
    pages = []
    for document in documents:
        if document["id"] not in RAG_DOCUMENT_IDS:
            continue
        for section in document["content"]:
            for page in section["content"]:
                pages.append({"page_id": page["id"], "document_id": document["id"],
                              "lecture": int(document["id"][3:5]), "document_title": document["title"],
                              "section": section["section"], "title": page["title"],
                              "page": page["page"], "content": page["content"]})
    return pages


def browse_tree(node_id: str | None = None) -> dict:
    """直下のページは先頭文、指定したページ自身は全文を返す。"""
    tree = json.loads(RAG_TREE.read_text(encoding="utf-8"))
    tree["children"] = [node for node in tree["children"] if node["id"] in RAG_DOCUMENT_IDS]
    node_id = node_id or tree["id"]
    pages = {page["page_id"]: page for page in load_pages(RAG_SOURCE)}

    def describe(node, full=False):
        info = {key: node[key] for key in ("id", "kind", "title")}
        if node["kind"] == "page":
            info.update({key: value for key, value in pages[node["id"]].items() if key != "page_id"})
            if not full:
                info["content"] = re.split(r"(?<=[。！？])|\n", info["content"].strip(), maxsplit=1)[0]
        return info

    remaining = [tree]
    while remaining:
        node = remaining.pop()
        if node["id"] == node_id:
            return {
                "node": describe(node, full=True),
                "children": [describe(child) for child in node.get("children", [])],
            }
        remaining.extend(node.get("children", []))
    raise ValueError("対象の目次ノードが見つかりません。")


def read_page(page_id: str) -> dict:
    """第1〜3回の本講義から、指定した1ページの本文と引用情報を返す。"""
    for page in load_pages(RAG_SOURCE):
        if page["page_id"] == page_id:
            return page
    raise ValueError("対象のページが見つかりません。")


def normalized_vector(values: list[float]) -> list[float]:
    """ベクトルの長さを1に揃える。"""
    norm = math.hypot(*values)
    if norm == 0:
        raise ValueError("埋め込みがゼロベクトルです。")
    return [value / norm for value in values]


def embed_text(text: str, task_type: str) -> list[float]:
    """Geminiで文章を埋め込む。入力上限を超えた場合は切り捨てず停止する。"""
    with genai.Client(api_key=get_api_key()) as client:
        count = client.models.count_tokens(model=EMBEDDING_MODEL, contents=text).total_tokens
        if count is None or count > EMBEDDING_MAX_TOKENS:
            raise ValueError(f"埋め込み入力が上限を超えるか計測不能です: {count} tokens。")
        response = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=text,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIMENSIONS),
        )
    embedding = response.embeddings[0]
    if embedding.statistics and embedding.statistics.truncated:
        raise ValueError("埋め込みAPIが本文を切り捨てました。")
    return normalized_vector(embedding.values)


@contextmanager
def open_index(path: Path):
    """既存の検索DBを読み取り専用で開き、終了時に閉じる。"""
    if not path.is_file():
        raise FileNotFoundError("検索DBがありません。")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        db.row_factory = sqlite3.Row
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        yield db
    finally:
        db.close()


def search(query: str, top_k: int | None = None) -> list[dict]:
    """質問を埋め込み、近いページを最大top_k件（省略時はRAG_TOP_K件）返す。"""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("検索語が空です。")
    with open_index(RAG_DB) as db:
        vector = embed_text(query.strip(), "RETRIEVAL_QUERY")
        rows = db.execute("""
            SELECT page_id, document_id, lecture, document_title, section, title, page, content,
                   vec_distance_cosine(embedding, ?) AS distance
            FROM chunks ORDER BY distance, page_id LIMIT ?
        """, (sqlite_vec.serialize_float32(vector), RAG_TOP_K if top_k is None else top_k))
        return [dict(row) for row in rows]


def with_neighbors(hits: list[dict], pages: list[dict], window: int = NEIGHBOR_WINDOW) -> list[dict]:
    """検索結果の順を保ち、同じ資料の前後ページを重複なしで後ろに足す。"""
    by_position = {(page["document_id"], page["page"]): page for page in pages}
    seen = {hit["page_id"] for hit in hits}
    results = [{**hit, "retrieved_by": hit.get("retrieved_by", "search")} for hit in hits]
    for hit in hits:
        for offset in (o for d in range(1, window + 1) for o in (-d, d)):
            page = by_position.get((hit["document_id"], hit["page"] + offset))
            if page and page["page_id"] not in seen:
                seen.add(page["page_id"])
                results.append({**page, "retrieved_by": "neighbor", "neighbor_of": hit["page_id"]})
    return results


def search_with_neighbors(query: str) -> list[dict]:
    """第5回 宿題（実装）: ベクトル検索の結果に、前後ページの本文を足して返す。"""
    return with_neighbors(search(query), load_pages(RAG_SOURCE))


def query_terms(query: str) -> list[str]:
    """質問から、英数字・カタカナ・2文字以上の漢字の連続を検索語として取り出す。"""
    terms = re.findall(r"[A-Za-z][A-Za-z0-9.+-]*|[ァ-ヶー]{2,}|[一-龥]{2,}", query)
    return list(dict.fromkeys(term.lower() for term in terms))


def keyword_rank(query: str, pages: list[dict], limit: int = HYBRID_CANDIDATES) -> list[str]:
    """BM25の考え方で、珍しい語を多く含むページのIDを順に返す（形態素解析は使わない）。"""
    texts = {page["page_id"]: f"{page['title']}\n{page['content']}".lower() for page in pages}
    average_length = sum(map(len, texts.values())) / max(len(texts), 1)
    scores = defaultdict(float)
    for term in query_terms(query):
        matched = {page_id: text.count(term) for page_id, text in texts.items() if term in text}
        idf = math.log(1 + (len(texts) - len(matched) + 0.5) / (len(matched) + 0.5))
        for page_id, count in matched.items():
            length_ratio = len(texts[page_id]) / average_length
            scores[page_id] += idf * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length_ratio))
    return sorted(scores, key=lambda page_id: (-scores[page_id], page_id))[:limit]


def fuse_rankings(rankings: list[list[str]], k: int = HYBRID_RRF_K) -> list[str]:
    """Reciprocal Rank Fusion: 距離とスコアの尺度が違う検索を、順位だけで統合する。"""
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, page_id in enumerate(ranking, 1):
            scores[page_id] += 1 / (k + rank)
    return sorted(scores, key=lambda page_id: (-scores[page_id], page_id))


def search_hybrid(query: str) -> list[dict]:
    """第5回 宿題（発展）: ベクトルとキーワードを統合し、上位ページの前後だけを足す。"""
    pages = load_pages(RAG_SOURCE)
    by_id = {page["page_id"]: page for page in pages}
    vector_ids = [hit["page_id"] for hit in search(query, top_k=HYBRID_CANDIDATES)]
    keyword_ids = keyword_rank(query, pages)
    fused = [page_id for page_id in fuse_rankings([vector_ids, keyword_ids]) if page_id in by_id]
    hits = [{**by_id[page_id], "retrieved_by": "hybrid"} for page_id in fused[:HYBRID_TOP_K]]
    expanded = with_neighbors(hits[:HYBRID_EXPAND_TOP], pages)
    extras = [page for page in expanded if page["retrieved_by"] == "neighbor"
              and page["page_id"] not in {hit["page_id"] for hit in hits}]
    return (hits + extras)[:HYBRID_MAX_RESULTS]


def search_graph(query: str) -> dict:
    """ベクトル検索を入口に、前後ページと共通用語で候補を広げる。"""
    pages = {page["page_id"]: page for page in load_pages(RAG_SOURCE)}
    graph = json.loads(RAG_GRAPH.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]
             if node["kind"] == "term" or node["id"] in pages}
    adjacent = defaultdict(set)
    for edge in graph["edges"]:
        a, b = edge["source"], edge["target"]
        if edge["relation"] in ("next_page", "mentions") and a in nodes and b in nodes:
            adjacent[a].add(b)
            adjacent[b].add(a)

    seeds = [hit for hit in search(query) if hit["page_id"] in pages][:min(GRAPH_START_K, GRAPH_MAX_RESULTS)]
    seed_ids = {seed["page_id"] for seed in seeds}
    results, candidates = [], {}
    for rank, seed in enumerate(seeds):
        root = seed["page_id"]
        results.append({**pages[root], "distance": seed["distance"], "hops": 0,
                        "path": [{"id": root, "title": pages[root]["title"]}]})
        queue = deque([(root, [root])])
        visited = {root}
        while queue:
            current, path = queue.popleft()
            if len(path) - 1 >= GRAPH_HOPS:
                continue
            # 同じ深さなら、接続先が少ない用語からたどる。
            neighbors = sorted(adjacent[current], key=lambda n: (len(adjacent[n]), n))
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                route = path + [neighbor]
                queue.append((neighbor, route))
                if neighbor not in pages or neighbor in seed_ids:
                    continue
                frequency = max((len(adjacent[n]) for n in route if nodes[n]["kind"] == "term"), default=0)
                priority = (len(route) - 1, frequency, rank, neighbor)
                candidate = {**pages[neighbor], "hops": len(route) - 1,
                             "path": [{"id": n, "title": nodes[n]["title"]} for n in route]}
                if neighbor not in candidates or priority < candidates[neighbor][0]:
                    candidates[neighbor] = (priority, candidate)
    expanded = [candidate for _, candidate in sorted(candidates.values())]
    return {"seeds": results, "expanded": expanded[:max(0, GRAPH_MAX_RESULTS - len(results))],
            "max_hops": GRAPH_HOPS}



def run_full_context(agent, question: str, model, instructions: str, prompt_template: str):
    """全資料を一括投入し、検索ツールを使わずに回答する。"""
    prompt = prompt_template.format(materials=get_all_materials(), question=question)
    print(f"[full-context] 入力{len(prompt):,}文字")
    try:
        with agent.override(tools=[], instructions=instructions):
            return agent.run_sync(prompt, model=model)
    except ModelHTTPError as e:
        print(f"[full-context] APIエラー HTTP {e.status_code}: {e.body}")
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="エージェントを使わず、講義資料の検索だけを実行する")
    parser.add_argument("query", help="調べたい内容")
    args = parser.parse_args()
    for i, result in enumerate(search(args.query), 1):
        print(f"\n{'=' * 60}\n検索結果 {i}\n{'=' * 60}")
        print(f"講義: {result['document_title']}")
        print(f"章: {result['section']}")
        print(f"タイトル: {result['title']}")
        print(f"ページ: {result['page']}")
        print(f"\n{result['content']}")
