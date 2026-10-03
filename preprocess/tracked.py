"""원문 위치를 기억하면서 문자열을 고치는 도구 (위치 추적 골격).

정규화의 모든 단계는 문자열을 직접 고치지 않고 TrackedText 를 거쳐서 고친다.
그래야 정리본의 각 글자가 원문 어디에서 왔는지(offset_map)가 끝까지 맞는다.

정리본의 글자마다 원문 구간 [starts[i], ends[i]) 를 기억한다.
- 삭제        : 그 글자의 구간도 함께 사라진다              "이<제로폭>전" → "이전"
- 1 → N 치환  : 새 글자 N개가 원래 글자 1개의 구간을 공유    "㈜" → "(주)"
- N → 1 치환  : 새 글자 1개가 N개 글자 전체 구간을 가리킴    NFD 자모 2개 → "무"
- 길이가 같은 치환은 한 글자씩 짝지어 구간을 넘긴다          "ｉｇｎ" → "ign"

원문에 없던 글자를 '끼워 넣기'만 하는 편집은 지원하지 않는다. 정리본의 모든 글자는
원문의 어떤 글자에서 나와야 하기 때문이다 (예: </p> 태그를 줄바꿈으로 '치환'한다).
"""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

RawSpan = tuple[int, int]  # 원문 기준 [start, end)


@dataclass(frozen=True)
class Edit:
    """현재 text 기준 [start, end) 를 new 로 바꾼다. new 가 "" 이면 삭제."""

    start: int
    end: int
    new: str


class TrackedText:
    """원문 위치를 기억하는 문자열."""

    def __init__(self, raw: str):
        self.raw = raw
        self.text = raw
        self.starts: list[int] = list(range(len(raw)))
        self.ends: list[int] = list(range(1, len(raw) + 1))

    def __len__(self) -> int:
        return len(self.text)

    # ── 편집 ──

    def apply(self, edits: Iterable[Edit]) -> list[RawSpan]:
        """편집 여러 개를 한 번에 적용하고, 편집마다 원문 구간을 돌려준다.

        편집은 현재 text 기준이고, start 순으로 정렬돼 있고, 서로 겹치지 않아야 한다.
        한 단계에서 찾은 편집을 모아 한 번에 적용하면 긴 문서도 한 번 훑는 것으로 끝난다.
        조건이 틀리면 ValueError 를 내고 아무것도 바꾸지 않는다.
        """
        edits = list(edits)
        _check_edits(edits, len(self.text))
        if not edits:
            return []

        pieces: list[str] = []
        starts: list[int] = []
        ends: list[int] = []
        spans: list[RawSpan] = []
        pos = 0
        for ed in edits:
            # 앞 편집과 이번 편집 사이의 바뀌지 않은 부분
            pieces.append(self.text[pos : ed.start])
            starts.extend(self.starts[pos : ed.start])
            ends.extend(self.ends[pos : ed.start])

            src = (self.starts[ed.start], self.ends[ed.end - 1])
            spans.append(src)
            if len(ed.new) == ed.end - ed.start:
                # 길이가 같으면 한 글자씩 짝지어 원래 구간을 그대로 넘긴다
                starts.extend(self.starts[ed.start : ed.end])
                ends.extend(self.ends[ed.start : ed.end])
            else:
                # 길이가 다르면 새 글자 전부가 바뀐 구간 전체를 가리킨다
                starts.extend([src[0]] * len(ed.new))
                ends.extend([src[1]] * len(ed.new))
            pieces.append(ed.new)
            pos = ed.end

        pieces.append(self.text[pos:])
        starts.extend(self.starts[pos:])
        ends.extend(self.ends[pos:])

        self.text = "".join(pieces)
        self.starts = starts
        self.ends = ends
        return spans

    def map_chars(self, fn: Callable[[str], str | None]) -> list[RawSpan]:
        """글자마다 fn 을 불러 바꾼다. 바뀐 글자들의 원문 구간을 돌려준다.

        fn 이 None 이나 같은 글자를 돌려주면 그대로 두고, "" 을 돌려주면 지운다.
        """
        edits = []
        for i, ch in enumerate(self.text):
            new = fn(ch)
            if new is not None and new != ch:
                edits.append(Edit(i, i + 1, new))
        return self.apply(edits)

    def sub(
        self,
        pattern: str | re.Pattern[str],
        repl: str | Callable[[re.Match[str]], str],
    ) -> list[RawSpan]:
        """정규식에 걸린 부분을 바꾼다. 바뀐 부분들의 원문 구간을 돌려준다.

        repl 이 문자열이면 re.sub 처럼 \\1 같은 역참조를 쓸 수 있다.
        빈 문자열에 걸리는 매치는 '끼워 넣기'라서 건너뛴다.
        """
        rx = re.compile(pattern) if isinstance(pattern, str) else pattern
        edits = []
        for m in rx.finditer(self.text):
            if m.start() == m.end():
                continue
            new = m.expand(repl) if isinstance(repl, str) else repl(m)
            if new != m.group():
                edits.append(Edit(m.start(), m.end(), new))
        return self.apply(edits)

    # ── 위치 ──

    def raw_span(self, start: int, end: int) -> RawSpan:
        """정리본 [start, end) → 원문 [start, end)."""
        if not 0 <= start < end <= len(self.text):
            raise ValueError(f"text 범위를 벗어난 구간입니다: [{start}, {end})")
        return self.starts[start], self.ends[end - 1]

    def validate(self) -> None:
        """대응표가 지켜야 할 규칙을 검사한다. 테스트와 디버깅용."""
        n, n_raw = len(self.text), len(self.raw)
        if not len(self.starts) == len(self.ends) == n:
            raise AssertionError("starts·ends 길이가 text 길이와 다릅니다")
        for i in range(n):
            if not 0 <= self.starts[i] < self.ends[i] <= n_raw:
                raise AssertionError(f"{i}번째 글자의 원문 구간이 잘못됐습니다")
            if i and (self.starts[i] < self.starts[i - 1] or self.ends[i] < self.ends[i - 1]):
                raise AssertionError(f"{i}번째 글자에서 원문 위치가 거꾸로 갑니다")


def _check_edits(edits: list[Edit], n: int) -> None:
    prev_end = 0
    for ed in edits:
        if not 0 <= ed.start < ed.end <= n:
            raise ValueError(f"편집 구간이 잘못됐습니다 (끼워 넣기·범위 밖 포함): {ed}")
        if ed.start < prev_end:
            raise ValueError(f"편집은 start 순으로 정렬되고 서로 겹치지 않아야 합니다: {ed}")
        prev_end = ed.end
