from services import event_logger


def test_shannon_entropy_does_not_crash():
    value = event_logger._shannon_entropy("abc123XYZ")
    assert isinstance(value, float)
    assert value >= 0.0

