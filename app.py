"""노인 복지 상담 챗봇 — Flask 웹 앱.

실행:
    python app.py
    → 브라우저에서 http://localhost:8501 접속

AI 상담 답변을 받으려면 실행 전에 API 키를 설정하세요:
    export ANTHROPIC_API_KEY=sk-ant-...   (macOS/Linux)
    set ANTHROPIC_API_KEY=sk-ant-...      (Windows cmd)
"""

from pathlib import Path

from flask import Flask, jsonify, request

from rag.loader import load_chunks
from rag.retriever import BM25Retriever, TOKENIZER
from rag.generator import generate_answer, api_key

BASE = Path(__file__).resolve().parent
app = Flask(__name__)

# 서버 시작 시 지식베이스 색인 (문서 수정 후엔 서버 재시작)
chunks = load_chunks(BASE / "data")
retriever = BM25Retriever(chunks)
print(f"📚 청크 {len(chunks)}개 색인 완료 | 토크나이저: {TOKENIZER}")


@app.get("/")
def index():
    return PAGE_HTML


@app.get("/api/status")
def status():
    return jsonify({
        "chunks": len(chunks),
        "tokenizer": TOKENIZER,
        "llm": bool(api_key()),
    })


@app.post("/api/chat")
def chat():
    payload = request.get_json(force=True)
    question = (payload.get("message") or "").strip()
    history = payload.get("history") or []
    if not question:
        return jsonify({"error": "질문이 비어 있습니다."}), 400
    results = retriever.search(question, top_k=4)
    out = generate_answer(question, results, history=history)
    return jsonify(out)


PAGE_HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>어르신 복지 상담 챗봇</title>
<style>
  :root {
    --bg: #f4f6f8; --card: #ffffff; --accent: #1a6b54; --accent-light: #e4f2ed;
    --text: #222; --muted: #667;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
    background: var(--bg); color: var(--text);
    display: flex; flex-direction: column; height: 100vh;
  }
  header {
    background: var(--accent); color: #fff; padding: 16px 24px;
    display: flex; align-items: center; gap: 12px;
  }
  header h1 { font-size: 22px; }
  header .badge {
    margin-left: auto; font-size: 13px; background: rgba(255,255,255,.2);
    padding: 4px 10px; border-radius: 999px;
  }
  #chat {
    flex: 1; overflow-y: auto; padding: 24px;
    max-width: 860px; width: 100%; margin: 0 auto;
  }
  .msg { display: flex; margin-bottom: 16px; }
  .msg.user { justify-content: flex-end; }
  .bubble {
    max-width: 78%; padding: 14px 18px; border-radius: 16px;
    font-size: 17px; line-height: 1.65; white-space: pre-wrap; word-break: break-word;
  }
  .user .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 4px; }
  .bot .bubble { background: var(--card); border: 1px solid #e0e4e8; border-bottom-left-radius: 4px; }
  .bot .bubble b { color: var(--accent); }
  .sources { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
  .source-chip {
    font-size: 13px; background: var(--accent-light); color: var(--accent);
    padding: 3px 10px; border-radius: 999px;
  }
  .suggestions {
    max-width: 860px; margin: 0 auto; padding: 0 24px 8px;
    display: flex; flex-wrap: wrap; gap: 8px; width: 100%;
  }
  .suggestions button {
    font-size: 15px; padding: 8px 14px; border-radius: 999px;
    border: 1px solid var(--accent); background: #fff; color: var(--accent);
    cursor: pointer;
  }
  .suggestions button:hover { background: var(--accent-light); }
  footer {
    padding: 12px 24px 20px; background: var(--bg);
  }
  .input-row {
    max-width: 860px; margin: 0 auto; display: flex; gap: 10px;
  }
  #input {
    flex: 1; font-size: 17px; padding: 14px 16px;
    border: 2px solid #cfd6dd; border-radius: 12px; outline: none;
  }
  #input:focus { border-color: var(--accent); }
  #send {
    font-size: 17px; padding: 0 26px; border: none; border-radius: 12px;
    background: var(--accent); color: #fff; cursor: pointer;
  }
  #send:disabled { opacity: .5; cursor: default; }
  .typing { color: var(--muted); font-size: 15px; }
</style>
</head>
<body>
<header>
  <h1>👵 어르신 복지 상담 챗봇</h1>
  <span class="badge" id="mode-badge">준비 중...</span>
</header>

<div id="chat"></div>

<div class="suggestions" id="suggestions">
  <button>기초연금은 얼마나 받을 수 있나요?</button>
  <button>장기요양등급은 어떻게 신청하나요?</button>
  <button>치매 치료비 지원이 있나요?</button>
  <button>노인 일자리는 어디서 신청해요?</button>
  <button>65세 이상 교통 혜택 알려주세요</button>
</div>

<footer>
  <div class="input-row">
    <input id="input" placeholder="궁금한 복지 제도를 물어보세요" autocomplete="off">
    <button id="send">보내기</button>
  </div>
</footer>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const send = document.getElementById('send');
const history = [];  // {role, content} — 서버로 보내는 대화 맥락

fetch('/api/status').then(r => r.json()).then(s => {
  document.getElementById('mode-badge').textContent =
    s.llm ? 'AI 상담 모드' : '검색 모드 (API 키 없음)';
});

function addMessage(role, text, sources) {
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  // 간단한 마크다운 볼드 처리
  bubble.innerHTML = escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  if (sources && sources.length) {
    const div = document.createElement('div');
    div.className = 'sources';
    const seen = new Set();
    sources.forEach(s => {
      if (seen.has(s.doc)) return; seen.add(s.doc);
      const chip = document.createElement('span');
      chip.className = 'source-chip';
      chip.textContent = '📄 ' + s.doc;
      div.appendChild(chip);
    });
    bubble.appendChild(div);
  }
  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function ask(question) {
  if (!question.trim()) return;
  addMessage('user', question);
  input.value = '';
  send.disabled = true;
  const typing = addMessage('bot', '');
  typing.innerHTML = '<span class="typing">답변을 준비하고 있어요…</span>';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: question, history: history})
    });
    const data = await res.json();
    typing.parentElement.remove();
    addMessage('bot', data.answer, data.sources);
    history.push({role: 'user', content: question});
    history.push({role: 'assistant', content: data.answer});
    if (history.length > 6) history.splice(0, history.length - 6);
  } catch (e) {
    typing.parentElement.remove();
    addMessage('bot', '⚠️ 서버와 통신 중 오류가 발생했습니다. 다시 시도해 주세요.');
  }
  send.disabled = false;
  input.focus();
}

send.onclick = () => ask(input.value);
input.onkeydown = e => { if (e.key === 'Enter') ask(input.value); };
document.getElementById('suggestions').onclick = e => {
  if (e.target.tagName === 'BUTTON') ask(e.target.textContent);
};

addMessage('bot',
  '안녕하세요! 어르신 복지 상담 챗봇입니다. 😊\n' +
  '기초연금, 장기요양보험, 돌봄서비스, 치매 지원, 노인 일자리 등 ' +
  '궁금한 것을 편하게 물어보세요.\n아래 버튼을 눌러 보셔도 됩니다.');
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
