from __future__ import annotations

import html
import json
import re
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
PARENTS = ("전국학원", "과목별학원")

H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)'
    r"(.*?)"
    r"(</script>)",
    re.IGNORECASE | re.DOTALL,
)
BREADCRUMB_RE = re.compile(
    r'(<nav\b[^>]*class=["\'][^"\']*\bbreadcrumb\b[^"\']*["\'][^>]*>)'
    r"(.*?)"
    r"(</nav>)",
    re.IGNORECASE | re.DOTALL,
)
SPAN_RE = re.compile(r"(<span\b[^>]*>)(.*?)(</span>)", re.IGNORECASE | re.DOTALL)


def plain_text(value: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", value)).split())


def update_breadcrumb_nodes(value: object, title: str) -> int:
    updates = 0

    if isinstance(value, dict):
        node_type = value.get("@type")
        is_breadcrumb = node_type == "BreadcrumbList" or (
            isinstance(node_type, list) and "BreadcrumbList" in node_type
        )
        if is_breadcrumb:
            items = value.get("itemListElement")
            if isinstance(items, list) and items:
                valid_items = [item for item in items if isinstance(item, dict)]
                if valid_items:
                    last_item = max(
                        valid_items,
                        key=lambda item: int(item.get("position", 0) or 0),
                    )
                    if last_item.get("name") != title:
                        last_item["name"] = title
                        updates += 1

        for child in value.values():
            updates += update_breadcrumb_nodes(child, title)

    elif isinstance(value, list):
        for child in value:
            updates += update_breadcrumb_nodes(child, title)

    return updates


def update_visible_breadcrumb(source: str, title: str) -> tuple[str, int]:
    match = BREADCRUMB_RE.search(source)
    if not match:
        return source, 0

    body = match.group(2)
    spans = list(SPAN_RE.finditer(body))
    if not spans:
        return source, 0

    last = spans[-1]
    if plain_text(last.group(2)) == title:
        return source, 0

    replacement = f"{last.group(1)}{html.escape(title)}{last.group(3)}"
    new_body = body[: last.start()] + replacement + body[last.end() :]
    updated_block = match.group(1) + new_body + match.group(3)
    return source[: match.start()] + updated_block + source[match.end() :], 1


def update_json_ld(source: str, title: str) -> tuple[str, int]:
    updates = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal updates
        raw = match.group(2).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)

        count = update_breadcrumb_nodes(data, title)
        if not count:
            return match.group(0)

        updates += count
        compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return match.group(1) + compact + match.group(3)

    return SCRIPT_RE.sub(replace, source), updates


def detail_pages() -> list[Path]:
    pages: list[Path] = []
    for parent in PARENTS:
        root = SITE / parent
        if not root.exists():
            continue
        for page in root.glob("*/*/index.html"):
            if page.is_file():
                pages.append(page)
    return sorted(pages)


def main() -> None:
    pages = detail_pages()
    changed_files = 0
    visible_updates = 0
    json_updates = 0
    skipped = 0

    for page in pages:
        # Keep each generated page's existing newline convention so a small
        # breadcrumb label update does not rewrite the entire HTML file.
        with page.open("r", encoding="utf-8", newline="") as handle:
            source = handle.read()
        h1_matches = H1_RE.findall(source)
        if len(h1_matches) != 1:
            skipped += 1
            continue

        title = plain_text(h1_matches[0])
        updated, visible_count = update_visible_breadcrumb(source, title)
        updated, json_count = update_json_ld(updated, title)

        if updated != source:
            with page.open("w", encoding="utf-8", newline="") as handle:
                handle.write(updated)
            changed_files += 1
        visible_updates += visible_count
        json_updates += json_count

    print(f"scanned={len(pages)}")
    print(f"changed_files={changed_files}")
    print(f"visible_updates={visible_updates}")
    print(f"json_updates={json_updates}")
    print(f"skipped={skipped}")


if __name__ == "__main__":
    main()
