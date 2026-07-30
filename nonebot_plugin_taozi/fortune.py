from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Fortune:
    name: str
    message: str
    keyword: str


FORTUNES = (
    Fortune("出货签", "今天适合随缘探索。看见问号，就去看看。", "探索"),
    Fortune("老演员签", "可能会碰见熟面孔。别急，换个地方再试试。", "耐心"),
    Fortune("无情机器签", "挑一件小事认真做完：收菜、钓鱼或解图鉴都可以。", "专注"),
    Fortune("头部主播签", "自信一点，有想法就先做起来。", "行动"),
    Fortune("好穷签", "资源少一点也没事，先享受手头能玩的部分。", "知足"),
    Fortune("帽险家签", "今天适合去没走过的地方，给自己留一点惊喜。", "发现"),
    Fortune("师父签", "遇到不确定的事，可以听听大家的建议再决定。", "交流"),
    Fortune("六冠王签", "目标可以有，但过程也要好玩。慢慢来。", "平衡"),
)


def pick_daily_fortune(user_id: str, day: date, *, salt: str = "taozi") -> Fortune:
    payload = f"{salt}:{day.isoformat()}:{user_id}".encode()
    digest = hashlib.sha256(payload).digest()
    index = int.from_bytes(digest[:8], byteorder="big") % len(FORTUNES)
    return FORTUNES[index]


def render_fortune(fortune: Fortune) -> str:
    return "\n".join(
        [
            f"【今日桃签·{fortune.name}】",
            fortune.message,
            f"今日关键词：{fortune.keyword}",
            "——互动文案，仅供娱乐，不是主播原话。",
        ]
    )


class Cooldown:
    def __init__(self, seconds: int) -> None:
        self._seconds = seconds
        self._last_seen: dict[str, float] = {}

    def acquire(self, key: str, *, now: float | None = None) -> float:
        if self._seconds <= 0:
            return 0.0

        current = time.monotonic() if now is None else now
        previous = self._last_seen.get(key)
        if previous is not None:
            remaining = self._seconds - (current - previous)
            if remaining > 0:
                return remaining

        self._last_seen[key] = current
        return 0.0

