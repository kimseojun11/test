# 팀 결정 기록

`common/config.py` 의 값과 함께 관리합니다. 한쪽을 바꾸면 다른 쪽도 같은 PR 에서 고치고, 전원 리뷰를 받습니다. 결정을 바꿀 때는 기존 내용을 지우지 않고 변경 내용을 덧붙입니다.

## ① 좌표 규칙

- `Span` 은 `[start, end)` 반열린 구간이고, 파이썬 문자열 인덱스 단위입니다.
- `DecodedSegment.span` 과 `StageResult.evidence_span` 은 `chunk.raw_text` 기준입니다. 문서 기준 위치는 `chunk.span.start` 를 더해서 구합니다.
- 정리본(`text`)에서 찾은 위치는 `Chunk.raw_span()` 으로 원문 위치로 바꿔서 내보냅니다.
- 관련 코드: `common/schema.py` 맨 위 설명

## ② 지원 파일 형식

- `.txt`, `.md`, `.html`, `.htm` 만 지원합니다. PDF 는 지원하지 않습니다.
- 관련 코드: `common/config.py` → `SUPPORTED_EXTENSIONS`

## ③ 점수 방향

- `risk_score` 와 `final_score` 는 0.0~1.0 이고, 높을수록 위험합니다.
- 관련 코드: `common/schema.py` → `StageResult.risk_score`, `Verdict.final_score`

## ④ 청크 크기

- 청크는 384토큰, 겹침은 50토큰입니다. 1단계(전처리)와 3단계(분류)가 같은 값을 씁니다.
- 관련 코드: `common/config.py` → `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`

## ⑤ 실험 기록

- 실험은 Weights & Biases 의 `rag-guard` 프로젝트에 팀 공용 계정으로 기록합니다.
- 관련 코드: `common/config.py` → `WANDB_PROJECT`, `WANDB_ENTITY`
