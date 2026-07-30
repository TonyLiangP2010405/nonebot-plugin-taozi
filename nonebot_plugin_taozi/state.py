from __future__ import annotations

import asyncio
import os
from pathlib import Path

from nonebot import logger

from .models import PersistedState


class TaoziStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._loaded = False
        self._state = PersistedState()

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        async with self._lock:
            if self._loaded:
                return
            self._state = await asyncio.to_thread(self._read_sync)
            self._loaded = True

    def _read_sync(self) -> PersistedState:
        if not self._path.exists():
            return PersistedState()
        try:
            return PersistedState.model_validate_json(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            logger.warning(f"桃纸助手状态文件读取失败，将使用空状态：{error}")
            return PersistedState()

    async def _save_locked(self) -> None:
        payload = self._state.model_dump_json(indent=2)
        await asyncio.to_thread(self._write_sync, payload)

    def _write_sync(self, payload: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f"{self._path.name}.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self._path)

    async def is_group_enabled(self, group_id: str, *, default: bool) -> bool:
        await self._ensure_loaded()
        return default and group_id not in self._state.disabled_groups

    async def set_group_enabled(self, group_id: str, enabled: bool) -> None:
        await self._ensure_loaded()
        async with self._lock:
            if enabled:
                self._state.disabled_groups.discard(group_id)
            else:
                self._state.disabled_groups.add(group_id)
            await self._save_locked()

    async def get_self_color(self, scope_id: str, user_id: str) -> str | None:
        await self._ensure_loaded()
        return self._state.self_colors.get(scope_id, {}).get(user_id)

    async def set_self_color(self, scope_id: str, user_id: str, color: str) -> None:
        await self._ensure_loaded()
        async with self._lock:
            self._state.self_colors.setdefault(scope_id, {})[user_id] = color
            await self._save_locked()

    async def remove_self_color(self, scope_id: str, user_id: str) -> bool:
        await self._ensure_loaded()
        async with self._lock:
            users = self._state.self_colors.get(scope_id)
            if not users or user_id not in users:
                return False
            del users[user_id]
            if not users:
                self._state.self_colors.pop(scope_id, None)
            await self._save_locked()
            return True

