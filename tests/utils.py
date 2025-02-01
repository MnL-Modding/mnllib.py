import typing

import pytest


def open_or_skip(*args: typing.Any, **kwargs: typing.Any) -> typing.IO[typing.Any]:
    try:
        return typing.cast(typing.IO[typing.Any], open(*args, **kwargs))
    except FileNotFoundError:
        pytest.skip("file not present")
