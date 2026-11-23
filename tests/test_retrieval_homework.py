"""第5回 宿題: 前後ページの追加とハイブリッド検索のテスト（APIキーを使わない）。"""

from app import retrieval


def _page(number, content="本文", document="lec02-main"):
    return {"page_id": f"{document}-p{number:03d}", "document_id": document, "page": number,
            "title": f"p{number}", "content": content}


def test_neighbors_keep_order_without_duplicates_or_other_documents():
    pages = [_page(1), _page(2), _page(3), _page(4), _page(2, document="lec03-main")]
    results = retrieval.with_neighbors([pages[1], pages[2]], pages)
    assert [r["page_id"] for r in results] == [
        "lec02-main-p002", "lec02-main-p003", "lec02-main-p001", "lec02-main-p004"]
    assert [r["retrieved_by"] for r in results] == ["search", "search", "neighbor", "neighbor"]


def test_neighbors_stop_at_document_edges():
    pages = [_page(1), _page(2)]
    assert [r["page"] for r in retrieval.with_neighbors([pages[0]], pages)] == [1, 2]


def test_keyword_rank_prefers_rare_matching_term():
    pages = [_page(1, "LoRA LoRA"), _page(2, "モデル"), _page(3, "モデル 冪等性")]
    assert retrieval.keyword_rank("冪等性とは", pages)[0] == "lec02-main-p003"


def test_fusion_rewards_pages_found_by_both():
    assert retrieval.fuse_rankings([["a", "b"], ["c", "b"]])[0] == "b"


def test_hybrid_respects_limit_and_has_no_duplicates(monkeypatch):
    pages = [_page(n, f"用語{n}") for n in range(1, 21)]
    monkeypatch.setattr(retrieval, "load_pages", lambda *_: pages)
    monkeypatch.setattr(retrieval, "search", lambda q, top_k=None: pages[5:15])
    ids = [r["page_id"] for r in retrieval.search_hybrid("用語")]
    assert len(ids) == len(set(ids)) <= retrieval.HYBRID_MAX_RESULTS
