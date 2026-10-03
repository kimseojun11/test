# prompt-injection-protection

RAG 시스템에 들어가는 문서에서 프롬프트 인젝션을 탐지하는 검사 파이프라인입니다. 문서는 `preprocess → rule → stage1 → stage2` 순서로 검사하고, 단계별 결과를 검사 로그(SQLite)에 남깁니다.

## 실행

[uv](https://docs.astral.sh/uv/) 설치 후 저장소 루트에서 실행합니다.

```bash
uv sync                            # 의존성 설치 (Python 3.11)
uv run python -m common.examples   # 공용 양식 예제 출력
uv run ruff check .                # 코드 검사
```

## 구조

| 위치 | 내용 |
|---|---|
| `common/schema.py` | 공용 데이터 양식 (`Chunk`, `StageResult`, `Verdict` 등) |
| `common/config.py` | 시드, 경로, 공통 상수 |
| `common/examples.py` | 양식별 예제 |
| `common/logdb.py` | 검사 로그 저장소 (SQLite) |
| `docs/decisions.md` | 팀 결정 기록 |

## 규칙

1. `common/` 을 고치는 PR 은 팀원 전원의 리뷰를 받습니다.
2. `common/config.py` 의 값을 바꾸면 `docs/decisions.md` 도 같은 PR 에서 고칩니다.
3. 학습·평가 스크립트는 맨 위에서 `common.config.set_seed()` 를 호출합니다.
4. 의존성은 `uv add` 로 추가하고 `pyproject.toml` 과 `uv.lock` 을 함께 커밋합니다.
5. `main` 에 직접 push 하지 않고 작업 브랜치에서 PR 을 올립니다.
6. 정리본(`text`)에서 찾은 위치는 `Chunk.raw_span()` 으로 원문 위치로 바꿔서 내보냅니다.

## 환경 변수

| 이름 | 기본값 | 용도 |
|---|---|---|
| `RAG_GUARD_DATA_DIR` | `data/` | 데이터 폴더 |
| `RAG_GUARD_DB_PATH` | `data/inspection_log.db` | 검사 로그 DB |
| `WANDB_PROJECT` | `rag-guard` | 실험 기록 프로젝트 |
| `WANDB_ENTITY` | 없음 | 팀 공용 W&B 계정 |
