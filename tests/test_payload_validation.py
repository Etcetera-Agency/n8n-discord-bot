import sys
import types
import logging
import pytest


@pytest.mark.asyncio
async def test_dispatch_invalid_payload_logs_and_returns_error(monkeypatch, caplog):
    # Stub minimal config
    Strings = types.SimpleNamespace(
        TRY_AGAIN_LATER="Спробуй трохи піздніше. Я тут пораюсь по хаті."
    )
    config_mod = types.SimpleNamespace(
        Config=types.SimpleNamespace(), logger=logging.getLogger("test"), Strings=Strings
    )
    monkeypatch.setitem(sys.modules, "config", config_mod)

    # Import router after stubbing config
    import importlib
    sys.modules.pop("router", None)
    router = importlib.import_module("router")

    caplog.set_level(logging.DEBUG)

    # Missing required channelId should trigger validation error
    bad_payload = {"userId": "321", "command": "dummy"}
    resp = await router.dispatch(bad_payload)

    assert resp.to_dict() == {"output": Strings.TRY_AGAIN_LATER}
    assert any("failed to validate payload" in r.getMessage() for r in caplog.records)

