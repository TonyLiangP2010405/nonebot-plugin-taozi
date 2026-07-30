import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter


def pytest_configure() -> None:
    nonebot.init(driver="~none")
    nonebot.get_driver().register_adapter(Adapter)
    plugin = nonebot.load_plugin("nonebot_plugin_taozi")
    if plugin is None:
        raise RuntimeError("nonebot_plugin_taozi 加载失败")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
