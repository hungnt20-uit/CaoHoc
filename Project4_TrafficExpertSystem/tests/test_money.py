from traffic_es.acquisition.money import parse_money, money_range


def test_parse_money():
    assert parse_money("30.000.000 đồng") == 30000000
    assert parse_money("500.000") == 500000


def test_money_range():
    text = "Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe"
    assert money_range(text) == (30000000, 40000000)


def test_money_range_single_returns_same():
    assert money_range("Phạt tiền 800.000 đồng") == (800000, 800000)


def test_money_range_none_when_absent():
    assert money_range("Không có mức tiền ở đây") is None


def test_money_range_ignores_small_numbers():
    # "0,4" và "1 lít" không phải tiền
    text = "nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở"
    assert money_range(text) is None
