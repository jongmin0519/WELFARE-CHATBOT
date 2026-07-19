"""터미널에서 챗봇을 바로 테스트하는 스크립트.

사용법:
    python cli.py                     # 대화형 모드
    python cli.py "기초연금 얼마 받아요?"   # 단발 질문
"""

import sys
from pathlib import Path

from rag.loader import load_chunks
from rag.retriever import BM25Retriever, TOKENIZER
from rag.generator import generate_answer, api_key, provider_label

BASE = Path(__file__).resolve().parent


def main() -> None:
    chunks = load_chunks(BASE / "data")
    retriever = BM25Retriever(chunks)
    mode = f"AI 상담 모드 ({provider_label()})" if api_key() else "검색 모드 (API 키 없음)"
    print(f"📚 문서 {len(chunks)}개 청크 로드 완료 | 토크나이저: {TOKENIZER} | {mode}")

    def ask(q: str) -> None:
        results = retriever.search(q)
        out = generate_answer(q, results)
        print("\n" + out["answer"] + "\n")

    if len(sys.argv) > 1:
        ask(" ".join(sys.argv[1:]))
        return

    print("질문을 입력하세요. (종료: quit)\n")
    while True:
        try:
            q = input("👵 질문 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in {"quit", "exit", "종료"}:
            break
        ask(q)


if __name__ == "__main__":
    main()
