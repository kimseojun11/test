"""위치 추적 골격(TrackedText) 테스트."""

import re
import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from preprocess.tracked import Edit, TrackedText

ZWSP = "\u200b"


def test_untouched_text_maps_to_itself():
    tt = TrackedText("abc")
    assert tt.text == "abc"
    assert tt.starts == [0, 1, 2]
    assert tt.raw_span(0, 3) == (0, 3)


def test_delete_shifts_positions():
    tt = TrackedText(f"이{ZWSP}전 지{ZWSP}시")
    spans = tt.map_chars(lambda c: "" if c == ZWSP else None)
    assert tt.text == "이전 지시"
    assert spans == [(1, 2), (5, 6)]
    assert tt.starts == [0, 2, 3, 4, 6]
    assert tt.raw_span(1, 4) == (2, 5)  # "전 지"


def test_one_to_many_shares_source():
    tt = TrackedText("A㈜B")
    tt.apply([Edit(1, 2, "(주)")])
    assert tt.text == "A(주)B"
    assert tt.starts == [0, 1, 1, 1, 2]
    assert tt.raw_span(1, 3) == (1, 2)  # "(주" → 원문 "㈜" 전체
    assert tt.raw_span(4, 5) == (2, 3)


def test_many_to_one_covers_all_jamo():
    raw = unicodedata.normalize("NFD", "무시해")  # macOS 형태, 자모 6개
    tt = TrackedText(raw)
    tt.apply([Edit(i, i + 2, unicodedata.normalize("NFC", raw[i : i + 2])) for i in (0, 2, 4)])
    assert tt.text == "무시해"
    assert tt.raw_span(0, 3) == (0, 6)  # 끝 자모까지 빠짐없이
    assert tt.raw_span(0, 2) == (0, 4)


def test_same_length_replacement_keeps_per_char_positions():
    tt = TrackedText("xｉｇｎy")
    tt.apply([Edit(1, 4, "ign")])
    assert tt.text == "xigny"
    assert tt.starts == [0, 1, 2, 3, 4]


def test_steps_compose():
    tt = TrackedText(f"㈜{ZWSP}무")
    tt.map_chars(lambda c: "" if c == ZWSP else None)
    tt.map_chars(lambda c: "(주)" if c == "㈜" else None)
    assert tt.text == "(주)무"
    assert tt.starts == [0, 0, 0, 2]
    assert tt.raw_span(3, 4) == (2, 3)


def test_sub_collapses_runs():
    tt = TrackedText("a  b   c")
    spans = tt.sub(r" {2,}", " ")
    assert tt.text == "a b c"
    assert spans == [(1, 3), (4, 7)]
    assert tt.raw_span(1, 2) == (1, 3)  # 줄어든 공백 하나가 원래 공백 둘을 가리킨다


def test_sub_supports_backreference_and_skips_empty_match():
    tt = TrackedText("ab")
    tt.sub(r"(a)|x*", r"\1\1")
    assert tt.text == "aab"


@pytest.mark.parametrize(
    "edits",
    [
        [Edit(1, 1, "x")],  # 끼워 넣기
        [Edit(2, 1, "")],  # 거꾸로
        [Edit(0, 5, "")],  # 범위 밖
        [Edit(1, 2, ""), Edit(0, 1, "")],  # 정렬 안 됨
        [Edit(0, 2, ""), Edit(1, 3, "")],  # 겹침
    ],
)
def test_invalid_edits_rejected_without_change(edits):
    tt = TrackedText("abc")
    with pytest.raises(ValueError):
        tt.apply(edits)
    assert tt.text == "abc"
    assert tt.starts == [0, 1, 2]


# ── 무작위 문자열로 규칙 검사 ──

_ALPHABET = ["a", "b", "가", ZWSP, "㈜", "\u3000", "\U000e0041", "😀"]
_texts = st.text(alphabet=st.sampled_from(_ALPHABET), max_size=40)


def _drop_or_expand(c: str) -> str | None:
    if c == ZWSP:
        return ""
    if c == "㈜":
        return "(주)"
    return None


@settings(derandomize=True, max_examples=300)
@given(_texts)
def test_every_char_points_to_its_source(raw):
    tt = TrackedText(raw)
    tt.map_chars(_drop_or_expand)
    tt.sub(r"a+", "a")
    tt.validate()

    expected = re.sub("a+", "a", raw.replace(ZWSP, "").replace("㈜", "(주)"))
    assert tt.text == expected
    for i, ch in enumerate(tt.text):
        src = raw[tt.starts[i] : tt.ends[i]]
        if ch in "()주":
            assert src == "㈜"
        elif ch == "a":
            assert set(src) == {"a"}
        else:
            assert src == ch


@settings(derandomize=True, max_examples=300)
@given(_texts)
def test_whole_text_span_covers_first_to_last_kept_char(raw):
    tt = TrackedText(raw)
    tt.map_chars(_drop_or_expand)
    if not tt.text:
        return
    start, end = tt.raw_span(0, len(tt.text))
    kept = [i for i, c in enumerate(raw) if c != ZWSP]
    assert (start, end) == (kept[0], kept[-1] + 1)
