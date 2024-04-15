from src.core.regions import Region


def test_basic():
    assert Region().name == "default_region"
