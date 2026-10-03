# 팀 결정 기록

`common/config.py` 의 값과 함께 관리합니다. 한쪽을 바꾸면 다른 쪽도 같은 PR 에서 고치고, 전원 리뷰를 받습니다. 결정을 바꿀 때는 기존 내용을 지우지 않고 변경 내용을 덧붙입니다.

## ① 좌표 규칙

- `Span` 은 `[start, end)` 반열린 구간이고, 파이썬 문자열 인덱스 단위입니다.
- `DecodedSegment.span` 과 `StageResult.evidence_span` 은 `chunk.raw_text` 기준입니다. 문서 기준 위치는 `chunk.span.start` 를 더해서 구합니다.
- 정리본(`text`)에서 찾은 위치는 `Chunk.raw_span()` 으로 원문 위치로 바꿔서 내보냅니다.
- 관련 코드: `common/schema.py` 맨 위 설명
- (2026-10 추가) `raw_span()` 의 끝은 "다음 글자의 원문 시작 위치"까지 잡습니다. 예전 계산은 NFD 자모가 합쳐진 글자(macOS 에서 온 한글)에서 끝을 잘랐습니다. 대신 구간 바로 뒤에서 지워진 글자(제로폭 등)도 하이라이트에 포함됩니다.
- (2026-10 추가) `offset_map` 은 감소하지 않습니다. 감소하면 `Chunk` 생성이 에러를 냅니다.
- (2026-10 추가) 위치 단위는 파이썬 코드포인트입니다. 웹(JS)은 UTF-16 단위라 이모지·태그 문자가 2칸이 되므로 web 에서 바꿔 씁니다.

## ② 지원 파일 형식

- `.txt`, `.md`, `.html`, `.htm` 만 지원합니다. PDF 는 지원하지 않습니다.
- 관련 코드: `common/config.py` → `SUPPORTED_EXTENSIONS`

## ③ 점수 방향

- `risk_score` 와 `final_score` 는 0.0~1.0 이고, 높을수록 위험합니다.
- 관련 코드: `common/schema.py` → `StageResult.risk_score`, `Verdict.final_score`

## ④ 청크 크기

- 청크는 384토큰, 겹침은 50토큰입니다. 1단계(전처리)와 3단계(분류)가 같은 값을 씁니다.
- 관련 코드: `common/config.py` → `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`
- (2026-10 추가) 토큰 수는 3단계 1차 모델의 토크나이저로 셉니다. 2주차 말 모델 확정 전까지는 임시로 `xlm-roberta-base` 를 씁니다. 384 에 특수 토큰([CLS], [SEP] 등)을 포함할지는 모델 확정 때 함께 정합니다.
- 관련 코드: `common/config.py` → `TOKENIZER_NAME`

## ⑤ 실험 기록

- 실험은 Weights & Biases 의 `rag-guard` 프로젝트에 팀 공용 계정으로 기록합니다.
- 관련 코드: `common/config.py` → `WANDB_PROJECT`, `WANDB_ENTITY`

## ⑥ 전처리 원칙 (제안: 이 PR 리뷰에서 확정)

- 원문 좌표는 바이트가 아니라 디코딩된 문자열 기준입니다.
- 숨김 텍스트(흰 글씨, `display:none`, 주석 등)는 지우지 않고 `text` 에 남기며, 위치는 `Chunk.transform_spans` 에 표시합니다. 실제 RAG 의 AI 가 읽는 내용과 검사 대상을 같게 하기 위해서입니다.
- 인코딩 복원 결과(`decoded_segments`)는 본문에 섞지 않고, 별도 청크로 만들어 1차에 함께 통과시킵니다. 그 청크의 위치는 원문의 인코딩 구간을 가리킵니다. (3단계 담당과 합의 필요)
- 변환 개수는 `TransformLog`, 위치는 `Chunk.transform_spans` 에 따로 담습니다. 로그 `reason` 칸에는 개수만 들어갑니다.
- Python 은 3.11 로 고정합니다. 파이썬 버전마다 유니코드 데이터가 달라 NFKC 결과가 바뀔 수 있습니다(3.11 = 14.0, 3.12 = 15.0). 3단계 학습도 3.11 에서 하고, 청크 `meta.unicode_version` 으로 확인합니다.
- 관련 코드: `common/schema.py` → `TransformLog`, `TransformSpan`, `DecodedSegment`
