"""정규화된 문서를 common.schema.Chunk 목록으로 자른다. (스텁)

TODO(1단계): 지금은 "원문을 먼저 자르고 조각마다 정규화"하는 순서인데,
반대로 "문서 전체를 먼저 정규화하고 정리본 기준으로 자르기"로 바꿔야 한다.
이유: 인코딩이 청크 경계에서 잘림, 숨김 HTML 판정이 깨짐, 토큰 수 기준이
원문(HTML 태그·제로폭 포함)과 어긋남, 조각별 NFKC 결과가 전체와 달라짐.
"""

from common.config import SEED  # noqa: F401  (TODO: config.set_seed() 로 교체)
from common.schema import Chunk, Span


def split_document(doc_id: str, raw: str, fmt: str | None = None) -> list[Chunk]:
    """문서 하나를 Chunk 목록으로 자른다. fmt 가 None 이면 내용으로 판별한다.

    TODO(1단계): 정리본 기준 384/50 토큰 슬라이딩 윈도우로 자르고,
    각 청크의 원문 구간은 offset_map 으로 역산한다. 지금은 문서 전체를
    청크 1개로 돌려준다.
    """
    from preprocess.normalize import VERSION, normalize_text

    text = normalize_text(raw, fmt)
    return [
        Chunk(
            chunk_id=f"{doc_id}-c0",
            doc_id=doc_id,
            raw_text=raw,
            text=text,
            span=Span(start=0, end=len(raw)),
            offset_map=list(range(len(text))),
            meta={"normalize_version": VERSION},
        )
    ]
