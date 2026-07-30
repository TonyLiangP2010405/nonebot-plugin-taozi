import nonebot


def test_plugin_load() -> None:
    plugin = nonebot.get_plugin_by_module_name("nonebot_plugin_taozi")
    assert plugin is not None
    assert plugin.metadata is not None
    assert plugin.metadata.name == "桃纸助手"
    assert plugin.metadata.type == "application"
    assert plugin.metadata.supported_adapters == {"~onebot.v11"}

