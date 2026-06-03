"""论文摘要存储与检索 — 纯 Python，仅依赖标准库

功能:
- 摘要存储到本地 JSON 文件（无需 Milvus）
- BM25 关键词检索（纯 Python 实现）
- 核心论文筛选（基于摘要 BM25 评分）
- 多关键词 RRF 融合检索
- Milvus 向量检索 + BGE embedding（可选，需额外依赖）

设计目标: 零外部依赖，可在任何环境运行。
Milvus 模式需要 pymilvus + sentence-transformers。
"""

import os
import re
import json
import math
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict, Counter


# ─── 摘要存储 ───

class AbstractStore:
    """论文摘要存储，基于本地 JSON 文件"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store_path = data_dir / "abstracts.json"
        self._papers = {}  # normalized_title -> paper

    def load(self):
        """从文件加载已有摘要"""
        if self.store_path.exists():
            with open(self.store_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for p in data:
                        nt = _normalize(p.get("title", ""))
                        self._papers[nt] = p
                elif isinstance(data, dict):
                    self._papers = data

    def add(self, paper: Dict) -> bool:
        """添加一篇论文摘要，返回是否新增"""
        nt = _normalize(paper.get("title", ""))
        if not nt or not paper.get("summary"):
            return False
        if nt in self._papers:
            return False
        self._papers[nt] = paper
        return True

    def add_batch(self, papers: List[Dict]) -> tuple:
        """批量添加，返回 (新增数, 跳过数)"""
        new = 0
        skipped = 0
        for p in papers:
            if self.add(p):
                new += 1
            else:
                skipped += 1
        return new, skipped

    def save(self):
        """保存摘要到文件"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(list(self._papers.values()), f, indent=4, ensure_ascii=False)

    def all_papers(self) -> List[Dict]:
        return list(self._papers.values())

    def get_abstract(self, normalized_title: str) -> Optional[str]:
        paper = self._papers.get(normalized_title)
        return paper.get("summary", "") if paper else None

    def count(self) -> int:
        return len(self._papers)


# ─── BM25 检索 ───

class BM25Retriever:
    """BM25 全文检索引擎（纯 Python）

    对摘要进行分词和索引，支持多关键词 RRF 融合。
    无需 Milvus、无需 embedding 模型。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # BM25 参数
        self.b = b    # BM25 参数
        self._docs = []         # List[Dict] 论文列表
        self._doc_ids = []      # List[int] 对应索引
        self._corpus = []       # List[List[str]] 分词后的文档
        self._df = defaultdict(int)  # 词 -> 文档频率
        self._N = 0             # 文档总数
        self._avgdl = 0         # 平均文档长度

    def build_index(self, papers: List[Dict]):
        """对论文摘要构建 BM25 索引"""
        self._docs = papers
        self._doc_ids = list(range(len(papers)))
        self._corpus = []
        self._df = defaultdict(int)

        for paper in papers:
            text = paper.get("summary", "") + " " + paper.get("title", "")
            tokens = _tokenize_zh_en(text)
            self._corpus.append(tokens)
            for t in set(tokens):
                self._df[t] += 1

        self._N = len(self._corpus)
        self._avgdl = sum(len(c) for c in self._corpus) / max(self._N, 1)

    def search(self, query: str, top_k: int = 20) -> List[tuple]:
        """BM25 搜索，返回 (doc_index, score) 列表"""
        if not self._corpus:
            return []

        query_tokens = _tokenize_zh_en(query)
        if not query_tokens:
            return []

        scores = []
        for i, doc in enumerate(self._corpus):
            score = self._bm25_score(query_tokens, doc, len(doc))
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _bm25_score(self, query_tokens: List[str], doc: List[str], doc_len: int) -> float:
        score = 0.0
        for token in query_tokens:
            df = self._df.get(token, 0)
            if df == 0:
                continue
            # IDF
            idf = math.log((self._N - df + 0.5) / (df + 0.5) + 1)
            # TF
            tf = doc.count(token)
            tf_norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self._avgdl))
            score += idf * tf_norm
        return score

    def search_multi_rrf(self, queries: List[str], top_k: int = 40,
                         exclude_titles: Optional[set] = None) -> List[Dict]:
        """多关键词 RRF 融合检索

        Args:
            queries: 关键词列表
            top_k: 返回论文数
            exclude_titles: 需要排除的标题集合

        Returns:
            论文列表，按 RRF 分数排序
        """
        rrf_scores = defaultdict(float)
        paper_indices = {}  # doc_idx -> paper

        for query in queries:
            results = self.search(query, top_k=top_k * 2)
            for rank, (doc_idx, score) in enumerate(results, 1):
                paper = self._docs[doc_idx]
                nt = _normalize(paper.get("title", ""))
                if exclude_titles and nt in exclude_titles:
                    continue
                rrf_scores[doc_idx] += 1.0 / (rank + 60)
                paper_indices[doc_idx] = paper

        # 按 RRF 分数排序
        merged = []
        for doc_idx in sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]:
            paper = dict(paper_indices[doc_idx])
            paper["rrf_score"] = round(rrf_scores[doc_idx], 4)
            merged.append(paper)

        return merged


# ─── 核心论文筛选 ───

def select_key_papers(store: AbstractStore, query: str, limit: int = 6) -> List[Dict]:
    """从摘要库中筛选与 query 最相关的核心论文

    使用 BM25 检索 + 标题匹配加分。
    """
    papers = store.all_papers()
    if not papers:
        return []

    retriever = BM25Retriever()
    retriever.build_index(papers)
    results = retriever.search(query, top_k=limit * 3)

    scored = []
    query_words = set(_tokenize_zh_en(query))
    for doc_idx, score in results:
        paper = papers[doc_idx]
        # 标题匹配加分
        title_tokens = set(_tokenize_zh_en(paper.get("title", "")))
        if query_words & title_tokens:
            score *= 1.3
        paper_with_score = dict(paper)
        paper_with_score["score"] = round(score, 4)
        scored.append(paper_with_score)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


# ─── 文本处理 ───

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _tokenize_zh_en(text: str) -> List[str]:
    """简单中英文分词

    - 英文按空格和标点分割
    - 中文按字符分割（2 字以上词组保留）
    """
    text = text.lower()
    # 替换常见标点为空格
    text = re.sub(r'[^\w一-鿿\s]', ' ', text)
    tokens = []
    for token in text.split():
        if re.match(r'^[a-z]+$', token) and len(token) >= 2:
            tokens.append(token)
        elif re.match(r'^[一-鿿]+$', token):
            # 中文：逐字 + n-gram (2-4)
            chars = list(token)
            tokens.extend(chars)
            for n in range(2, min(5, len(chars) + 1)):
                for i in range(len(chars) - n + 1):
                    tokens.append(''.join(chars[i:i + n]))
        elif len(token) >= 2:
            tokens.append(token)
    # 去重保序
    seen = set()
    result = []
    for t in tokens:
        if t not in seen and len(t) >= 2:
            seen.add(t)
            result.append(t)
    return result


# ─── Milvus 向量检索（可选依赖）───

_DEFAULT_EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL_PATH", "")
_DEFAULT_MILVUS_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "milvus_data" / "milvus_data.db")
_COLLECTION_NAME = "paper_knowledge_base"
_DIMENSION = 1024  # BGE-large-zh-v1.5


class MilvusStore:
    """论文摘要向量存储 — 基于 Milvus Lite + BGE embedding

    可选依赖: pymilvus, sentence-transformers
    接口与 AbstractStore 兼容，下游代码无需修改。
    """

    def __init__(self, data_dir: Path, embedding_model: str = None,
                 milvus_uri: str = None):
        self.data_dir = data_dir
        self.embedding_model_path = embedding_model or _DEFAULT_EMBEDDING_MODEL
        self.milvus_uri = milvus_uri or _DEFAULT_MILVUS_DB_PATH
        self._client = None
        self._embedder = None
        self._papers = {}  # 本地缓存 normalized_title -> paper

    def _ensure_client(self):
        """懒加载 Milvus 客户端和 embedding 模型"""
        if self._client is not None:
            return

        from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType

        self._client = MilvusClient(uri=self.milvus_uri)

        if self._client.has_collection(collection_name=_COLLECTION_NAME):
            pass
        else:
            schema = CollectionSchema(
                fields=[
                    FieldSchema(name='id', dtype=DataType.INT64, is_primary=True),
                    FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=_DIMENSION),
                    FieldSchema(name='chunk_index', dtype=DataType.INT64),
                    FieldSchema(name='content', dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name='entry_id', dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name='content_type', dtype=DataType.VARCHAR, max_length=50),
                    FieldSchema(name='normalized_title', dtype=DataType.VARCHAR, max_length=1000),
                    FieldSchema(name='source', dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name='file_name', dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name='venue', dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name='authors', dtype=DataType.VARCHAR, max_length=2000),
                    FieldSchema(name='published', dtype=DataType.VARCHAR, max_length=20),
                    FieldSchema(name='total_chunks', dtype=DataType.INT64),
                ],
            )
            self._client.create_collection(
                collection_name=_COLLECTION_NAME, schema=schema, metric_type="COSINE",
            )

        # Milvus Lite 3.0 需要显式 load
        state = self._client.get_load_state(collection_name=_COLLECTION_NAME, object_type="Collection")
        state_name = str(state.get("state", "")).split(":")[-1].strip().rstrip(">")
        if state_name != "Loaded":
            self._client.load_collection(collection_name=_COLLECTION_NAME)

        # 加载 embedding 模型
        from sentence_transformers import SentenceTransformer
        self._embedder = SentenceTransformer(self.embedding_model_path)

    def _load_local_cache(self):
        """从本地 JSON 缓存加载元数据（避免从 Milvus 查询所有论文）"""
        cache_path = self.data_dir / "abstracts.json"
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for p in data:
                        nt = _normalize(p.get("title", ""))
                        self._papers[nt] = p

    def load(self):
        self._load_local_cache()

    def add(self, paper: Dict) -> bool:
        nt = _normalize(paper.get("title", ""))
        if not nt or not paper.get("summary"):
            return False
        if nt in self._papers:
            return False
        self._papers[nt] = paper
        return True

    def add_batch(self, papers: List[Dict]) -> tuple:
        new = 0
        skipped = 0
        for p in papers:
            if self.add(p):
                new += 1
            else:
                skipped += 1
        return new, skipped

    def _encode(self, text: str) -> list:
        return self._embedder.encode(text, normalize_embeddings=True).tolist()

    def save(self):
        """将本地缓存中的论文摘要向量化入库"""
        import hashlib

        self._ensure_client()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 同步本地缓存到 Milvus
        count = 0
        to_insert = []
        for nt, paper in self._papers.items():
            safe_nt = nt.replace("'", "\\'")
            try:
                res = self._client.query(
                    collection_name=_COLLECTION_NAME,
                    filter=f"normalized_title == '{safe_nt}' and content_type == 'abstract_only'",
                    output_fields=["id"]
                )
            except Exception:
                continue
            if res:
                continue

            title = paper.get("title", "")
            summary = paper.get("summary", "")
            authors = paper.get("authors", [])
            if isinstance(authors, list):
                authors = json.dumps(authors, ensure_ascii=False)

            file_name = paper.get("file_name", "")
            published = paper.get("published", "")
            entry_id = paper.get("entry_id", "")
            source = paper.get("source", "")
            venue = paper.get("venue", "")

            doc_id = int(hashlib.md5((file_name + "0").encode()).hexdigest(), 16) % (10**18)
            embedding = self._encode(f"File: {file_name}\nContent: {summary}")

            to_insert.append({
                "id": doc_id, "chunk_index": 0, "content": summary,
                "embedding": embedding, "entry_id": entry_id,
                "content_type": "abstract_only", "normalized_title": nt,
                "source": source, "venue": venue, "file_name": file_name,
                "authors": authors, "published": published, "total_chunks": 1,
            })
            count += 1

            if len(to_insert) >= 10:
                self._client.insert(_COLLECTION_NAME, data=to_insert)
                to_insert = []

        if to_insert:
            self._client.insert(_COLLECTION_NAME, data=to_insert)
        self._client.flush(_COLLECTION_NAME)

        # 同时保存到本地 JSON 缓存
        cache_path = self.data_dir / "abstracts.json"
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(list(self._papers.values()), f, indent=4, ensure_ascii=False)

        print(f"Milvus 向量入库: 新增 {count} 篇")

    def all_papers(self) -> List[Dict]:
        if not self._papers:
            self._load_local_cache()
        return list(self._papers.values())

    def get_abstract(self, normalized_title: str) -> Optional[str]:
        if not self._papers:
            self._load_local_cache()
        paper = self._papers.get(normalized_title)
        return paper.get("summary", "") if paper else None

    def count(self) -> int:
        if not self._papers:
            self._load_local_cache()
        return len(self._papers)

    def get_retriever(self) -> "MilvusRetriever":
        """返回 MilvusRetriever 实例"""
        self._ensure_client()
        return MilvusRetriever(self._client, self._embedder)

    def _expand_query(self, query: str) -> List[str]:
        """查询扩展：原始 + 首字母缩写 + 小写"""
        variants = [query]
        words = query.split()
        if 2 <= len(words) <= 5:
            variants.append(''.join(w[0].upper() for w in words))
        if query != query.lower():
            variants.append(query.lower())
        return list(dict.fromkeys(variants))

    def select_key_papers(self, query: str, limit: int = 6, min_score: float = 0.3) -> List[Dict]:
        """从 Milvus 中选出与 query 最相关的核心论文"""
        self._ensure_client()
        if not self._papers:
            self._load_local_cache()

        search_filter = "chunk_index == 0 and content_type == 'abstract_only'"
        output_fields = ["content", "chunk_index", "file_name", "normalized_title",
                         "authors", "published", "source", "entry_id", "venue"]

        results = []
        for variant in self._expand_query(query):
            embedding = self._encode(variant)
            try:
                search_res = self._client.search(
                    collection_name=_COLLECTION_NAME, data=[embedding],
                    output_fields=output_fields, limit=limit * 3,
                    search_params={"metric_type": "COSINE", "params": {}},
                    filter=search_filter,
                )
            except Exception:
                continue

            if not search_res or not search_res[0]:
                continue

            for hit in search_res[0]:
                entity = hit.get("entity", hit)
                score = hit.get('distance', entity.get('distance', 0.0))
                file_name = entity.get("file_name", "")
                if not file_name or score < min_score:
                    continue

                # 避免重复
                if any(r.get("file_name") == file_name for r in results):
                    existing = next(r for r in results if r.get("file_name") == file_name)
                    if score > existing.get("score", 0):
                        existing["score"] = round(score, 4)
                    continue

                results.append({
                    "file_name": file_name,
                    "title": entity.get("normalized_title", ""),
                    "normalized_title": entity.get("normalized_title", ""),
                    "summary": entity.get("content", ""),
                    "authors": entity.get("authors", ""),
                    "published": entity.get("published", ""),
                    "source": entity.get("source", ""),
                    "venue": entity.get("venue", ""),
                    "entry_id": entity.get("entry_id", ""),
                    "score": round(score, 4),
                })

        # 标题匹配加分
        query_words = set(_tokenize_zh_en(query))
        for r in results:
            title_tokens = set(_tokenize_zh_en(r.get("title", "")))
            if query_words & title_tokens:
                r["score"] = round(r["score"] * 1.3, 4)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def search_multi_rrf(self, queries: List[str], top_k: int = 40,
                         exclude_titles: Optional[set] = None,
                         min_score: float = 0.3) -> List[Dict]:
        """多关键词 RRF 融合向量检索"""
        self._ensure_client()

        search_filter = "chunk_index == 0 and content_type == 'abstract_only'"
        output_fields = ["chunk_index", "file_name", "normalized_title",
                         "authors", "published", "source", "entry_id", "venue"]

        rrf_scores = defaultdict(float)
        paper_data = {}

        for query in queries:
            for variant in self._expand_query(query):
                embedding = self._encode(variant)
                try:
                    search_res = self._client.search(
                        collection_name=_COLLECTION_NAME, data=[embedding],
                        output_fields=output_fields, limit=max(top_k, 20),
                        search_params={"metric_type": "COSINE", "params": {}},
                        filter=search_filter,
                    )
                except Exception:
                    continue

                if not search_res or not search_res[0]:
                    continue

                for rank, hit in enumerate(search_res[0], 1):
                    entity = hit.get("entity", hit)
                    score = hit.get('distance', entity.get('distance', 0.0))
                    file_name = entity.get("file_name", "")
                    if not file_name or score < min_score:
                        continue

                    nt = _normalize(entity.get("normalized_title", ""))
                    if exclude_titles and nt in exclude_titles:
                        continue

                    rrf_scores[file_name] += 1.0 / (rank + 60)

                    if file_name not in paper_data or score > paper_data[file_name].get("_dist", 0):
                        paper_data[file_name] = {
                            "file_name": file_name,
                            "title": entity.get("normalized_title", ""),
                            "normalized_title": entity.get("normalized_title", ""),
                            "authors": entity.get("authors", ""),
                            "published": entity.get("published", ""),
                            "source": entity.get("source", ""),
                            "venue": entity.get("venue", ""),
                            "entry_id": entity.get("entry_id", ""),
                            "_dist": score,
                        }

        merged = []
        for fn in sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]:
            entry = dict(paper_data[fn])
            entry["rrf_score"] = round(rrf_scores[fn], 4)
            entry.pop("_dist", None)
            merged.append(entry)

        return merged


class MilvusRetriever:
    """Milvus 向量检索器（由 MilvusStore.get_retriever() 创建）"""

    def __init__(self, client, embedder):
        self._client = client
        self._embedder = embedder

    def _encode(self, text: str) -> list:
        return self._embedder.encode(text, normalize_embeddings=True).tolist()

    def search(self, query: str, top_k: int = 20, exclude_titles: Optional[set] = None,
               min_score: float = 0.3) -> List[tuple]:
        """向量搜索，返回 [(paper_dict, score), ...]"""
        search_filter = "chunk_index == 0 and content_type == 'abstract_only'"
        output_fields = ["content", "chunk_index", "file_name", "normalized_title",
                         "authors", "published", "source", "entry_id", "venue"]

        embedding = self._encode(query)
        try:
            search_res = self._client.search(
                collection_name=_COLLECTION_NAME, data=[embedding],
                output_fields=output_fields, limit=top_k,
                search_params={"metric_type": "COSINE", "params": {}},
                filter=search_filter,
            )
        except Exception:
            return []

        if not search_res or not search_res[0]:
            return []

        results = []
        for hit in search_res[0]:
            entity = hit.get("entity", hit)
            score = hit.get('distance', entity.get('distance', 0.0))
            if score < min_score:
                continue
            results.append((dict(entity), score))

        return results[:top_k]

    def search_multi_rrf(self, queries: List[str], top_k: int = 40,
                         exclude_titles: Optional[set] = None,
                         min_score: float = 0.3) -> List[Dict]:
        """多关键词 RRF 融合"""
        rrf_scores = defaultdict(float)
        paper_data = {}

        for query in queries:
            results = self.search(query, top_k=top_k * 2, exclude_titles=exclude_titles, min_score=min_score)
            for rank, (entity, score) in enumerate(results, 1):
                file_name = entity.get("file_name", "")
                if not file_name:
                    continue

                nt = _normalize(entity.get("normalized_title", ""))
                if exclude_titles and nt in exclude_titles:
                    continue

                rrf_scores[file_name] += 1.0 / (rank + 60)
                if file_name not in paper_data or score > paper_data[file_name].get("_dist", 0):
                    paper_data[file_name] = {
                        "file_name": file_name,
                        "title": entity.get("normalized_title", ""),
                        "normalized_title": entity.get("normalized_title", ""),
                        "authors": entity.get("authors", ""),
                        "published": entity.get("published", ""),
                        "source": entity.get("source", ""),
                        "venue": entity.get("venue", ""),
                        "entry_id": entity.get("entry_id", ""),
                        "_dist": score,
                    }

        merged = []
        for fn in sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]:
            entry = dict(paper_data[fn])
            entry["rrf_score"] = round(rrf_scores[fn], 4)
            entry.pop("_dist", None)
            merged.append(entry)

        return merged


# ─── 统一 select_key_papers（自动适配 BM25 / Milvus）───

def select_key_papers(store, query: str, limit: int = 6) -> List[Dict]:
    """从摘要库中筛选与 query 最相关的核心论文

    自动适配存储类型：
    - AbstractStore → BM25 检索
    - MilvusStore → Milvus 向量检索 + 查询扩展
    """
    if isinstance(store, MilvusStore):
        return store.select_key_papers(query, limit=limit)

    # BM25 fallback
    papers = store.all_papers()
    if not papers:
        return []

    retriever = BM25Retriever()
    retriever.build_index(papers)
    results = retriever.search(query, top_k=limit * 3)

    scored = []
    query_words = set(_tokenize_zh_en(query))
    for doc_idx, score in results:
        paper = papers[doc_idx]
        title_tokens = set(_tokenize_zh_en(paper.get("title", "")))
        if query_words & title_tokens:
            score *= 1.3
        paper_with_score = dict(paper)
        paper_with_score["score"] = round(score, 4)
        scored.append(paper_with_score)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
