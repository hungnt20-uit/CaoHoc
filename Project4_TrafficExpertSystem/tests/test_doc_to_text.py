import zipfile
from pathlib import Path

from traffic_es.acquisition.doc_to_text import to_text


def test_reads_txt_directly():
    txt = to_text(Path("tests/fixtures/sample_clause.txt"))
    assert "Điều 6." in txt
    assert "nồng độ cồn vượt quá 0,4" in txt


def test_reads_docx_via_zipfile(tmp_path):
    # tạo 1 .docx tối thiểu hợp lệ để test không phụ thuộc file thật
    docx = tmp_path / "mini.docx"
    document_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Điều 6. Thử nghiệm</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>11. Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng.</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/document.xml", document_xml)
    txt = to_text(docx)
    assert "Điều 6. Thử nghiệm" in txt
    assert "30.000.000" in txt
