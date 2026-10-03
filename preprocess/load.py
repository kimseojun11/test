"""문서를 읽어 문자열로 돌려준다. (스텁)

TODO(1단계): 바이트로 읽고 직접 디코딩하도록 바꾼다.
- UTF-8 BOM 은 디코딩 단계에서 제거 (변환 기록에는 넣지 않음)
- read_text() 의 유니버설 뉴라인 변환(\\r\\n → \\n) 을 끄고, 줄바꿈 통일은
  정규화 단계에서 위치를 추적하며 처리
- CP949/EUC-KR 등 UTF-8 이 아닌 파일도 읽을 수 있어야 함 (charset-normalizer)
"""

from pathlib import Path


def load_document(path: str | Path) -> str:
    """경로의 문서를 읽어 문자열로 돌려준다."""
    return Path(path).read_text(encoding="utf-8")
