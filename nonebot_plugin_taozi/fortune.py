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
    Fortune("老农民签", "先把今天的一小块地照顾好。稳稳做日常，积累也会出货。", "积累"),
    Fortune("红字排错签", "遇到报错别慌，从第一条开始，一条条解决。", "排错"),
    Fortune("保姆级签", "把复杂事情拆成三步，先让第一步跑起来。", "拆解"),
    Fortune("问号签", "今天的问号值得点开。先好奇，再判断。", "好奇"),
    Fortune("一厘米签", "离目标只差一点时，换个角度再试；差一点不等于失败。", "调整"),
    Fortune("放平心态签", "有就玩，没有就等等。别让稀缺感替你做决定。", "松弛"),
    Fortune("原则签", "投入时间或金钱以前，先问自己：它真的值得吗？", "价值"),
    Fortune("迷宫签", "给普通的一天加一条小岔路，也许会冒出新点子。", "创造"),
    Fortune("满星签", "练过的东西会在某个时刻连起来。今天适合再完整试一次。", "成长"),
    Fortune("练习签", "挑一个还不会的小技巧，练到比昨天顺一点。", "练习"),
    Fortune("细节签", "慢半拍看看细节，答案可能藏在不起眼的地方。", "观察"),
    Fortune("桃莱美签", "今天适合唱一段、分享一首，或者认真听完一首歌。", "表达"),
    Fortune("水友赛签", "独自卡关时，找一个靠谱队友一起过。", "协作"),
    Fortune("迷路签", "走错路不一定白走，把沿途的新发现带回来就好。", "随遇"),
    Fortune("萌新开荒签", "不会很正常。先开第一格地图，问题会越走越清楚。", "开始"),
    Fortune("更新签", "旧方法失效时别硬顶，先检查版本和新的条件。", "更新"),
)

def pick_daily_fortune(user_id: str, day: date, *, salt: str = "taozi") -> Fortune:
    """Return an independently drawn, stable fortune for one user and day."""
    payload = f"{salt}:{day.isoformat()}:{user_id}".encode()
    digest = hashlib.sha256(payload).digest()
    index = int.from_bytes(digest[:8], byteorder="big") % len(FORTUNES)
    return FORTUNES[index]


def render_fortune(
    fortune: Fortune,
    owner_name: str,
    owner_id: str,
) -> str:
    return "\n".join(
        [
            f"【{owner_name}的今日桃签·{fortune.name}】",
            f"账号：{owner_id}",
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
