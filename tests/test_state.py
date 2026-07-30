import json
from pathlib import Path

import pytest

from nonebot_plugin_taozi.state import TaoziStateStore


@pytest.mark.asyncio
async def test_state_persists_group_switch_and_self_color(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = TaoziStateStore(path)

    assert await store.is_group_enabled("123", default=True)
    await store.set_group_enabled("123", False)
    assert not await store.is_group_enabled("123", default=True)

    await store.set_self_color("group:123", "456", "黑桃")
    assert await store.get_self_color("group:123", "456") == "黑桃"

    reloaded = TaoziStateStore(path)
    assert not await reloaded.is_group_enabled("123", default=True)
    assert await reloaded.get_self_color("group:123", "456") == "黑桃"
    assert await reloaded.remove_self_color("group:123", "456")
    assert await reloaded.get_self_color("group:123", "456") is None

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1


@pytest.mark.asyncio
async def test_invalid_state_file_falls_back_to_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{invalid", encoding="utf-8")
    store = TaoziStateStore(path)
    assert await store.is_group_enabled("123", default=True)
    assert await store.get_self_color("group:123", "456") is None

