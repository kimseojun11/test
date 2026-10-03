"""③ 유니코드 정규화 단계 5개. normalize.STEPS 에 이 순서대로 들어간다.

  1. decode_tag_chars   태그 문자 해독      → tag_chars_decoded, decoded_segments
  2. remove_bidi        양방향 제어문자 제거 → bidi_removed
  3. remove_invisible   보이지 않는 문자 제거 → zero_width_removed, hangul_filler_removed,
                                                variation_selector_removed, emoji_zwj
  4. apply_nfkc         NFKC + 한글 자모 후처리 → nfkc_changed
  5. tidy_whitespace    줄바꿈·공백 정리 (기록 안 함, 의심 신호가 아님)

순서가 중요하다. 태그 문자와 양방향 제어문자도 유니코드 분류가 Cf(형식 문자)라서,
3번의 "Cf 는 지운다" 규칙이 먼저 돌면 태그 문자는 해독 전에 사라지고 양방향 제어문자는
제로폭 문자로 잘못 세어진다.
"""

import unicodedata

from preprocess.context import Context
from preprocess.tracked import Edit

# ── 1. 태그 문자 ──

_TAG_FIRST, _TAG_LAST = 0xE0000, 0xE007F
_CANCEL_TAG = "\U000e007f"
_BLACK_FLAG = "\U0001f3f4"  # 🏴 + 태그 문자 = 잉글랜드·스코틀랜드 같은 지역 깃발 이모지


def _is_tag(ch: str) -> bool:
    return _TAG_FIRST <= ord(ch) <= _TAG_LAST


def decode_tag_chars(ctx: Context) -> None:
    """태그 문자를 해독해서 복원 칸에 넣고 본문에서는 지운다.

    태그 문자는 화면에 안 보이지만 하나하나가 ASCII 한 글자에 대응해서, AI 가 숨긴 영어
    문장을 읽어낼 수 있다 (ASCII 스머글링). 지우기만 하면 증거가 사라지므로 먼저 해독한다.
    단, 🏴 뒤에 붙은 지역 깃발 이모지는 정상이라 지우기만 하고 세지 않는다.
    """
    tt = ctx.tt
    text = tt.text
    suspicious: list[int] = []
    i = 0
    while i < len(text):
        if not _is_tag(text[i]):
            i += 1
            continue
        j = i
        while j < len(text) and _is_tag(text[j]):
            j += 1
        decoded = "".join(
            chr(ord(c) - _TAG_FIRST) for c in text[i:j] if 0x20 <= ord(c) - _TAG_FIRST <= 0x7E
        )
        is_flag = (
            i > 0
            and text[i - 1] == _BLACK_FLAG
            and text[j - 1] == _CANCEL_TAG
            and decoded.isalnum()
            and decoded.islower()
        )
        if not is_flag:
            suspicious.extend(range(i, j))
            if decoded:
                ctx.add_decoded("unicode_tag", tt.raw_span(i, j), decoded)
        i = j

    flagged = set(suspicious)
    edits = [Edit(k, k + 1, "") for k, ch in enumerate(text) if _is_tag(ch)]
    spans = tt.apply(edits)
    ctx.record(
        "tag_chars_decoded", [s for e, s in zip(edits, spans, strict=True) if e.start in flagged]
    )


# ── 2. 양방향 제어문자 ──

_BIDI = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200e\u200f\u061c")


def remove_bidi(ctx: Context) -> None:
    """글자 표시 순서를 뒤집는 특수문자를 지운다.

    아랍어·히브리어 정상 문서에도 들어 있으니 개수는 신호로만 쓴다.
    """
    spans = ctx.tt.map_chars(lambda c: "" if c in _BIDI else None)
    ctx.record("bidi_removed", spans)


# ── 3. 보이지 않는 문자 ──

_ZWJ = "\u200d"
_VS16 = "\ufe0f"
_KEYCAP = "\u20e3"
_HANGUL_FILLERS = frozenset("\u3164\u115f\u1160\uffa0")
# Cf 가 아니라서 분류 규칙으로 안 잡히는 보이지 않는 문자
_EXTRA_INVISIBLE = frozenset("\u034f")  # COMBINING GRAPHEME JOINER (Mn)

# 이모지 범위 (근사치). 파이썬 unicodedata 에는 Extended_Pictographic 속성이 없다
_PICTO_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x2300, 0x23FF),
    (0x2B00, 0x2BFF),
    (0x2190, 0x21FF),
)
_PICTO_SINGLES = frozenset(
    "\u00a9\u00ae\u203c\u2049\u2122\u2139\u3030\u303d\u3297\u3299\u24c2\u25aa\u25ab\u25b6\u25c0"
)


def _is_picto(ch: str) -> bool:
    cp = ord(ch)
    return ch in _PICTO_SINGLES or any(a <= cp <= b for a, b in _PICTO_RANGES)


def _is_variation_selector(ch: str) -> bool:
    cp = ord(ch)
    return 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF


def _prev_picto(text: str, i: int) -> bool:
    """i 앞의 글자가 (변형 선택자를 건너뛰고) 이모지인가."""
    k = i - 1
    while k >= 0 and _is_variation_selector(text[k]):
        k -= 1
    return k >= 0 and _is_picto(text[k])


def remove_invisible(ctx: Context) -> None:
    """제로폭 문자·한글 채움 문자·변형 선택자를 지우고 종류별로 센다.

    정상적인 이모지를 이루는 문자는 지우되 의심 신호에서 뺀다.
    - 이모지 사이의 ZWJ (👨‍👩‍👧)  → emoji_zwj 로 따로 센다
    - 이모지 바로 뒤의 U+FE0F (❤️), 키캡 숫자 (1️⃣)  → 세지 않는다
    """
    text = ctx.tt.text
    edits: list[Edit] = []
    kinds: list[str | None] = []
    for i, ch in enumerate(text):
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch == _ZWJ:
            kind = "emoji_zwj" if _prev_picto(text, i) and nxt and _is_picto(nxt) else None
            kind = kind or "zero_width_removed"
        elif ch in _HANGUL_FILLERS:
            kind = "hangul_filler_removed"
        elif _is_variation_selector(ch):
            prev = text[i - 1] if i else ""
            normal_emoji = ch == _VS16 and (
                (prev and _is_picto(prev)) or (prev in "0123456789#*" and prev and nxt == _KEYCAP)
            )
            kind = None if normal_emoji else "variation_selector_removed"
        elif ch in _EXTRA_INVISIBLE or unicodedata.category(ch) == "Cf":
            kind = "zero_width_removed"
        else:
            continue
        edits.append(Edit(i, i + 1, ""))
        kinds.append(kind)

    spans = ctx.tt.apply(edits)
    by_kind: dict[str, list] = {}
    for kind, span in zip(kinds, spans, strict=True):
        if kind is not None:
            by_kind.setdefault(kind, []).append(span)
    for kind, kind_spans in by_kind.items():
        ctx.record(kind, kind_spans)


# ── 4. NFKC + 한글 자모 후처리 ──


def _is_conjoining_jamo(ch: str) -> bool:
    cp = ord(ch)
    return 0x1100 <= cp <= 0x11FF or 0xA960 <= cp <= 0xA97F or 0xD7B0 <= cp <= 0xD7FF


def _build_compat_jamo() -> dict[str, str]:
    """조합형 자모 → 호환 자모 (NFKC 의 반대 방향). 예: U+110F(ᄏ) → U+314B(ㅋ)"""
    table: dict[str, str] = {}
    for cp in range(0x3131, 0x318F):
        d = unicodedata.normalize("NFKC", chr(cp))
        if len(d) == 1 and _is_conjoining_jamo(d):
            table.setdefault(d, chr(cp))
    return table


_TO_COMPAT_JAMO = _build_compat_jamo()


def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def _cannot_join_back(ch: str) -> bool:
    """앞 조각과 NFKC 에서 합쳐질 수 없는 글자인가. ASCII 와 완성형 한글 음절이 그렇다."""
    return ch < "\x80" or 0xAC00 <= ord(ch) <= 0xD7A3


def _nfkc_segments(text: str) -> list[tuple[int, int]]:
    """NFKC 를 조각마다 따로 해도 전체 결과와 같아지도록 문자열을 나눈다.

    결합 문자(악센트 등)는 앞 글자와 같은 조각에 둔다. 이웃 조각끼리 NFKC 에서 합쳐지면
    (예: 호환 자모 ㅁ + ㅜ → 무) 한 조각으로 묶는다. ASCII 와 완성형 음절은 앞 조각과
    합쳐질 일이 없어서 비교 없이 바로 끊는다 (긴 한국어 문서도 빠르게 처리하기 위해).
    """
    starts = [i for i, ch in enumerate(text) if i == 0 or unicodedata.combining(ch) == 0]
    bounds = list(zip(starts, starts[1:] + [len(text)], strict=True))
    if not bounds:
        return []
    out: list[tuple[int, int]] = []
    cur_s, cur_e = bounds[0]
    for s, e in bounds[1:]:
        nxt = text[s:e]
        cur = text[cur_s:cur_e]
        if _cannot_join_back(nxt[0]) or _nfkc(cur + nxt) == _nfkc(cur) + _nfkc(nxt):
            out.append((cur_s, cur_e))
            cur_s, cur_e = s, e
        else:
            cur_e = e
    out.append((cur_s, cur_e))
    return out


def apply_nfkc(ctx: Context) -> None:
    """NFKC 정규화. 전각 ｉｇｎ → ign, ㈜ → (주), 자모 분리 ㅁㅜㅅㅣ → 무시.

    부작용 하나를 되돌린다. NFKC 는 ㅋ(호환 자모)을 ᄏ(조합형 초성)으로 바꾸는데,
    음절로 합쳐지지 못하고 혼자 남으면 정상 텍스트(ㅋㅋㅋ)가 다른 글자가 되어 토큰화가
    달라진다. 그래서 원래 호환 자모였다가 혼자 남은 것은 호환 자모로 되돌린다.
    """
    text = ctx.tt.text
    if unicodedata.is_normalized("NFKC", text):
        return
    segments = _nfkc_segments(text)
    if "".join(_nfkc(text[s:e]) for s, e in segments) != _nfkc(text):
        segments = [(0, len(text))]  # 드문 경우의 안전장치: 위치는 거칠어져도 결과는 정확하게

    edits = []
    for s, e in segments:
        seg = text[s:e]
        new = _nfkc(seg)
        if not any(_is_conjoining_jamo(c) for c in seg):
            new = "".join(_TO_COMPAT_JAMO.get(c, c) for c in new)
        if new != seg:
            edits.append(Edit(s, e, new))
    ctx.record("nfkc_changed", ctx.tt.apply(edits))


# ── 5. 공백 정리 ──


def tidy_whitespace(ctx: Context) -> None:
    """줄바꿈을 \\n 으로 통일하고, 연속 공백과 3줄 이상 빈 줄을 줄인다.

    소문자 변환은 하지 않는다 (모델이 대소문자를 구분해서 읽는다).
    """
    tt = ctx.tt
    tt.sub(r"\r\n?|[\u2028\u2029\u0085]", "\n")
    tt.sub(r"[^\S\n]+", " ")
    tt.sub(r"\n(?: ?\n){2,}", "\n\n")
