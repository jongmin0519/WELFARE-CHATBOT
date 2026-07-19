# 👵 어르신 복지 상담 챗봇 (RAG)

노인 복지제도(기초연금, 장기요양보험, 돌봄서비스, 치매 지원, 노인일자리 등)를 안내하는
RAG(검색 증강 생성) 기반 상담 챗봇입니다.

- **검색(Retrieval)**: `data/` 폴더의 문서를 BM25 알고리즘으로 검색 (외부 라이브러리 불필요)
- **생성(Generation)**: 검색된 자료를 근거로 Claude API가 상담 답변 생성
- **폴백 모드**: API 키가 없어도 관련 자료를 찾아서 보여주는 '검색 모드'로 작동

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 실행 (Streamlit 버전 — 권장)
streamlit run streamlit_app.py

#    또는 의존성 최소 Flask 버전
python app.py    # → http://localhost:8501
```

**🚀 인터넷에 공개(Render 배포)**: [DEPLOY.md](DEPLOY.md) 참고 — GitHub에 올리고
Render Blueprint로 10분 안에 배포할 수 있습니다.

터미널에서 바로 테스트할 수도 있습니다:

```bash
python cli.py "기초연금은 얼마나 받을 수 있나요?"
python cli.py          # 대화형 모드
```

## AI 상담 모드 켜기 (Claude API 키)

API 키 없이도 '검색 모드'로 작동하지만, 키를 설정하면 자료를 바탕으로
자연스러운 상담 답변을 생성합니다.

1. https://console.anthropic.com 에서 계정 생성
2. 좌측 **API Keys** 메뉴 → **Create Key** 로 키 발급 (`sk-ant-...` 형태)
3. **Billing**에서 결제 수단 등록 (사용한 만큼 과금, 소액 크레딧 충전 방식)
4. 환경변수로 설정 후 실행:

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-여기에-키-입력
python app.py

# Windows (cmd)
set ANTHROPIC_API_KEY=sk-ant-여기에-키-입력
python app.py

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-여기에-키-입력"
python app.py
```

모델을 바꾸려면 `CLAUDE_MODEL` 환경변수를 설정하세요.
(기본값: `claude-sonnet-4-5`, 저렴한 옵션: `claude-haiku-4-5`)

## 내 문서로 지식베이스 교체하기

`data/` 폴더의 `.md` 파일이 지식베이스 전부입니다. 현재 들어 있는 것은
2026년 공공 자료 기반의 **샘플 문서**이며, 자유롭게 교체·추가하세요.

- **추가**: `data/`에 `.md` 또는 `.txt` 파일을 넣고 서버 재시작
- **형식**: 마크다운 권장. `# 문서제목` + `## 소제목` 구조로 쓰면
  소제목 단위로 청크가 만들어져 검색 정확도가 좋아집니다
- **PDF/한글(HWP) 문서**: 텍스트를 추출해 `.md`로 변환 후 넣으세요
  (PDF는 `pymupdf`, HWP는 한컴오피스의 '텍스트로 저장' 기능 활용)

```
data/
├── 기초연금.md
├── 노인장기요양보험.md
├── 노인맞춤돌봄서비스.md
├── 치매지원.md
├── 노인일자리.md
└── 기타혜택.md
```

## 프로젝트 구조

```
welfare-chatbot/
├── streamlit_app.py    # Streamlit 채팅 UI (Render 배포 기준)
├── app.py              # Flask 버전 (의존성 최소)
├── cli.py              # 터미널 테스트용
├── render.yaml         # Render 배포 설정 (Blueprint)
├── DEPLOY.md           # Render 배포 가이드
├── rag/
│   ├── loader.py       # 문서 로드 + 섹션 단위 청킹
│   ├── retriever.py    # BM25 검색 (한국어 바이그램 토크나이저 내장)
│   └── generator.py    # Claude API 호출 + 검색 모드 폴백
├── data/               # 지식베이스 (여기만 바꾸면 다른 도메인 챗봇이 됨)
└── requirements.txt
```

## 검색 정확도 높이기 (선택)

기본 토크나이저는 한글 음절 바이그램 방식으로, 별도 설치 없이 꽤 잘 작동합니다.
형태소 분석기를 설치하면 자동으로 전환되어 정확도가 더 올라갑니다:

```bash
pip install kiwipiepy
```

더 확장하고 싶다면:

- **벡터 검색(임베딩)**: `sentence-transformers`의 한국어 모델
  (`jhgan/ko-sroberta-multitask`)로 의미 기반 검색 추가 → BM25와 하이브리드
- **대화 요약**: 긴 상담 대화를 요약해 맥락 유지
- **평가**: 예상 질문 목록을 만들어 검색 상위 결과가 맞는지 주기적으로 점검

## 주의사항

- 샘플 문서는 2026년 7월 기준 공공 자료를 참고해 작성했지만, 복지제도는
  수시로 바뀝니다. **실서비스에 쓰려면 반드시 공식 자료로 검증·교체하세요.**
- 챗봇 답변은 참고용이며, 최종 확인은 보건복지상담센터(129)나 관할
  행정복지센터에 안내하도록 시스템 프롬프트에 반영되어 있습니다.
