from nonebot_plugin_taozi.lexicon import (
    BUILTIN_LEXICON,
    TaoziLexicon,
    normalize_term,
    render_entry,
)


def test_builtin_lexicon_contains_sourced_black_tao() -> None:
    entry = BUILTIN_LEXICON.find("黑桃")
    assert entry is not None
    assert entry.confidence == "高"
    assert entry.subject == "水友立场"
    assert "黑粉" in entry.meaning
    assert any("BV17vDaBjE3a" in source.url for source in entry.sources)


def test_alias_and_whitespace_are_normalized() -> None:
    assert normalize_term(" AI 桃 ") == "ai桃"
    entry = BUILTIN_LEXICON.find("AI桃")
    assert entry is not None
    assert entry.term == "AI 桃"


def test_unknown_term_returns_suggestions() -> None:
    assert "黑桃" in BUILTIN_LEXICON.suggest("黑")
    assert BUILTIN_LEXICON.find("不存在的桃") is None


def test_expanded_lexicon_has_sourced_terms_across_content_families() -> None:
    assert len(BUILTIN_LEXICON.entries) >= 35
    for term in (
        "桃神",
        "六冠王",
        "桃莱美",
        "双玛头",
        "小小桃大学习",
        "嘟嘟桃",
        "保姆级",
        "红字",
        "深度体验",
    ):
        entry = BUILTIN_LEXICON.find(term)
        assert entry is not None
        assert entry.sources


def test_render_entry_keeps_boundary_and_source() -> None:
    entry = BUILTIN_LEXICON.find("红桃")
    assert entry is not None
    rendered = render_entry(entry)
    assert "可信度：低" in rendered
    assert "不把“害羞”" in rendered
    assert "https://www.bilibili.com/" in rendered
    assert "非官方粉丝整理" in rendered


def test_duplicate_alias_is_rejected() -> None:
    first = BUILTIN_LEXICON.entries[0].model_copy(deep=True)
    second = BUILTIN_LEXICON.entries[1].model_copy(deep=True)
    second.aliases.append(first.term)

    try:
        TaoziLexicon([first, second])
    except ValueError as error:
        assert "别名冲突" in str(error)
    else:
        raise AssertionError("重复别名应被拒绝")
