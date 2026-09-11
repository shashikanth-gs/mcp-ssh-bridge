"""Application lifecycle and transport dispatch regression tests."""

from types import SimpleNamespace

import pytest

import ssh_mcp_bridge.app as app_module
from ssh_mcp_bridge.app import Application
from ssh_mcp_bridge.models.config import Config, ServerConfig


def initialized_application(server_config: ServerConfig) -> Application:
    app = Application(Config(server=server_config))
    app.service = object()
    app.mcp_server = SimpleNamespace(run=lambda: None)
    app.http_server = object()
    return app


def test_application_dispatches_stdio_transport():
    app = initialized_application(ServerConfig(enable_stdio=True, enable_http=False))
    called = []
    app.mcp_server = SimpleNamespace(run=lambda: called.append("stdio"))

    app.run()

    assert called == ["stdio"]


def test_application_dispatches_http_transport(monkeypatch):
    app = initialized_application(ServerConfig(enable_stdio=False, enable_http=True))
    called = []
    monkeypatch.setattr(app, "_run_http", lambda: called.append("http"))

    app.run()

    assert called == ["http"]


@pytest.mark.parametrize(
    ("enable_stdio", "enable_http"),
    [(True, True), (False, False)],
)
def test_application_rejects_ambiguous_or_missing_transport(enable_stdio, enable_http):
    app = initialized_application(ServerConfig(enable_stdio=enable_stdio, enable_http=enable_http))

    with pytest.raises(SystemExit) as error:
        app.run()

    assert error.value.code == 1


def test_http_runner_passes_config_to_uvicorn(monkeypatch):
    server = ServerConfig(
        host="127.0.0.1",
        port=9123,
        enable_stdio=False,
        enable_http=True,
        log_level="WARNING",
    )
    app = initialized_application(server)
    captured = {}

    def fake_run(asgi_app, **kwargs):
        captured.update({"app": asgi_app, **kwargs})

    monkeypatch.setattr(app_module.uvicorn, "run", fake_run)

    app._run_http()

    assert captured == {
        "app": app.http_server,
        "host": "127.0.0.1",
        "port": 9123,
        "log_level": "warning",
    }


def test_shutdown_stops_session_manager():
    app = Application(Config())
    called = []
    app.session_manager = SimpleNamespace(stop=lambda: called.append("stopped"))

    app.shutdown()

    assert called == ["stopped"]
