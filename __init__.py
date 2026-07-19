"""지식베이스 문서 로더.

data/ 폴더의 마크다운(.md) 문서를 읽어 '## ' 소제목 단위로 청크(chunk)를 만듭니다.
각 청크에는 문서 제목과 섹션 제목이 함께 붙어 검색 정확도를 높입니다.

새 문서를 추가하려면 data/ 폴더에 .md 파일을 넣기만 하면 됩니다.
(txt 파일도 지원: 빈 줄 2개 기준으로 단락 청킹)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    doc_title: str    # 문서 제목 (예: 기초연금)
    section: str      # 섹션 제목 (예: 지원 대상)
    text: str         # 섹션 본문
    source: str       # 파일명

    @property
    def full_text(self) -> str:
        """검색·생성에 쓰이는 전체 텍스트 (제목 포함)."""
        return f"{self.doc_title} - {self.section}\n{self.text}"


def _split_markdown(doc_title: str, body: str, source: str) -> list[Chunk]:
    """'## ' 헤더 기준으로 마크다운을 섹션 청크로 분할."""
    chunks: list[Chunk] = []
    # 문서 최상단 제목(# ...) 아래 ~ 첫 '## ' 전까지의 서문도 하나의 청크로
    parts = re.split(r"^## +", body, flags=re.MULTILINE)
    preamble = parts[0]
    # 서문에서 '# 제목' 줄 제거
    preamble = re.sub(r"^# .*$", "", preamble, flags=re.MULTILINE).strip()
    if preamble:
        chunks.append(Chunk(doc_title, "개요", preamble, source))

    for part in parts[1:]:
        lines = part.splitlines()
        section = lines[0].strip() if lines else "본문"
        text = "\n".join(lines[1:]).strip()
        if text:
            chunks.append(Chunk(doc_title, section, text, source))
    return chunks


def _split_plaintext(doc_title: str, body: str, source: str) -> list[Chunk]:
    """일반 텍스트는 빈 줄 2개(단락) 기준으로 분할하되 너무 짧으면 합침."""
    chunks: list[Chunk] = []
    paragraphs = re.split(r"\n\s*\n", body)
    buf = ""
    idx = 1
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        buf = f"{buf}\n\n{p}".strip() if buf else p
        if len(buf) >= 300:  # 최소 청크 길이
            chunks.append(Chunk(doc_title, f"단락 {idx}", buf, source))
            idx += 1
            buf = ""
    if buf:
        chunks.append(Chunk(doc_title, f"단락 {idx}", buf, source))
    return chunks


def load_chunks(data_dir: str | Path = "data") -> list[Chunk]:
    """data 폴더의 모든 문서를 청크 리스트로 로드."""
    data_dir = Path(data_dir)
    chunks: list[Chunk] = []
    for path in sorted(data_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        body = path.read_text(encoding="utf-8")
        # 문서 제목: 첫 '# ' 헤더가 있으면 그걸, 없으면 파일명
        m = re.search(r"^# +(.+)$", body, flags=re.MULTILINE)
        doc_title = m.group(1).strip() if m else path.stem
        if path.suffix.lower() == ".md":
            chunks.extend(_split_markdown(doc_title, body, path.name))
        else:
            chunks.extend(_split_plaintext(doc_title, body, path.name))
    return chunks


if __name__ == "__main__":
    for c in load_chunks(Path(__file__).resolve().parent.parent / "data"):
        print(f"[{c.source}] {c.doc_title} / {c.section} ({len(c.text)}자)")
