from mdcx.controllers.main_window.nfo_controller import normalize_nfo_editor_value


def test_single_line_nfo_fields_collapse_line_breaks_and_unicode_whitespace():
    assert normalize_nfo_editor_value("  三枝れい\u2028\t 490FAN-212\r\n ", multiline=False) == "三枝れい 490FAN-212"
    assert normalize_nfo_editor_value("标题\u2029下一行", multiline=False) == "标题 下一行"
    assert normalize_nfo_editor_value("演员\u00a0名字", multiline=False) == "演员 名字"


def test_multiline_nfo_fields_keep_intentional_lines_but_normalize_special_separators():
    assert normalize_nfo_editor_value("  第一行\u2028第二行  \r\n第三行  ", multiline=True) == "第一行\n第二行\n第三行"
