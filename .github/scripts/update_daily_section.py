import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

README = Path("README.md")
START_MARKER = "<!-- DAILY-SECTION-START -->"
END_MARKER = "<!-- DAILY-SECTION-END -->"
BING_ARCHIVE_URL = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1"


def get_daily_image():
    request = Request(
        BING_ARCHIVE_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; GitHubProfileUpdater/1.0)"},
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    image = payload["images"][0]
    image_url = image["url"]
    if image_url.startswith("/"):
        image_url = "https://www.bing.com" + image_url
    elif not image_url.startswith("https://"):
        image_url = "https://www.bing.com/" + image_url.lstrip("/")

    return image_url, image.get("title") or image.get("copyright") or "Bing daily image"


def main():
    text = README.read_text(encoding="utf-8")
    if START_MARKER not in text or END_MARKER not in text:
        raise RuntimeError("Daily section markers were not found in README.md")

    updated_at = datetime.now(ZoneInfo("America/Vancouver")).strftime(
        "%b %d, %Y at %I:%M %p %Z"
    )
    image_url, image_title = get_daily_image()

    section = (
        f"\n> Last updated: {updated_at} · Automatically refreshed daily.\n\n"
        "Hello, I'm Kan, based in Vancouver. Here's today's image:\n\n"
        f'<img width="100%" align="center" src="{html.escape(image_url, quote=True)}" '
        f'alt="{html.escape(image_title, quote=True)}">\n'
    )

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        flags=re.DOTALL,
    )
    replacement = f"{START_MARKER}{section}{END_MARKER}"
    updated_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError("Could not update the daily section")

    README.write_text(updated_text, encoding="utf-8")


if __name__ == "__main__":
    main()
