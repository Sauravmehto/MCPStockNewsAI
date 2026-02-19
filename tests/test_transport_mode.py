from mcp_server.main import resolve_http_transport, resolve_transport_mode


def test_resolve_transport_mode_auto_local(monkeypatch) -> None:
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    assert resolve_transport_mode("auto") == "stdio"


def test_resolve_transport_mode_auto_hosted(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "10000")
    assert resolve_transport_mode("auto") == "http"


def test_resolve_http_transport_default() -> None:
    assert resolve_http_transport("invalid") == "sse"


