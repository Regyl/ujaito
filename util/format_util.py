import html
import re

_TAG = re.compile(r"<[^>]+>")

def plain_text(value: str) -> str:
    return html.unescape(_TAG.sub(" ", value))