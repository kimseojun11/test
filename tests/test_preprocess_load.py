"""① 입력 디코딩(load.py) 테스트."""

import codecs

import pytest

from preprocess.load import (
    UnsupportedDocumentError,
    decode_bytes,
    load_document,
    read_document,
)

KOREAN = "휴가 규정 안내\r\n연차는 1년에 15일이며, 미사용 연차는 이월되지 않습니다.\r\n"


def _write(tmp_path, name: str, data: bytes):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_plain_utf8():
    assert decode_bytes("연차는 15일".encode()) == ("연차는 15일", "utf-8", False)


def test_utf8_bom_is_removed():
    text, encoding, had_bom = decode_bytes(codecs.BOM_UTF8 + "연차".encode())
    assert (text, encoding, had_bom) == ("연차", "utf-8", True)


def test_bom_in_the_middle_is_kept():
    # 문서 중간의 U+FEFF 는 BOM 이 아니라 숨김 문자일 수 있으니 ③ 정규화가 처리한다
    text, _, had_bom = decode_bytes("연\ufeff차".encode())
    assert text == "연\ufeff차"
    assert had_bom is False


def test_crlf_is_preserved():
    text, _, _ = decode_bytes(b"line1\r\nline2\r\n")
    assert text == "line1\r\nline2\r\n"


@pytest.mark.parametrize("encoding", ["cp949", "euc_kr"])
def test_korean_legacy_encodings(encoding):
    text, detected, had_bom = decode_bytes(KOREAN.encode(encoding))
    assert text == KOREAN
    assert detected in ("cp949", "euc_kr")
    assert had_bom is False


def test_short_cp949_text():
    text, _, _ = decode_bytes("연차 규정".encode("cp949"))
    assert text == "연차 규정"


def test_utf16_with_bom_from_notepad():
    data = codecs.BOM_UTF16_LE + KOREAN.encode("utf-16-le")
    assert decode_bytes(data) == (KOREAN, "utf-16-le", True)


def test_binary_file_rejected():
    with pytest.raises(UnsupportedDocumentError, match="글자 파일"):
        decode_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe")


def test_empty_file():
    assert decode_bytes(b"") == ("", "utf-8", False)


# ── 파일 단위 ──


@pytest.mark.parametrize(
    ("name", "fmt"),
    [("a.txt", "txt"), ("a.md", "md"), ("a.html", "html"), ("a.htm", "html"), ("A.TXT", "txt")],
)
def test_format_from_extension(tmp_path, name, fmt):
    doc = read_document(_write(tmp_path, name, b"hello"))
    assert doc.fmt == fmt


@pytest.mark.parametrize("name", ["a.pdf", "a.docx", "README"])
def test_unsupported_extension_rejected(tmp_path, name):
    with pytest.raises(UnsupportedDocumentError, match="지원하지 않는"):
        read_document(_write(tmp_path, name, b"hello"))


def test_read_document_keeps_raw_text(tmp_path):
    path = _write(tmp_path, "rule.txt", codecs.BOM_UTF8 + KOREAN.encode())
    doc = read_document(path)
    assert doc.text == KOREAN  # BOM 만 빠지고 \r\n 은 그대로
    assert (doc.encoding, doc.had_bom) == ("utf-8", True)


def test_load_document_returns_text_only(tmp_path):
    path = _write(tmp_path, "rule.txt", KOREAN.encode("cp949"))
    assert load_document(path) == KOREAN
