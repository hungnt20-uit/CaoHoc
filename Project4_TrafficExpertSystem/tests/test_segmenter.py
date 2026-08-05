from traffic_es.acquisition.segmenter import segment

TEXT = """Điều 6. Xử phạt người điều khiển xe ô tô
11. Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe thực hiện hành vi:
a) Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.
b) Không chấp hành yêu cầu kiểm tra về nồng độ cồn.
12. Phạt tiền từ 2.000.000 đồng đến 3.000.000 đồng đối với hành vi khác.
Điều 7. Xử phạt người điều khiển xe mô tô
1. Phạt tiền từ 200.000 đồng đến 300.000 đồng.
"""


def test_segment_counts_dieu():
    clauses = segment(TEXT)
    dieus = sorted({c.dieu for c in clauses})
    assert dieus == [6, 7]


def test_diem_carries_dieu_khoan_context():
    clauses = segment(TEXT)
    a = next(c for c in clauses if c.diem == "a")
    assert a.dieu == 6 and a.khoan == 11
    assert "nồng độ cồn vượt quá 0,4" in a.text


def test_khoan_without_diem_is_a_clause():
    clauses = segment(TEXT)
    k12 = next(c for c in clauses if c.dieu == 6 and c.khoan == 12 and c.diem is None)
    assert "2.000.000" in k12.text
