"""노인 복지 상담 챗봇 — Streamlit 버전.

로컬 실행:
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Render 배포: DEPLOY.md 참고
AI 상담 모드: 환경변수 ANTHROPIC_API_KEY 설정 (Render에서는 대시보드 Environment 탭)
"""

from pathlib import Path

import streamlit as st

from rag.loader import load_chunks
from rag.retriever import BM25Retriever, TOKENIZER
from rag.generator import generate_answer, api_key

BASE = Path(__file__).resolve().parent

st.set_page_config(
    page_title="어르신 복지 상담 챗봇",
    page_icon="👵",
    layout="centered",
)


@st.cache_resource
def get_retriever() -> BM25Retriever:
    """지식베이스 색인은 서버 기동 시 1회만 수행 (캐시)."""
    return BM25Retriever(load_chunks(BASE / "data"))


retriever = get_retriever()
llm_on = bool(api_key())

# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.header("ℹ️ 챗봇 정보")
    st.markdown(
        f"""
- **모드**: {"🤖 AI 상담 모드" if llm_on else "🔎 검색 모드 (API 키 없음)"}
- **지식베이스**: 청크 {len(retriever.chunks)}개
- **토크나이저**: {TOKENIZER}
"""
    )
    if not llm_on:
        st.info(
            "환경변수 `ANTHROPIC_API_KEY`를 설정하면 자료를 바탕으로 "
            "자연스러운 상담 답변을 생성합니다."
        )
    st.divider()
    st.caption(
        "⚠️ 답변은 참고용입니다. 복지제도는 수시로 바뀌므로 최종 확인은 "
        "보건복지상담센터(국번 없이 129) 또는 관할 행정복지센터에 문의하세요."
    )
    if st.button("🗑️ 대화 지우기", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── 본문 ─────────────────────────────────────────────────
st.title("👵 어르신 복지 상담 챗봇")
st.caption("기초연금 · 장기요양보험 · 돌봄서비스 · 치매 지원 · 노인일자리 · 생활 혜택")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 예시 질문 버튼 (대화 시작 전에만 표시)
pending: str | None = None
if not st.session_state.messages:
    st.markdown("**이런 것을 물어보실 수 있어요:**")
    samples = [
        "기초연금은 얼마나 받을 수 있나요?",
        "장기요양등급은 어떻게 신청하나요?",
        "치매 치료비 지원이 있나요?",
        "노인 일자리는 어디서 신청해요?",
        "65세 이상 교통 혜택 알려주세요",
    ]
    cols = st.columns(2)
    for i, q in enumerate(samples):
        if cols[i % 2].button(q, use_container_width=True, key=f"sample_{i}"):
            pending = q

# 지난 대화 렌더링
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👵" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg.get("sources"):
            seen = sorted({s["doc"] for s in msg["sources"]})
            st.caption("📄 참고 문서: " + " · ".join(seen))

# 입력 처리
user_input = st.chat_input("궁금한 복지 제도를 물어보세요")
question = user_input or pending

if question:
    with st.chat_message("user", avatar="👵"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("답변을 준비하고 있어요…"):
            results = retriever.search(question, top_k=4)
            # 이전 대화 맥락 (최근 3턴)
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[-6:]
            ]
            out = generate_answer(question, results, history=history)
        st.markdown(out["answer"])
        if out["sources"]:
            seen = sorted({s["doc"] for s in out["sources"]})
            st.caption("📄 참고 문서: " + " · ".join(seen))

    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(
        {"role": "assistant", "content": out["answer"], "sources": out["sources"]}
    )
    if pending:  # 버튼으로 시작한 경우 버튼 영역을 지우기 위해 새로고침
        st.rerun()
