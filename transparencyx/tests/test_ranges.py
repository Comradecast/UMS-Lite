from transparencyx.ranges import parse_range

def test_parse_range_standard():
    result = parse_range("$1,001 - $15,000")
    assert result.original_label == "$1,001 - $15,000"
    assert result.minimum == 1001
    assert result.maximum == 15000
    assert result.midpoint == 8000

def test_parse_range_large():
    result = parse_range("$1,000,001 - $5,000,000")
    assert result.original_label == "$1,000,001 - $5,000,000"
    assert result.minimum == 1000001
    assert result.maximum == 5000000
    assert result.midpoint == 3000000

def test_parse_range_over():
    result = parse_range("Over $50,000,000")
    assert result.original_label == "Over $50,000,000"
    assert result.minimum == 50000000
    assert result.maximum is None
    assert result.midpoint is None

def test_parse_range_none():
    result = parse_range("None")
    assert result.original_label == "None"
    assert result.minimum == 0
    assert result.maximum == 0
    assert result.midpoint == 0

def test_parse_range_na():
    result = parse_range("N/A")
    assert result.original_label == "N/A"
    assert result.minimum is None
    assert result.maximum is None
    assert result.midpoint is None

def test_parse_range_garbage():
    result = parse_range("Some weird string")
    assert result.original_label == "Some weird string"
    assert result.minimum is None
    assert result.maximum is None
    assert result.midpoint is None

def test_parse_range_almost_valid_but_garbage():
    result = parse_range("$1,001 to $15,000")
    assert result.minimum is None
    assert result.maximum is None
    assert result.midpoint is None
