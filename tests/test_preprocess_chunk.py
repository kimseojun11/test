"""문서 단위 정규화와 정리본 기준 청킹 테스트."""

import pytest

from common import examples
from common.schema import Span
from preprocess.chunk import chunks_from_document, split_document
from preprocess.normalize import (
    UNICODE_VERSION,
    VERSION,
    Context,
    normalize_document,
    normalize_text,
    resolve_format,
)

ZWSP = examples.ZWSP


def _drop_zero_width(ctx: Context) -> None:
    """테스트용 단계. 1주차에 진짜 단계로 STEPS 에 들어갈 모양 그대로다."""
    spans = ctx.tt.map_chars(lambda c: "" if c == ZWSP else None)
    ctx.record("zero_width_removed", spans)


def _expand_corp(ctx: Context) -> None:
    ctx.tt.map_chars(lambda c: "(주)" if c == "㈜" else None)


# ── 지금 동작 (STEPS 가 비어 있음) ──


def test_without_steps_text_equals_raw():
    raw = "연차는 1년에 15일입니다."
    (chunk,) = split_document("d", raw)
    assert chunk.text == chunk.raw_text == raw
    assert chunk.offset_map == list(range(len(raw)))
    assert chunk.span == Span(start=0, end=len(raw))
    assert normalize_text(raw) == raw


def test_chunk_meta_records_versions():
    (chunk,) = split_document("d", "abc", fmt=".md")
    assert chunk.meta == {
        "normalize_version": VERSION,
        "unicode_version": UNICODE_VERSION,
        "fmt": "md",
    }


def test_empty_document_gives_one_empty_chunk():
    (chunk,) = split_document("d", "")
    assert chunk.text == chunk.raw_text == ""
    assert chunk.chunk_id == "d-c0"


# ── 골격이 정규화 단계를 받았을 때 ──


def test_skeleton_reproduces_example_chunk():
    doc = normalize_document(examples.RAW_DOC, "txt", steps=[_drop_zero_width])
    (chunk,) = chunks_from_document("example", doc)
    assert chunk.text == examples.CHUNK.text
    assert chunk.offset_map == examples.CHUNK.offset_map
    assert chunk.transform_log.zero_width_removed == examples.TRANSFORM_LOG.zero_width_removed


def test_all_invisible_document_still_gives_one_chunk():
    raw = ZWSP * 5
    doc = normalize_document(raw, "txt", steps=[_drop_zero_width])
    (chunk,) = chunks_from_document("d", doc)
    assert chunk.text == ""
    assert chunk.raw_text == raw
    assert chunk.transform_log.zero_width_removed == 5


def test_deleted_chars_between_chunks_go_to_previous_chunk():
    raw = f"{ZWSP}ab{ZWSP}cd{ZWSP}"
    doc = normalize_document(raw, "txt", steps=[_drop_zero_width])
    c0, c1 = chunks_from_document("d", doc, windows=[(0, 2), (2, 4)])
    assert (c0.raw_text, c1.raw_text) == (f"{ZWSP}ab{ZWSP}", f"cd{ZWSP}")
    assert (c0.transform_log.zero_width_removed, c1.transform_log.zero_width_removed) == (2, 1)
    assert c1.span == Span(start=4, end=7)
    assert c1.raw_text[c1.offset_map[0]] == "c"


def test_overlapping_windows_share_raw_text():
    doc = normalize_document("abcdef", "txt")
    c0, c1 = chunks_from_document("d", doc, windows=[(0, 4), (2, 6)])
    assert (c0.raw_text, c1.raw_text) == ("abcd", "cdef")
    assert (c0.chunk_id, c1.chunk_id) == ("d-c0", "d-c1")


def test_window_ending_inside_expansion():
    doc = normalize_document("A㈜B", "txt", steps=[_expand_corp])
    assert doc.text == "A(주)B"
    c0, c1 = chunks_from_document("d", doc, windows=[(0, 2), (2, 5)])
    assert (c0.raw_text, c1.raw_text) == ("A㈜", "㈜B")
    assert c1.offset_map == [0, 0, 1]


def test_invalid_window_rejected():
    doc = normalize_document("abc", "txt")
    with pytest.raises(ValueError):
        chunks_from_document("d", doc, windows=[(2, 1)])


def test_record_rejects_unknown_kind():
    def typo(ctx: Context) -> None:
        ctx.record("zero_width_remove", [(0, 1)])

    with pytest.raises(ValueError, match="TransformLog"):
        normalize_document("a", "txt", steps=[typo])


# ── 형식 판별 ──


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [("html", "html"), (".htm", "html"), ("MD", "md"), ("txt", "txt"), (None, "txt")],
)
def test_resolve_format(fmt, expected):
    assert resolve_format("hello", fmt) == expected


def test_resolve_format_detects_html_head():
    assert resolve_format("\ufeff  <!DOCTYPE html><p>x</p>", None) == "html"
    assert resolve_format("<html lang='ko'>", None) == "html"


def test_resolve_format_rejects_pdf():
    with pytest.raises(ValueError, match="지원하지 않는"):
        resolve_format("x", ".pdf")
