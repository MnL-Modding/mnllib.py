import collections.abc

import pytest


@pytest.fixture(scope="module")
def monkeymodule() -> collections.abc.Generator[pytest.MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(autouse=True, scope="module")
def _change_test_dir(  # pyright: ignore[reportUnusedFunction]
    request: pytest.FixtureRequest, monkeymodule: pytest.MonkeyPatch
) -> None:
    monkeymodule.chdir(request.path.parent)
