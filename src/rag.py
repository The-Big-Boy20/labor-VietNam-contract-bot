"""Truy hồi điều luật (RAG retriever).

Hỗ trợ hai backend embedding, có cùng giao diện:
- "st"   : sentence-transformers với embedding tiếng Việt (bản triển khai chính).
- "tfidf": TF-IDF (sklearn), dùng khi không tải được mô hình embedding.
"""
import json
import numpy as np
from pathlib import Path

ROMAN_TO_ZONE = {"I": "vung_1", "II": "vung_2", "III": "vung_3", "IV": "vung_4"}
MAX_CHARS = 1600  # độ dài tối đa của nội dung điều luật trả về, đủ để không cắt mất khoản quan trọng


class Retriever:
    def __init__(self, backend="auto", model_name="bkai-foundation-models/vietnamese-bi-encoder"):
        self.backend = backend
        self.model_name = model_name
        self.model = None
        self.vectorizer = None
        self.matrix = None
        self.chunks = []
        if backend in ("auto", "st"):
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
                self.backend = "st"
            except Exception:
                if backend == "st":
                    raise
                self.backend = "tfidf"

    def _embed(self, texts):
        if self.backend == "st":
            return np.asarray(self.model.encode(texts, normalize_embeddings=True))
        from sklearn.feature_extraction.text import TfidfVectorizer
        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            return self.vectorizer.fit_transform(texts)
        return self.vectorizer.transform(texts)

    def build(self, chunks_path):
        self.chunks = json.loads(Path(chunks_path).read_text(encoding="utf-8"))
        texts = [f"{c['article_title']}. {c['text']}" for c in self.chunks]
        self.matrix = self._embed(texts)
        return self

    def search(self, query, k=3, doc_filter=None):
        qv = self._embed([query])
        if self.backend == "st":
            scores = self.matrix @ qv[0]
        else:
            from sklearn.metrics.pairwise import cosine_similarity
            scores = cosine_similarity(qv, self.matrix)[0]
        results = []
        for i in np.argsort(-scores):
            c = self.chunks[i]
            if doc_filter and doc_filter not in c["doc_number"]:
                continue
            results.append({
                "score": float(scores[i]),
                "doc": c["doc_number"],
                "dieu": c["article_num"],
                "tieu_de": c["article_title"],
                "text": c["text"][:MAX_CHARS],
            })
            if len(results) >= k:
                break
        return results
