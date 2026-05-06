import re


CHINESE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def normalize_lines(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line and line.strip()]


def chinese_chars(text: str) -> list[str]:
    return [char for char in text if CHINESE_RE.match(char)]


def unique_chinese_chars(text: str) -> list[str]:
    seen: set[str] = set()
    chars: list[str] = []
    for char in chinese_chars(text):
        if char not in seen:
            seen.add(char)
            chars.append(char)
    return chars


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    sanitized = sanitized.strip("._-")
    return sanitized or "Chinese_Stroke_Order"

