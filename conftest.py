import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--run-expensive", action="store_true", default=False, help="run expensive tests"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "expensive: mark test as expensive to run")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-expensive"):
        skip_expensive = pytest.mark.skip(reason="need --run-expensive option to run")
        for item in items:
            if "expensive" in item.keywords:
                item.add_marker(skip_expensive)