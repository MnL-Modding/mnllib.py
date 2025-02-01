import pytest


@pytest.fixture(autouse=True)
def _change_test_dir(  # pyright: ignore[reportUnusedFunction]
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(request.path.parent)
