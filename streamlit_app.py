"""어르신 복지 상담 챗봇 — 올인원(단일 파일) Streamlit 앱.

이 파일 하나에 지식베이스 문서, BM25 검색, LLM 호출, 채팅 UI가 모두 들어 있습니다.
data/ 폴더나 rag/ 폴더가 없어도 작동합니다.

- 저장소에 data/*.md 또는 01_이름.md 형식 문서가 있으면 그것을 사용
- 없으면 파일에 내장된 기본 문서(2026년 노인 복지제도 6종)를 사용

AI 상담 모드 (환경변수):
- GROQ_API_KEY      → Groq Llama 3.3 70B (무료 티어, console.groq.com)
- ANTHROPIC_API_KEY → Claude (console.anthropic.com)
- 둘 다 없으면 검색 모드로 작동
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import requests

# ═══════════════════════════════════════════════════════════════════
# 1. 내장 지식베이스 (data 폴더가 없을 때 사용되는 기본 문서)
# ═══════════════════════════════════════════════════════════════════

EMBEDDED_DOCS = {
    '01_basic_pension.md': "# 기초연금\n\n## 제도 개요\n기초연금은 만 65세 이상 어르신 중 소득인정액이 선정기준액 이하인 분께 매월 연금을 드려 안정적인 노후 생활을 지원하는 제도입니다. 보건복지부가 주관하며, 국민연금 가입 여부와 관계없이 신청할 수 있습니다.\n\n## 지원 대상 (2026년 기준)\n- 만 65세 이상, 대한민국 국적, 국내 거주자\n- 소득인정액이 선정기준액 이하인 경우\n  - 단독가구: 월 소득인정액 247만 원 이하\n  - 부부가구: 월 소득인정액 395만 2천 원 이하\n- 소득인정액 = 소득평가액 + 재산의 소득환산액\n- 근로소득 공제액: 월 116만 원 (2026년 기준, 일하는 어르신의 수급 불이익 방지)\n- 공무원연금, 사학연금, 군인연금, 별정우체국연금 수급자 및 배우자는 원칙적으로 제외\n\n## 지원 금액 (2026년 기준)\n- 기준연금액: 월 최대 34만 9,700원 (2025년 34만 2,510원에서 7,190원 인상)\n- 부부가 모두 받는 경우 부부감액(20%)이 적용될 수 있으며, 저소득층부터 단계적으로 감액 축소가 추진되고 있습니다.\n- 소득 수준에 따라 일부 감액될 수 있습니다.\n\n## 신청 방법\n- 주소지 관할 읍·면·동 행정복지센터(주민센터) 또는 가까운 국민연금공단 지사에서 신청\n- 온라인 신청: 복지로(www.bokjiro.go.kr)\n- 만 65세 생일이 속한 달의 1개월 전부터 신청 가능 (예: 7월생이면 6월 1일부터 신청 가능)\n- 거동이 불편한 경우 국민연금공단의 '찾아뵙는 서비스'(국번 없이 1355) 이용 가능\n\n## 필요 서류\n- 신분증 (주민등록증, 운전면허증 등)\n- 기초연금 지급 신청서 (현장 비치)\n- 소득·재산 신고서, 금융정보 등 제공 동의서\n- 본인 명의 통장 사본\n- 전·월세 계약서 (해당자에 한함)\n\n## 문의처\n- 보건복지상담센터: 국번 없이 129\n- 국민연금공단 콜센터: 국번 없이 1355\n",
    '02_longterm_care.md': '# 노인장기요양보험\n\n## 제도 개요\n노인장기요양보험은 고령이나 노인성 질병(치매, 뇌혈관성 질환, 파킨슨병 등)으로 혼자서 일상생활을 하기 어려운 어르신께 신체활동·가사활동 지원 등의 장기요양급여를 제공하는 사회보험 제도입니다. 국민건강보험공단이 운영합니다.\n\n## 신청 자격\n- 만 65세 이상 어르신, 또는\n- 만 65세 미만이지만 치매·뇌혈관성 질환 등 노인성 질병이 있는 분\n- 소득 수준과 관계없이 건강보험 가입자라면 누구나 신청 가능\n\n## 등급 체계\n장기요양등급은 심신 상태에 따라 6단계로 나뉩니다.\n\n| 등급 | 인정점수 | 상태 |\n|------|---------|------|\n| 1등급 | 95점 이상 | 일상생활에서 전적으로 다른 사람의 도움 필요 |\n| 2등급 | 75점 이상 95점 미만 | 일상생활 전반에 상당 부분 도움 필요 |\n| 3등급 | 60점 이상 75점 미만 | 일상생활에서 부분적으로 도움 필요 |\n| 4등급 | 51점 이상 60점 미만 | 일상생활에서 일정 부분 도움 필요 |\n| 5등급 | 45점 이상 51점 미만 | 치매환자 (신체기능은 비교적 양호) |\n| 인지지원등급 | 45점 미만 | 경증 치매환자 |\n\n## 신청 절차\n1. 신청서 제출: 국민건강보험공단 지사 방문, 온라인(longtermcare.or.kr), 우편·팩스\n2. 방문조사: 신청 후 약 1주일 내 공단 직원이 방문하여 5개 영역 52개 항목 평가\n3. 등급 판정: 신청일로부터 30일 이내 등급판정위원회에서 판정\n4. 서비스 이용: 장기요양인정서 도달일부터 이용 가능\n\n## 급여 종류\n- 재가급여: 방문요양, 방문목욕, 방문간호, 주·야간보호, 단기보호, 복지용구(연 160만 원 별도 한도)\n- 시설급여: 노인요양시설(요양원) 입소 — 원칙적으로 1~2등급 대상\n- 재가급여 월 한도액 (2026년): 1등급 약 251만 원, 2등급 약 233만 원 (등급별 상이, 매년 고시)\n\n## 본인부담금\n- 재가급여: 비용의 15%\n- 시설급여: 비용의 20%\n- 국민기초생활수급자: 무료 (0%)\n- 감경대상자(저소득층 등): 6~9%\n\n## 문의처\n- 국민건강보험공단: 1577-1000\n- 노인장기요양보험 홈페이지: www.longtermcare.or.kr\n',
    '03_care_service.md': '# 노인맞춤돌봄서비스\n\n## 제도 개요\n노인맞춤돌봄서비스는 일상생활 영위가 어려운 취약 어르신께 안전지원, 사회참여, 생활교육, 일상생활 지원 등 맞춤형 돌봄서비스를 제공하여 안정적인 노후 생활을 돕는 제도입니다. 2026년에는 대상자가 57만 6천 명으로 확대되었습니다.\n\n## 지원 대상\n- 만 65세 이상 국민기초생활수급자, 차상위계층, 기초연금수급자 중\n- 독거·조손가구 등 돌봄이 필요한 어르신\n- 신체적 기능 저하, 정신적 어려움(우울, 고독사 위험) 등으로 돌봄이 필요한 경우\n- 유사 중복 서비스(노인장기요양보험 등급자 등) 이용자는 제외\n\n## 서비스 내용\n- 안전지원: 안전·안부 확인(방문·전화), 생활안전점검, 정보제공, 말벗\n- 사회참여: 여가활동, 평생교육 활동, 문화활동 지원\n- 생활교육: 영양·건강 교육, 우울 예방 프로그램\n- 일상생활 지원: 이동 동행(외출, 병원 방문), 가사 지원(청소, 식사 준비)\n- 연계 서비스: 생활지원 물품, 후원 연계\n- 중점돌봄군은 월 20시간 이상, 일반돌봄군은 월 16시간 미만의 직접 서비스 제공\n- 야간 연장돌봄: 인근 센터에서 24시까지 이용 가능 (2026년 확대)\n\n## 신청 방법\n- 주소지 관할 읍·면·동 행정복지센터(주민센터) 방문 신청\n- 본인, 가족, 이웃, 복지 담당 공무원 등이 대리 신청 가능\n- 상시 신청 가능하며, 대상자 선정 조사 후 서비스 시작\n\n## 필요 서류\n- 신분증\n- 노인맞춤돌봄서비스 신청서 (현장 비치)\n- 대리 신청 시 위임장 및 대리인 신분증\n\n## 문의처\n- 주소지 읍·면·동 행정복지센터\n- 보건복지상담센터: 국번 없이 129\n',
    '04_dementia_support.md': '# 치매 관련 지원 (치매안심센터·치매치료관리비)\n\n## 치매안심센터\n전국 시·군·구 보건소에 설치된 치매안심센터에서 치매 관련 통합 서비스를 제공합니다.\n\n### 주요 서비스\n- 치매 조기검진: 만 60세 이상 무료 선별검사, 필요시 진단검사·감별검사 연계\n- 치매환자 등록 및 맞춤형 사례관리\n- 인지강화 프로그램, 치매예방교실 운영\n- 치매환자 쉼터 운영\n- 가족 지원: 가족교실, 자조모임, 심리상담\n- 배회 인식표 보급, 실종 예방 지원\n- 치매안심 재산관리지원서비스: 2026년 시범사업 시작\n\n## 치매치료관리비 지원\n\n### 지원 대상\n- 만 60세 이상 (초로기 치매환자는 예외적으로 60세 미만도 가능)\n- 치매안심센터(보건소)에 치매환자로 등록된 분\n- 치매 진단을 받고 치매치료제를 복용 중인 분\n- 소득 기준: 기준 중위소득 140% 이하 권고\n  - 2026년 기준 1인 가구 약 359만 원, 2인 가구 약 588만 원\n  - 일부 지자체는 소득 기준을 폐지하였으므로 관할 보건소에 확인 필요\n\n### 지원 금액\n- 월 3만 원(연간 36만 원) 한도 내 치매치료제 복용에 따른 약제비와 진료비 본인부담금 지원\n\n### 신청 방법\n- 관할 보건소(치매안심센터)에 신청\n- 필요 서류: 지원신청서, 소득재산조사 동의서, 본인 명의 통장 사본, 최근 1년 이내 발행된 치매약 처방전 또는 약국 영수증, 주민등록등본\n\n## 문의처\n- 치매상담콜센터: 1899-9988 (24시간 365일)\n- 보건복지상담센터: 국번 없이 129\n- 관할 보건소 치매안심센터\n',
    '05_senior_jobs.md': '# 노인일자리 및 사회활동 지원사업\n\n## 제도 개요\n노인일자리 및 사회활동 지원사업은 어르신이 활기차고 건강한 노후를 보낼 수 있도록 다양한 일자리와 사회활동 기회를 제공하는 사업입니다. 2026년에는 전국 115만 2천 개 일자리가 공급되어 전년(109만 8천 개)보다 확대되었습니다.\n\n## 일자리 유형\n\n### 공익활동형\n- 대상: 만 65세 이상 기초연금수급자\n- 내용: 노노케어(취약 어르신 안부 확인), 취약계층 지원, 공공시설 봉사, 경륜전수 활동 등\n- 활동: 월 30시간 내외, 활동비 월 29만 원 수준 (연도별 상이)\n\n### 사회서비스형\n- 대상: 만 65세 이상 (일부 유형 60세 이상)\n- 내용: 보육시설·학교·복지시설 등 사회서비스 제공 지원\n- 활동: 월 60시간, 급여 월 76만 원 수준\n\n### 민간형 (시장형사업단·취업알선형·시니어인턴십·고령자친화기업)\n- 대상: 만 60세 이상\n- 내용: 소규모 매장 운영, 제조·판매, 기업 연계 취업 등\n- 급여: 사업 유형과 근무 형태에 따라 상이\n\n## 신청 방법\n- 모집 시기: 통상 매년 12월경 다음 해 참여자 모집 (상시 모집 유형도 있음)\n- 신청처: 주소지 시니어클럽, 노인복지관, 대한노인회, 읍·면·동 행정복지센터 등 수행기관\n- 온라인: 노인일자리 여기(www.seniorro.or.kr)\n\n## 필요 서류\n- 신분증\n- 참여 신청서 (수행기관 비치)\n- 기초연금 수급 확인 (공익활동형)\n\n## 문의처\n- 노인일자리 상담 대표전화: 1544-3388\n- 한국노인인력개발원: www.kordi.or.kr\n- 노인일자리 여기: www.seniorro.or.kr\n',
    '06_other_benefits.md': '# 어르신 생활 지원 혜택 모음\n\n## 교통 혜택\n- 지하철 무료 이용: 만 65세 이상 어르신은 수도권·부산 등 도시철도 무료 (신분증 또는 어르신 교통카드 발급 후 이용)\n- KTX·새마을호·무궁화호: 만 65세 이상 30% 할인 (KTX·새마을호는 주중에 한함)\n- 항공·여객선: 일부 노선 어르신 할인 제공 (항공사·선사별 상이)\n\n## 통신비 감면\n- 대상: 만 65세 이상 기초연금수급자\n- 내용: 이동통신 요금 최대 월 1만 1천 원(50%) 감면\n- 신청: 통신사 대리점, 국번 없이 1523, 복지로(www.bokjiro.go.kr)\n\n## 문화 혜택\n- 고궁·능원·국공립 박물관·미술관·국공립공원: 만 65세 이상 무료 또는 할인\n- 문화누리카드: 기초생활수급자·차상위계층 대상 연 14만 원 문화·여행·체육 활동비 지원 (연도별 금액 상이)\n\n## 건강 지원\n- 국가건강검진: 만 66세 이후 2년마다 생애전환기 건강진단 포함 일반건강검진\n- 독감(인플루엔자) 예방접종: 만 65세 이상 무료 (매년 10월경 시작, 보건소·지정 의료기관)\n- 폐렴구균 예방접종: 만 65세 이상 무료 (보건소)\n- 노인 안검진 및 개안수술: 만 60세 이상 저소득층 대상 정밀 안검진, 백내장 등 개안수술비 지원\n- 노인 무릎인공관절 수술비 지원: 만 60세 이상 저소득층 대상 한쪽 무릎 기준 최대 120만 원\n\n## 에너지·주거 지원\n- 에너지바우처: 기초생활수급 가구 중 노인 포함 가구 등에 냉난방 비용 지원\n- 주거급여: 소득인정액 기준 충족 시 임차료 지원 또는 자가 수선비 지원\n\n## 경로당·노인복지관\n- 경로당: 만 65세 이상 누구나 이용 가능, 냉난방비·양곡비 지원\n- 노인복지관: 만 60세 이상 이용 가능, 식사·교육·건강·여가 프로그램 제공\n\n## 문의처\n- 보건복지상담센터: 국번 없이 129\n- 복지로: www.bokjiro.go.kr\n- 주소지 읍·면·동 행정복지센터\n',
}

# ═══════════════════════════════════════════════════════════════════
# 2. 문서 로드 + 청킹
# ═══════════════════════════════════════════════════════════════════


@dataclass
class Chunk:
    doc_title: str
    section: str
    text: str
    source: str

    @property
    def full_text(self) -> str:
        return f"{self.doc_title} - {self.section}\n{self.text}"


def _split_markdown(doc_title: str, body: str, source: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    parts = re.split(r"^## +", body, flags=re.MULTILINE)
    preamble = re.sub(r"^# .*$", "", parts[0], flags=re.MULTILINE).strip()
    if preamble:
        chunks.append(Chunk(doc_title, "개요", preamble, source))
    for part in parts[1:]:
        lines = part.splitlines()
        section = lines[0].strip() if lines else "본문"
        text = "\n".join(lines[1:]).strip()
        if text:
            chunks.append(Chunk(doc_title, section, text, source))
    return chunks


def _parse_doc(name: str, body: str) -> list[Chunk]:
    m = re.search(r"^# +(.+)$", body, flags=re.MULTILINE)
    doc_title = m.group(1).strip() if m else Path(name).stem
    return _split_markdown(doc_title, body, name)


def load_chunks() -> list[Chunk]:
    """data/ 폴더에 .md 문서가 있으면 그것을 사용, 없으면 내장 문서 사용.

    → 나중에 문서를 교체하고 싶으면 data 폴더를 만들어 .md 파일을 넣으면 됩니다.
    """
    base = Path(__file__).resolve().parent
    paths = sorted((base / "data").glob("*.md"))
    chunks: list[Chunk] = []
    for p in paths:
        try:
            chunks.extend(_parse_doc(p.name, p.read_text(encoding="utf-8")))
        except Exception:
            continue  # 깨진 파일은 건너뜀
    if not chunks:  # 폴백: 내장 문서
        for name, body in EMBEDDED_DOCS.items():
            chunks.extend(_parse_doc(name, body))
    return chunks


# ═══════════════════════════════════════════════════════════════════
# 3. BM25 검색 (한국어 바이그램 토크나이저)
# ═══════════════════════════════════════════════════════════════════

_word_re = re.compile(r"[가-힣]+|[a-zA-Z]+|[0-9]+")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for word in _word_re.findall(text.lower()):
        tokens.append(word)
        if re.match(r"[가-힣]", word) and len(word) >= 2:
            tokens.extend(word[i : i + 2] for i in range(len(word) - 1))
    return tokens


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self._doc_tokens = [tokenize(c.full_text) for c in chunks]
        self._doc_freqs = [Counter(t) for t in self._doc_tokens]
        self._doc_lens = [len(t) for t in self._doc_tokens]
        self._avg_len = sum(self._doc_lens) / max(len(chunks), 1)
        df: Counter[str] = Counter()
        for freqs in self._doc_freqs:
            df.update(freqs.keys())
        n = len(chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _score(self, q: list[str], i: int) -> float:
        score, freqs, dl = 0.0, self._doc_freqs[i], self._doc_lens[i]
        for term in q:
            if term in freqs:
                f = freqs[term]
                score += self._idf.get(term, 0.0) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * dl / self._avg_len)
                )
        return score

    def search(self, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        scored = [(self.chunks[i], self._score(q, i)) for i in range(len(self.chunks))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scored[:top_k] if s > 0]


# ═══════════════════════════════════════════════════════════════════
# 4. LLM 답변 생성 (Groq 우선 → Claude → 검색 모드 폴백)
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """당신은 노인 복지 전문 상담사입니다. 어르신과 그 가족을 돕습니다.

답변 원칙:
1. 아래 [참고 자료]에 있는 내용만 근거로 답하세요. 자료에 없는 내용은 지어내지 말고,
   "제가 가진 자료에는 없는 내용"이라고 말한 뒤 보건복지상담센터(129) 문의를 안내하세요.
2. 어르신도 이해하기 쉽게 존댓말로, 짧은 문장으로 설명하세요. 전문용어는 풀어서 쓰세요.
3. 금액, 자격 기준, 전화번호 등 숫자는 자료 그대로 정확히 인용하세요.
4. 신청 방법과 문의처를 함께 안내하면 좋습니다.
5. 답변 끝에 참고한 문서 이름을 "참고: ..." 형태로 밝히세요.
6. 제도는 바뀔 수 있으므로, 확정 전에 관할 기관에 확인하시라고 부드럽게 덧붙이세요.
7. 반드시 한국어로만 답변하세요."""


def provider() -> str | None:
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def provider_label() -> str:
    p = provider()
    if p == "groq":
        return f"Groq ({os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')})"
    if p == "anthropic":
        return f"Claude ({os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-5')})"
    return "없음"


def _call_groq(messages: list[dict]) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_anthropic(messages: list[dict]) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5"),
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(b["text"] for b in data["content"] if b["type"] == "text")


def _search_mode_answer(results: list[tuple[Chunk, float]]) -> str:
    parts = ["🔎 질문과 관련된 자료를 찾았습니다:\n"]
    for chunk, _ in results[:3]:
        parts.append(f"📄 **{chunk.doc_title} — {chunk.section}**\n{chunk.text}\n")
    parts.append(
        "---\n💡 GROQ_API_KEY(무료) 또는 ANTHROPIC_API_KEY를 설정하면 "
        "자료를 바탕으로 자연스러운 상담 답변을 생성해 드립니다."
    )
    return "\n".join(parts)


def generate_answer(question, results, history=None) -> dict:
    sources = [{"doc": c.doc_title, "section": c.section} for c, _ in results]
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
    p = provider()
    if p is None:
        return {"answer": _search_mode_answer(results), "mode": "search", "sources": sources}

    context = "\n\n".join(
        f"[자료 {i}] ({c.doc_title} - {c.section})\n{c.text}"
        for i, (c, _) in enumerate(results, 1)
    )
    messages = list(history or [])[-6:]
    messages.append({"role": "user", "content": f"[참고 자료]\n{context}\n\n[질문]\n{question}"})
    try:
        answer = _call_groq(messages) if p == "groq" else _call_anthropic(messages)
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


# ═══════════════════════════════════════════════════════════════════
# 5. Streamlit 채팅 UI
# ═══════════════════════════════════════════════════════════════════

import streamlit as st

st.set_page_config(page_title="어르신 복지 상담 챗봇", page_icon="👵", layout="centered")


@st.cache_resource
def get_retriever() -> BM25Retriever:
    return BM25Retriever(load_chunks())


retriever = get_retriever()
llm_on = provider() is not None

with st.sidebar:
    st.header("ℹ️ 챗봇 정보")
    st.markdown(
        f"""
- **모드**: {"🤖 AI 상담 모드" if llm_on else "🔎 검색 모드 (API 키 없음)"}
- **모델**: {provider_label()}
- **지식베이스**: 청크 {len(retriever.chunks)}개
"""
    )
    if not llm_on:
        st.info(
            "환경변수 `GROQ_API_KEY`(무료) 또는 `ANTHROPIC_API_KEY`를 설정하면 "
            "자료를 바탕으로 자연스러운 상담 답변을 생성합니다."
        )
    st.divider()
    st.caption(
        "⚠️ 답변은 참고용입니다. 복지제도는 수시로 바뀌므로 최종 확인은 "
        "보건복지상담센터(국번 없이 129) 또는 관할 행정복지센터에 문의하세요."
    )
    if st.button("🗑️ 대화 지우기", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("👵 어르신 복지 상담 챗봇")
st.caption("기초연금 · 장기요양보험 · 돌봄서비스 · 치매 지원 · 노인일자리 · 생활 혜택")

if "messages" not in st.session_state:
    st.session_state.messages = []

pending = None
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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👵" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg.get("sources"):
            seen = sorted({s["doc"] for s in msg["sources"]})
            st.caption("📄 참고 문서: " + " · ".join(seen))

user_input = st.chat_input("궁금한 복지 제도를 물어보세요")
question = user_input or pending

if question:
    with st.chat_message("user", avatar="👵"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("답변을 준비하고 있어요…"):
            results = retriever.search(question, top_k=4)
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
    if pending:
        st.rerun()
