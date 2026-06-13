import web


def test_web_package_importable() -> None:
    assert web.__doc__
