"""파이프라인 진입점. --file 로 받은 문서를 단계별로 검사한다. (스텁)

지금은 전처리 결과를 만드는 것까지만 한다. rule/stage1/stage2 는
담당자 작업이 끝나는 대로 이어붙인다.
"""

import argparse
from pathlib import Path

from preprocess.chunk import split_document
from preprocess.load import load_document
from preprocess.normalize import VERSION


def run(path: str | Path) -> None:
    doc_id = Path(path).stem
    raw = load_document(path)
    # TODO(팀장): --file 의 확장자를 fmt 로 넘긴다.
    chunks = split_document(doc_id, raw)
    print(f"[preprocess v{VERSION}] {doc_id}: {len(chunks)}개 청크")
    for c in chunks:
        print(f"  {c.chunk_id}: {len(c.text)}자")


def main() -> None:
    parser = argparse.ArgumentParser(description="prompt-injection-protection 파이프라인")
    parser.add_argument("--file", required=True, help="검사할 문서 경로")
    args = parser.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
