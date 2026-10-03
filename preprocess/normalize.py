"""정규화: 보이지 않는 문자 제거, 홈글리프 치환, 인코딩 복원 등. (스텁)

TODO(1단계): 처리 순서 고정 — 포맷 파싱 → 유니코드 정규화 → 홈글리프 → 인코딩 복원.
문서 단위로 한 번에 처리하고, 위치 대응표(offset_map)를 갱신해야 한다.
지금은 입력을 그대로 돌려준다.
"""

VERSION = "stub-0"


def normalize_text(raw: str, fmt: str | None = None) -> str:
    """raw 를 정규화한 텍스트로 바꾼다. fmt 는 "html"/"md"/None(txt).

    TODO(1단계): (정리본, offset_map, decoded_segments, transform_log) 를
    함께 돌려주도록 반환 타입을 바꾼다. common.schema.Chunk 생성에 필요하다.
    """
    return raw
