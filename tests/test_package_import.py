from importlib.metadata import distribution

from jobradar.api.app import app


def test_jobradar_package_is_installed_and_importable() -> None:
    assert distribution("jobradar").version == "0.1.0"
    assert app.title == "JobRadar"
