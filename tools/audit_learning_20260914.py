"""Independent static audit; product files are read-only. Reports are disposable QA outputs."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = "6840db69e"
ORIGIN = "https://xn--zj4b74v1taq8c.com"
REPORT = ROOT / "tools/reports/learning-upgrade"
HOSTS = {"xn--zj4b74v1taq8c.com", "코칭센터.com"}
failures, warnings = [], []
counts = Counter()
soups, images = {}, {}
existence = {}


def check(condition, category, path, detail):
    counts[category + "_checks"] += 1
    if not condition:
        failures.append({"category": category, "path": path, "detail": detail})


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def original(rel):
    return git("show", BASE + ":" + rel)


def parse(data):
    return BeautifulSoup(data.decode("utf-8-sig") if isinstance(data, bytes) else data, "html.parser")


def page(rel):
    if rel not in soups:
        soups[rel] = parse((ROOT / rel).read_bytes())
    return soups[rel]


def clean(value):
    return " ".join(str(value).split())


def text(node):
    return clean(node.get_text(" ", strip=True)) if node else ""


def types(node):
    value = node.get("@type", [])
    return [value] if isinstance(value, str) else value


def graph(soup, rel):
    result = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
            result.extend(data if isinstance(data, list) else data.get("@graph", [data]))
            check(True, "jsonld", rel, "")
        except Exception as exc:
            check(False, "jsonld", rel, str(exc))
    return result


def local_target(source_rel, value):
    if not value or value.startswith(("tel:", "sms:", "mailto:", "data:", "javascript:")):
        return None
    current = ORIGIN + "/" + source_rel.removesuffix("index.html")
    resolved = urlsplit(urljoin(current, value))
    if resolved.scheme not in ("http", "https") or resolved.hostname not in HOSTS:
        return None
    rel = unquote(resolved.path).lstrip("/")
    if not rel or resolved.path.endswith("/") or (not Path(rel).suffix and (ROOT / rel).is_dir()):
        rel = rel.rstrip("/") + "/index.html" if rel else "index.html"
    return rel, unquote(resolved.fragment)


def inspect_reference(source_rel, value, category="internal_reference", fragments=True):
    target = local_target(source_rel, value)
    if not target:
        return
    rel, fragment = target
    path = ROOT / rel
    if rel not in existence:
        existence[rel] = path.is_file()
    check(existence[rel], category, source_rel, "Missing destination: " + value)
    if fragment and fragments and existence[rel] and path.suffix.lower() == ".html":
        dest = page(rel)
        check(bool(dest.find(id=fragment) or dest.find("a", attrs={"name": fragment})),
              "html_fragment", source_rel, "Missing fragment: " + value)


def xml_signature(element):
    return [element.tag, sorted(element.attrib.items()), clean(element.text or ""),
            [xml_signature(child) for child in element]]


def main():
    generation = json.loads((REPORT / "generation.json").read_text(encoding="utf-8"))
    targets = list(generation["outputs"])
    target_set = set(targets)
    hubs = [p for p in targets if p.startswith(("전국학원/", "과목별학원/"))]
    check(len(targets) == 30 and len(hubs) == 26, "scope", "generation.json", "Expected 30 targets / 26 hubs")

    tree = {}
    for row in git("ls-tree", "-rz", "--full-tree", BASE).split(b"\0"):
        if not row:
            continue
        meta, name = row.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        if kind == "blob":
            tree[name.decode("utf-8")] = oid
    protected = []
    for rel, oid in tree.items():
        protected_html = rel.endswith(".html") and rel not in target_set
        protected_asset = rel.startswith("assets/")
        if not (protected_html or protected_asset):
            continue
        protected.append((rel, oid, "old_html_bytes" if protected_html else "old_asset_bytes"))

    def audit_blob(item):
        rel, oid, category = item
        path = ROOT / rel
        if not path.is_file():
            return False, category, rel, "Protected baseline file missing"
        data = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        return actual == oid, category, rel, "Protected bytes differ from baseline Git blob"

    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(audit_blob, protected):
            check(*result)
            if result[0]:
                existence[result[2]] = True
    print(json.dumps({"phase": "protected_baseline_bytes", "counts": dict(counts), "failures": len(failures)}), flush=True)
    # Product generation may complete during the long raw-byte preservation pass.
    generation = json.loads((REPORT / "generation.json").read_text(encoding="utf-8"))
    changed = git("diff", "--name-only", "-z", BASE).decode("utf-8").split("\0")
    allowed = target_set | {"sitemap.xml", "rss.xml", "llms.txt"}
    for rel in filter(None, changed):
        check(rel in allowed or rel.startswith("tools/"), "tracked_scope", rel, "Unexpected tracked product edit")

    for rel in targets:
        soup = page(rel)
        check(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == generation["outputs"][rel],
              "generation_digest", rel, "Output differs from generation report; rerun audit after final generation")
        check(len(soup.find_all("h1")) == 1 and bool(text(soup.h1)), "h1", rel, "Expected exactly one nonempty H1")
        ids = [node["id"] for node in soup.select("[id]")]
        duplicates = [key for key, count in Counter(ids).items() if count > 1]
        check(not duplicates, "duplicate_html_ids", rel, repr(duplicates))
        check(bool(soup.html and soup.html.get("lang") == "ko"), "language", rel, "Expected lang=ko")
        check(len(soup.select('link[rel="canonical"]')) == 1, "canonical", rel, "Expected one canonical")
        canonical = soup.select_one('link[rel="canonical"]')["href"]
        check(local_target(rel, canonical) == (rel, ""), "canonical", rel, canonical)
        check(soup.select_one('meta[property="og:url"]')["content"] == canonical,
              "canonical", rel, "og:url differs from canonical")
        check(bool(soup.select_one('meta[name="description"]')["content"].strip()), "metadata", rel, "Empty description")
        check("noindex" not in soup.select_one('meta[name="robots"]')["content"], "metadata", rel, "Target unexpectedly noindex")
        check(soup.select_one("link[href*='learning-upgrade.css']") is not None,
              "scoped_assets", rel, "Scoped stylesheet missing")
        check("learning-upgraded" in soup.body.get("class", []), "scoped_assets", rel, "Scoped body class missing")
        if rel in tree:
            previous_ids = {node["id"] for node in parse(original(rel)).select("[id]")}
            check(previous_ids.issubset(set(ids)), "old_fragment_ids_preserved", rel,
                  "Removed old HTML IDs: " + repr(sorted(previous_ids - set(ids))))

        nodes = graph(soup, rel)
        node_ids = [unquote(n["@id"]) for n in nodes if "@id" in n]
        duplicates = [key for key, count in Counter(node_ids).items() if count > 1]
        check(not duplicates, "duplicate_schema_ids", rel, repr(duplicates))
        visible = []
        for detail in soup.find_all("details"):
            summary = detail.find("summary")
            paras = detail.find_all("p")
            if summary and paras:
                visible.append((text(summary), clean(" ".join(text(p) for p in paras))))
        structured = []
        for node in nodes:
            if "FAQPage" in types(node):
                for question in node.get("mainEntity", []):
                    structured.append((clean(question["name"]), clean(question["acceptedAnswer"]["text"])))
        check(visible == structured and bool(visible), "faq_exact_visible", rel,
              "Visible/schema FAQ mismatch: " + repr({"visible": visible, "schema": structured}))
        counts["faq_pairs"] += len(visible)

        for node in soup.select("[href], [src], [poster]"):
            for attr in ("href", "src", "poster"):
                if node.has_attr(attr):
                    inspect_reference(rel, node[attr])
        for node in soup.select("[srcset]"):
            for candidate in node["srcset"].split(","):
                inspect_reference(rel, candidate.strip().split()[0], "srcset")
        for node in soup.select('meta[property="og:image"],meta[name="twitter:image"]'):
            inspect_reference(rel, node["content"], "social_image", fragments=False)
        for node in nodes:
            if "WebPageElement" in types(node) and node.get("url"):
                inspect_reference(rel, node["url"], "schema_element_url")

        for img in soup.find_all("img"):
            check(bool(img.get("alt", "").strip()), "image_alt", rel, "Empty ALT: " + img.get("src", ""))
            check(bool(img.get("width") and img.get("height")), "image_dimensions", rel, img.get("src", ""))
            target = local_target(rel, img.get("src", ""))
            if target and (ROOT / target[0]).is_file():
                try:
                    if target[0] not in images:
                        with Image.open(ROOT / target[0]) as decoded:
                            images[target[0]] = decoded.size
                            decoded.verify()
                    actual = images[target[0]]
                    declared = (int(img.get("width", 0)), int(img.get("height", 0)))
                    check(declared == actual, "image_intrinsic_dimensions", rel,
                          img["src"] + " declared=" + str(declared) + " actual=" + str(actual))
                except Exception as exc:
                    check(False, "image_decode", rel, str(exc))

        if rel in hubs:
            old = parse(original(rel))
            for label, selector, attr in [("title", "title", None), ("h1", "h1", None),
                                         ("canonical", 'link[rel="canonical"]', "href"),
                                         ("og_url", 'meta[property="og:url"]', "content")]:
                a, b = old.select_one(selector), soup.select_one(selector)
                check((a[attr] if attr else text(a)) == (b[attr] if attr else text(b)),
                      "hub_preserved_" + label, rel, "Changed protected field")
            old_centers = old.select(".hub-center-card")
            new_centers = soup.select(".hub-center-card")
            check([str(n) for n in old_centers] == [str(n) for n in new_centers],
                  "center_html_exact", rel, "Center card markup/facts changed")
            counts["center_cards"] += len(old_centers)
            before_nodes = graph(old, "baseline:" + rel)
            for node in before_nodes:
                if set(types(node)) & {"EducationalOrganization", "Organization", "ItemList"}:
                    matches = [n for n in nodes if n.get("@id") == node.get("@id")]
                    check(node in matches, "center_directory_schema_preserved", rel,
                          "Changed/missing node: " + str(node.get("@id")))
            selector = ".local-button-grid > a, .category-grid > a"
            before_links = [(n.get("href"), text(n)) for n in old.select(selector)]
            after_links = [(n.get("href"), text(n)) for n in soup.select(selector)]
            check(before_links == after_links, "directory_anchors_order", rel, "Directory anchors/order changed")
            counts["directory_anchors"] += len(before_links)
            if old.select(".region-block"):
                script = soup.select_one("script[src*='directory-learning-v2.js']")
                check(script is not None, "directory_script", rel, "New directory script missing")
                check(not soup.select("script[src*='/directory.js']"), "directory_script", rel, "Old directory script still loads")

    sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
    old_sitemap = ET.fromstring(original("sitemap.xml"))
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [node.findtext("s:loc", namespaces=ns) for node in sitemap]
    old_locs = [node.findtext("s:loc", namespaces=ns) for node in old_sitemap]
    normal_locs = [unquote(value) for value in locs]
    check(len(locs) == len(set(normal_locs)), "sitemap_unique", "sitemap.xml", "Duplicate sitemap URLs")
    check([value for value in locs if value in set(old_locs)] == old_locs,
          "sitemap_preserved_order", "sitemap.xml", "Existing URL list/order changed")
    added = set(normal_locs) - {unquote(value) for value in old_locs}
    check(added == {ORIGIN + "/학습코칭/"}, "sitemap_added", "sitemap.xml", repr(added))
    for node in sitemap:
        url = node.findtext("s:loc", namespaces=ns)
        inspect_reference("index.html", url, "sitemap_destination", fragments=False)
        target = local_target("index.html", url)
        if target and target[0] in target_set:
            check(node.findtext("s:lastmod", namespaces=ns) == "2026-09-14", "sitemap_modified", target[0], "Missing/current lastmod")
    for rel in targets:
        check(unquote(ORIGIN + "/" + rel.removesuffix("index.html")) in normal_locs,
              "target_discovery", rel, "Missing from sitemap")
    counts["sitemap_urls"] = len(locs)

    rss = ET.parse(ROOT / "rss.xml").getroot()
    old_rss = ET.fromstring(original("rss.xml"))
    items = rss.findall("channel/item")
    old_items = old_rss.findall("channel/item")
    rss_by_link = {unquote(item.findtext("link")): item for item in items}
    check(len(rss_by_link) == len(items), "rss_unique", "rss.xml", "Duplicate RSS links")
    for item in old_items:
        link = unquote(item.findtext("link"))
        check(link in rss_by_link, "rss_old_preserved", "rss.xml", "Old item missing: " + link)
        target = local_target("index.html", link)
        if target and target[0] not in target_set and link in rss_by_link:
            check(xml_signature(item) == xml_signature(rss_by_link[link]),
                  "rss_nontarget_exact", "rss.xml", "Unrelated item modified: " + link)
    for item in items:
        inspect_reference("index.html", item.findtext("link"), "rss_destination", fragments=False)
    check(ORIGIN + "/학습코칭/" in rss_by_link, "rss_new_page", "rss.xml", "New page absent")
    counts["rss_items"] = len(items)

    llms = (ROOT / "llms.txt").read_text(encoding="utf-8-sig")
    llms_urls = re.findall(r"https?://[^\s<>()]+", llms)
    original_llms_urls = re.findall(r"https?://[^\s<>()]+", original("llms.txt").decode("utf-8-sig"))
    check({unquote(value) for value in original_llms_urls}.issubset({unquote(value) for value in llms_urls}),
          "llms_old_links", "llms.txt", "Existing discovery links removed")
    check(ORIGIN + "/학습코칭/" in {unquote(value) for value in llms_urls},
          "llms_new_page", "llms.txt", "New coaching discovery link absent")
    for value in llms_urls:
        inspect_reference("index.html", value, "llms_destination", fragments=False)

    source_manifest = json.loads((ROOT / "tools/data/learning-upgrade/sources.json").read_text(encoding="utf-8-sig"))
    source_assets = {item["file"]: item.get("sha256") for item in source_manifest["images"]}
    source_assets.update({item["thumbnail_file"]: item["thumbnail_sha256"] for item in source_manifest["videos"]})
    for asset in (ROOT / "assets/official-learning-20260914").iterdir():
        check(asset.name in source_assets, "official_asset_manifest", asset.name, "Unlisted official asset")
        expected = source_assets.get(asset.name)
        check(bool(expected) and hashlib.sha256(asset.read_bytes()).hexdigest() == str(expected).lower(),
              "official_asset_bytes", asset.name, "Official source bytes not preserved")

    for css in [ROOT / "assets/learning-upgrade.css"]:
        for ref in re.findall(r"url\(['\"]?([^)'\"]+)", css.read_text(encoding="utf-8")):
            if not ref.startswith("data:"):
                resolved = urljoin(ORIGIN + "/assets/", ref)
                inspect_reference("index.html", resolved, "css_resource", fragments=False)

    counts["targets"] = len(targets)
    counts["hubs"] = len(hubs)
    counts["unique_decoded_images"] = len(images)
    report = {"baseline": BASE, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "PASS" if not failures else "FAIL", "counts": dict(counts),
              "failures": failures, "warnings": warnings, "targets": targets,
              "limits": ["Static checks only; root performs viewport and interactive browser QA.",
                         "External source availability and video playback are not retested here.",
                         "Product files are read-only; baseline old-HTML/assets compared as raw Git blob bytes."]}
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "independent-static-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "counts": dict(counts),
                      "failure_count": len(failures), "failures": failures[:20]}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
