"""답변 생성기.

- ANTHROPIC_API_KEY 환경변수가 설정되어 있으면 Claude API로 상담 답변을 생성합니다.
  (별도 SDK 없이 requests로 직접 호출)
- API 키가 없으면 '검색 모드'로 폴백: 관련 문서 내용을 정리해서 보여줍니다.

모델 변경: 환경변수 CLAUDE_MODEL (기본값: claude-sonnet-4-5)
"""

from __future__ import annotations

import os

import requests

from .loader import Chunk

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")

SYSTEM_PROMPT = """당신은 노인 복지 전문 상담사입니다. 어르신과 그 가족을 돕습니다.

답변 원칙:
1. 아래 [참고 자료]에 있는 내용만 근거로 답하세요. 자료에 없는 내용은 지어내지 말고,
   "제가 가진 자료에는 없는 내용"이라고 말한 뒤 보건복지상담센터(129) 문의를 안내하세요.
2. 어르신도 이해하기 쉽게 존댓말로, 짧은 문장으로 설명하세요. 전문용어는 풀어서 쓰세요.
3. 금액, 자격 기준, 전화번호 등 숫자는 자료 그대로 정확히 인용하세요.
4. 신청 방법과 문의처를 함께 안내하면 좋습니다.
5. 답변 끝에 참고한 문서 이름을 "참고: ..." 형태로 밝히세요.
6. 제도는 바뀔 수 있으므로, 확정 전에 관할 기관에 확인하시라고 부드럽게 덧붙이세요."""


def _build_context(results: list[tuple[Chunk, float]]) -> str:
    blocks = []
    for i, (chunk, _score) in enumerate(results, 1):
        blocks.append(f"[자료 {i}] ({chunk.doc_title} - {chunk.section})\n{chunk.text}")
    return "\n\n".join(blocks)


def api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or None


def generate_answer(
    question: str,
    results: list[tuple[Chunk, float]],
    history: list[dict] | None = None,
) -> dict:
    """질문 + 검색 결과로 답변 생성.

    반환: {"answer": str, "mode": "llm" | "search", "sources": [...]}
    history: [{"role": "user"|"assistant", "content": str}, ...] (이전 대화, 선택)
    """
    sources = [
        {"doc": c.doc_title, "section": c.section, "file": c.source}
        for c, _ in results
    ]

    if not results:
        return {
            "answer": (
                "죄송합니다. 질문과 관련된 내용을 자료에서 찾지 못했습니다.\n\n"
                "다른 표현으로 다시 질문해 보시거나, 보건복지상담센터 "
                "(국번 없이 129)로 문의해 보세요."
            ),
            "mode": "search",
            "sources": [],
        }

    key = api_key()
    if not key:
        return {"answer": _search_mode_answer(results), "mode": "search", "sources": sources}

    context = _build_context(results)
    user_content = f"[참고 자료]\n{context}\n\n[질문]\n{question}"
    messages = list(history or [])[-6:]  # 최근 3턴만 유지
    messages.append({"role": "user", "content": user_content})

    try:
        resp = requests.post(
            API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": DEFAULT_MODEL,
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        return {"answer": answer, "mode": "llm", "sources": sources}
    except requests.RequestException as e:
        detail = ""
        if getattr(e, "response", None) is not None:
            detail = f" (HTTP {e.response.status_code})"
        return {
            "answer": (
                f"⚠️ AI 답변 생성 중 오류가 발생했습니다{detail}. "
                "아래는 질문과 관련된 자료입니다.\n\n" + _search_mode_answer(results)
            ),
            "mode": "search",
            "sources": sources,
        }


def _search_mode_answer(results: list[tuple[Chunk, float]]) -> str:
    """API 키가 없을 때: 검색된 자료를 그대로 정리해서 보여주는 폴백."""
    parts = ["🔎 질문과 관련된 자료를 찾았습니다:\n"]
    for chunk, _ in results[:3]:
        parts.append(f"📄 **{chunk.doc_title} — {chunk.section}**\n{chunk.text}\n")
    parts.append(
        "---\n💡 ANTHROPIC_API_KEY를 설정하면 자료를 바탕으로 "
        "자연스러운 상담 답변을 생성해 드립니다. (README 참고)"
    )
    return "\n".join(parts)
