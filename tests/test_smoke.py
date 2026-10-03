"""저장소가 일단 돌아가는지 확인하는 최소 테스트.

각 담당자가 맡은 영역에 테스트를 추가하면 이 파일은 그대로 둬도 되고,
더 적절한 파일로 옮겨도 된다.
"""

from common import examples
from common.logdb import connect, escalation_rate, log_verdict
from preprocess.chunk import split_document


def test_examples_build_without_error():
    assert examples.CHUNK.chunk_id == "example-c0"
    assert examples.VERDICT.final_label == "injection"


def test_logdb_roundtrip():
    conn = connect(":memory:")
    n = log_verdict(conn, examples.VERDICT, request_id="r1", doc_id="example", policy="default")
    assert n == len(examples.VERDICT.stage_results) + 1  # preprocess 줄 포함
    assert escalation_rate(conn) == 1.0


def test_split_document_stub_returns_one_chunk():
    chunks = split_document("doc1", "hello world")
    assert len(chunks) == 1
    assert chunks[0].doc_id == "doc1"
