import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

README = Path("README.md")
START_MARKER = "<!-- DAILY-SECTION-START -->"
END_MARKER = "<!-- DAILY-SECTION-END -->"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
VANCOUVER_IMAGE_CATEGORY = "Category:Quality_images_of_Vancouver"
USER_AGENT = "ZhouKanGitHubProfile/1.0 (https://github.com/Zhou-Kan)"


def commons_request(parameters):
    url = f"{COMMONS_API}?{urlencode(parameters)}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if "error" in payload:
        raise RuntimeError(f"Wikimedia Commons API error: {payload['error']}")
    return payload


def metadata_text(metadata, key, fallback=""):
    value = metadata.get(key, {})
    if isinstance(value, dict):
        value = value.get("value", fallback)
    value = re.sub(r"<[^>]*>", " ", str(value))
    return " ".join(html.unescape(value).split()) or fallback


def get_vancouver_image(local_date):
    category = commons_request(
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": VANCOUVER_IMAGE_CATEGORY,
            "cmtype": "file",
            "cmlimit": "max",
            "format": "json",
            "formatversion": "2",
        }
    )
    members = category.get("query", {}).get("categorymembers", [])
    if not members:
        raise RuntimeError("No images found in the Vancouver quality-images category")

    # Use the Vancouver date so every visitor sees the same local image that day.
    member = members[local_date.toordinal() % len(members)]
    details = commons_request(
        {
            "action": "query",
            "titles": member["title"],
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "1600",
            "format": "json",
            "formatversion": "2",
        }
    )
    pages = details.get("query", {}).get("pages", [])
    if not pages or not pages[0].get("imageinfo"):
        raise RuntimeError(f"No image details returned for {member['title']}")

    info = pages[0]["imageinfo"][0]
    metadata = info.get("extmetadata", {})
    image_url = info.get("thumburl") or info.get("url")
    description_url = info.get("descriptionurl")
    if not image_url or not description_url:
        raise RuntimeError(f"Image URL or attribution page missing for {member['title']}")

    title = member["title"].removeprefix("File:")
    author = metadata_text(metadata, "Artist", "Author not specified")
    license_name = metadata_text(metadata, "LicenseShortName", "Wikimedia Commons")
    license_url = metadata_text(metadata, "LicenseUrl")
    return image_url, description_url, title, author, license_name, license_url


def main():
    text = README.read_text(encoding="utf-8")
    if START_MARKER not in text or END_MARKER not in text:
        raise RuntimeError("Daily section markers were not found in README.md")

    now = datetime.now(ZoneInfo("America/Vancouver"))
    updated_at = now.strftime("%b %d, %Y at %I:%M %p %Z")
    image_url, description_url, title, author, license_name, license_url = (
        get_vancouver_image(now.date())
    )

    license_html = (
        f'<a href="{html.escape(license_url, quote=True)}">'
        f"{html.escape(license_name)}</a>"
        if license_url
        else html.escape(license_name)
    )
    section = (
        f"\n> Last updated: {updated_at} · Automatically refreshed daily.\n\n"
        "Hello, I'm Kan, based in Vancouver. Here's today's local photo:\n\n"
        f'<img width="100%" align="center" src="{html.escape(image_url, quote=True)}" '
        f'alt="{html.escape(title, quote=True)}">\n\n'
        f'<sub>Photo: <a href="{html.escape(description_url, quote=True)}">'
        f"{html.escape(title)}</a> · {html.escape(author)} · {license_html}"
        " · Wikimedia Commons</sub>\n"
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
