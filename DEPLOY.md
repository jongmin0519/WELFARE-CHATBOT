# 🚀 Render 배포 가이드 (Streamlit)

Render 무료 플랜으로 챗봇을 인터넷에 공개하는 방법입니다.
소요 시간: 약 10~15분

## 준비물

- GitHub 계정 (https://github.com)
- Render 계정 (https://render.com — GitHub 계정으로 가입 가능)
- (선택) Anthropic API 키 — 없으면 검색 모드로 배포됨

## 1단계. GitHub에 코드 올리기

Render는 GitHub 저장소에서 코드를 가져와 배포합니다.

```bash
cd welfare-chatbot

git init
git add .
git commit -m "노인 복지 상담 RAG 챗봇"

# GitHub에서 새 저장소(welfare-chatbot) 만든 뒤:
git remote add origin https://github.com/내아이디/welfare-chatbot.git
git branch -M main
git push -u origin main
```

> 💡 명령어가 낯설면 GitHub Desktop 앱으로 폴더를 끌어다 놓고 Publish 해도 됩니다.

## 2단계. Render에서 배포

**방법 A — Blueprint (추천, 설정 자동)**

1. https://dashboard.render.com 접속 → 우측 상단 **New +** → **Blueprint**
2. GitHub 계정 연결 후 `welfare-chatbot` 저장소 선택
3. 저장소 루트의 `render.yaml`을 자동으로 읽어 설정을 채워줍니다
4. `ANTHROPIC_API_KEY` 입력란이 보이면 키 입력 (없으면 비워두기) → **Apply**

**방법 B — 수동 설정**

1. **New +** → **Web Service** → 저장소 선택
2. 아래처럼 입력:
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command:
     ```
     streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
     ```
   - Instance Type: `Free`
3. **Environment Variables**에 추가:
   - `PYTHON_VERSION` = `3.11.9`
   - `ANTHROPIC_API_KEY` = `sk-ant-...` (AI 상담 모드를 켤 경우)
4. **Create Web Service** 클릭

## 3단계. 확인

- 빌드가 끝나면(수 분 소요) `https://welfare-chatbot-xxxx.onrender.com` 형태의
  주소가 생깁니다. 접속해서 질문해 보세요.
- 사이드바에 "AI 상담 모드"가 표시되면 API 키가 잘 적용된 것입니다.

## 자주 묻는 것

**Q. 무료 플랜의 제한은?**
15분간 접속이 없으면 서버가 잠들고, 다음 접속 시 깨어나는 데 30초~1분쯤
걸립니다. 데모·프로토타입 용도로는 충분합니다.

**Q. API 키를 코드에 넣으면 안 되나요?**
안 됩니다. GitHub에 올라간 키는 유출된 것과 같습니다. 반드시 Render
대시보드의 Environment Variables로만 설정하세요.

**Q. 문서를 수정하면?**
`data/` 폴더를 수정하고 `git push`하면 Render가 자동으로 재배포합니다.

**Q. 로컬에서 Streamlit 버전을 실행하려면?**
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**Q. Flask 버전(app.py)은 뭔가요?**
같은 챗봇의 의존성 최소 버전입니다. `python app.py`로 실행하며,
Streamlit 없이 돌리고 싶을 때 사용하세요. Render 배포는 Streamlit
버전(streamlit_app.py) 기준으로 설정되어 있습니다.
