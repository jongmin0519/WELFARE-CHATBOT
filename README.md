# 👵 어르신 복지 상담 챗봇

> 노인 복지제도를 쉽게 안내하는 **RAG(검색 증강 생성)** 기반 상담 챗봇

**🔗 라이브 데모: [어르신 복지 상담 챗봇](https://welfare-chatbot-nuxk.onrender.com/)**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Claude](https://img.shields.io/badge/Claude_API-Anthropic-D97757)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)

기초연금 · 노인장기요양보험 · 노인맞춤돌봄서비스 · 치매 지원 · 노인일자리 · 생활 혜택 등
어르신과 가족들이 궁금해하는 복지제도를 대화로 물어보면, 지식베이스 문서에서 근거를
찾아 쉬운 말로 답변합니다.

> ⏳ 무료 서버 특성상 첫 접속 시 서버가 깨어나는 데 30초~1분 정도 걸릴 수 있습니다.

## ✨ 주요 기능

- **문서 근거 기반 답변** — 답변은 `data/` 폴더의 복지제도 문서를 검색한 결과만을
  근거로 생성되며, 참고한 문서를 함께 표시합니다 (환각 최소화)
- **자료에 없으면 모른다고 답변** — 지식베이스 밖의 질문은 지어내지 않고
  보건복지상담센터(129) 문의를 안내합니다
- **의존성 최소 설계** — 벡터 DB 없이 BM25 검색을 직접 구현, 한국어 토크나이저 내장
  (형태소 분석기 `kiwipiepy` 설치 시 자동 전환)
- **2가지 모드** — `ANTHROPIC_API_KEY`가 있으면 AI 상담 모드, 없으면 관련 자료를
  그대로 보여주는 검색 모드로 자동 폴백
- **어르신 친화 UI** — 큰 글씨, 예시 질문 버튼, 쉬운 존댓말 답변

## 🧠 동작 원리 (RAG 파이프라인)

```
질문 입력
   │
   ▼
[1] 청킹     data/*.md 문서를 '## 소제목' 단위로 분할          (rag/loader.py)
   │
   ▼
[2] 검색     BM25 + 한국어 바이그램/형태소 토크나이저로          (rag/retriever.py)
             질문과 관련성 높은 청크 상위 4개 선별
   │
   ▼
[3] 생성     검색된 자료를 근거로 Claude API가 상담 답변 생성    (rag/generator.py)
             (키 없으면 검색 결과를 정리해서 표시)
```

## 🚀 로컬 실행

```bash
git clone https://github.com/<your-id>/welfare-chatbot.git
cd welfare-chatbot

pip install -r requirements.txt

# Streamlit 버전 (권장)
streamlit run streamlit_app.py

# 또는 Flask 버전 (의존성 최소) → http://localhost:8501
python app.py

# 또는 터미널에서 바로
python cli.py "기초연금은 얼마나 받을 수 있나요?"
```

### AI 상담 모드 켜기

두 가지 LLM 제공자를 지원합니다. 키를 환경변수로 설정하면 자동으로 AI 상담 모드가 켜집니다.

| 우선순위 | 제공자 | 환경변수 | 키 발급 | 비고 |
|---------|--------|---------|---------|------|
| 1 | **Groq** (Llama 3.3 70B) | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | **무료 티어 제공** |
| 2 | **Claude** (Anthropic) | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | 유료 (크레딧 충전) |

```bash
export GROQ_API_KEY=gsk_...           # macOS/Linux
streamlit run streamlit_app.py
```

모델 변경: `GROQ_MODEL` (기본 `llama-3.3-70b-versatile`) 또는
`CLAUDE_MODEL` (기본 `claude-sonnet-4-5`) 환경변수

## ☁️ 배포 (Render)

이 저장소에는 [Render Blueprint](render.yaml)가 포함되어 있어 클릭 몇 번으로
배포할 수 있습니다. 자세한 단계는 **[DEPLOY.md](DEPLOY.md)** 참고.

1. 저장소를 GitHub에 push
2. [Render 대시보드](https://dashboard.render.com) → **New +** → **Blueprint** → 저장소 선택
3. `ANTHROPIC_API_KEY` 환경변수 입력 → **Apply**

> 🔑 API 키는 절대 코드에 넣지 말고 Render 대시보드의 환경변수로만 설정하세요.

## 📁 프로젝트 구조

```
welfare-chatbot/
├── streamlit_app.py    # Streamlit 채팅 UI (배포 기준)
├── app.py              # Flask 버전 (의존성 최소)
├── cli.py              # 터미널 테스트용
├── rag/
│   ├── loader.py       # 문서 로드 + 섹션 단위 청킹
│   ├── retriever.py    # BM25 검색 (직접 구현, 외부 라이브러리 불필요)
│   └── generator.py    # Claude API 호출 + 검색 모드 폴백
├── data/               # 📚 지식베이스 (여기만 바꾸면 다른 도메인 챗봇이 됨)
│   ├── 01_basic_pension.md      # 기초연금
│   ├── 02_longterm_care.md      # 노인장기요양보험
│   ├── 03_care_service.md       # 노인맞춤돌봄서비스
│   ├── 04_dementia_support.md   # 치매 지원
│   ├── 05_senior_jobs.md        # 노인일자리
│   └── 06_other_benefits.md     # 기타 생활 혜택
├── render.yaml         # Render 배포 설정 (Blueprint)
├── DEPLOY.md           # 배포 가이드
└── requirements.txt
```

## 📝 지식베이스 교체·확장

`data/` 폴더의 `.md` 파일이 지식베이스의 전부입니다.

- `# 문서제목` + `## 소제목` 구조의 마크다운을 넣으면 소제목 단위로 청킹됩니다
- 파일을 추가·수정하고 `git push`하면 Render가 자동 재배포합니다
- PDF·한글(HWP) 자료는 텍스트로 변환 후 `.md`로 저장하세요
- 복지가 아닌 다른 도메인 문서를 넣으면 그대로 해당 도메인 챗봇이 됩니다

## 🛠️ 개선 아이디어

- [ ] `kiwipiepy` 형태소 분석 적용으로 검색 정확도 향상
- [ ] 임베딩 기반 벡터 검색 추가 (BM25와 하이브리드)
- [ ] 예상 질문 세트로 검색 품질 자동 평가
- [ ] 음성 입력/출력 (어르신 접근성)

## ⚠️ 주의사항

- 샘플 문서는 **2026년 7월 공공 자료** 기준으로 작성했으나, 복지제도는 수시로
  변경됩니다. 실서비스 활용 전 반드시 공식 자료로 검증하세요.
- 챗봇의 답변은 참고용입니다. 최종 확인은 **보건복지상담센터 (국번 없이 129)**
  또는 관할 행정복지센터에 문의하세요.

## 📄 라이선스

MIT
