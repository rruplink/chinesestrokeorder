from app.services.parser import normalize_lines, sanitize_filename, unique_chinese_chars


def test_normalize_lines_ignores_empty_lines():
    assert normalize_lines(["你好", "", "  中国  "]) == ["你好", "中国"]


def test_unique_chinese_chars_preserves_order():
    assert unique_chinese_chars("你好你好abc") == ["你", "好"]


def test_sanitize_filename_has_safe_default():
    assert sanitize_filename("Chinese Stroke Order!") == "Chinese_Stroke_Order"
    assert sanitize_filename("///") == "Chinese_Stroke_Order"

