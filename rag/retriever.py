"""BM25 기반 한국어 검색기 (외부 라이브러리 불필요).

- 토크나이저: kiwipiepy(형태소 분석기)가 설치되어 있으면 자동 사용,
  없으면 '어절 + 한글 음절 바이그램' 방식으로 동작합니다.
  바이그램 방식은 조사가 붙은 한국어에서도 어간 일치를 잘 잡아냅니다.
  (예: "기초연금을" → 기초, 초연, 연금, 금을 → "기초연금" 문서와 매칭)
- BM25 Okapi를 직접 구현했습니다 (약 40줄).

정확도를 더 높이고 싶다면:
  pip install kiwipiepy   # 형태소 기반 토큰화로 자동 전환
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .loader import Chunk

# ---------------------------------------------------------------------------
# 토크나이저
# ---------------------------------------------------------------------------

try:  # kiwipiepy가 있으면 형태소 분석 사용
    from kiwipiepy import Kiwi

    _kiwi = Kiwi()

    def tokenize(text: str) -> list[str]:
        tokens = []
        for t in _kiwi.tokenize(text):
            # 명사, 동사·형용사 어간, 숫자, 외국어만 색인
            if t.tag[0] in ("N", "V", "S") or t.tag in ("XR", "SL", "SN"):
                tokens.append(t.form.lower())
        return tokens

    TOKENIZER = "kiwi(형태소)"
except ImportError:

    _word_re = re.compile(r"[가-힣]+|[a-zA-Z]+|[0-9]+")

    def tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        for word in _word_re.findall(text.lower()):
            tokens.append(word)
            # 한글 어절은 음절 바이그램 추가 (조사 변형에 강함)
            if re.match(r"[가-힣]", word) and len(word) >= 2:
                tokens.extend(word[i : i + 2] for i in range(len(word) - 1))
        return tokens

    TOKENIZER = "bigram(바이그램)"


# ---------------------------------------------------------------------------
# BM25 Okapi
# ---------------------------------------------------------------------------

class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self._doc_tokens = [tokenize(c.full_text) for c in chunks]
        self._doc_freqs = [Counter(toks) for toks in self._doc_tokens]
        self._doc_lens = [len(toks) for toks in self._doc_tokens]
        self._avg_len = sum(self._doc_lens) / max(len(chunks), 1)
        # 역문서빈도(IDF)
        df: Counter[str] = Counter()
        for freqs in self._doc_freqs:
            df.update(freqs.keys())
        n = len(chunks)
        self._idf = {
            term: math.log(1 + (n - d + 0.5) / (d + 0.5)) for term, d in df.items()
        }

    def _score(self, query_tokens: list[str], idx: int) -> float:
        score = 0.0
        freqs, dl = self._doc_freqs[idx], self._doc_lens[idx]
        for term in query_tokens:
            if term not in freqs:
                continue
            f = freqs[term]
            idf = self._idf.get(term, 0.0)
            score += idf * f * (self.k1 + 1) / (
                f + self.k1 * (1 - self.b + self.b * dl / self._avg_len)
            )
        return score

    def search(self, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        """질문과 관련성 높은 청크를 (청크, 점수) 리스트로 반환."""
        q_tokens = tokenize(query)
        scored = [
            (self.chunks[i], self._score(q_tokens, i)) for i in range(len(self.chunks))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scored[:top_k] if s > 0]
