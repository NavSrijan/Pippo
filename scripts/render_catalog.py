"""Rebuild command cards and dialogs from their single JSON source."""
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "website"


def render_catalog(source, records):
    by_id = {record["id"]: record for record in records}

    def card(match):
        r = by_id[match.group(1)]
        e = {key: escape(str(value), quote=True) for key, value in r.items()}
        search = escape(" ".join(str(r[k]) for k in ("command", "title", "description", "category")).lower(), quote=True)
        return (
            f'<article class="command-card" id="{e["id"]}" data-category="{e["category"]}" data-search="{search}">'
            f'<div class="command-card-heading"><span class="command-emoji" aria-hidden="true">{e["emoji"]}</span>'
            f'<span class="command-category">{e["category"]}</span></div><h2><code>/{e["command"]}</code></h2>'
            f'<h3>{e["title"]}</h3><p>{e["description"]}</p>'
            f'<button type="button" class="command-preview" data-open="detail-{e["id"]}" aria-label="View {e["command"]} preview and example">'
            f'<img src="{e["image"]}" alt="Pippo {e["command"]} preview" loading="lazy" width="640" height="340"/>'
            f'<span>{e["capture"]}<b aria-hidden="true">↗</b></span></button><div class="command-card-bottom">'
            f'<code>{e["example"]}</code><button type="button" data-copy="{e["example"]}" aria-label="Copy {e["command"]} example">Copy</button></div></article>'
        )

    def dialog(match):
        r = by_id[match.group(1)]
        e = {key: escape(str(value), quote=True) for key, value in r.items()}
        return (
            f'<dialog class="command-dialog" id="detail-{e["id"]}" aria-labelledby="title-{e["id"]}">'
            '<button type="button" class="dialog-close" aria-label="Close command preview" data-close>×</button>'
            f'<div class="dialog-copy"><p class="eyebrow eyebrow-dark">{e["category"]} · {e["capture"]}</p>'
            f'<h2 id="title-{e["id"]}">{e["emoji"]} /{e["command"]}</h2><p>{e["description"]}</p>'
            f'<div class="example-line"><code>{e["example"]}</code><button type="button" data-copy="{e["example"]}">Copy example</button></div>'
            f'</div><figure><img src="{e["image"]}" alt="Pippo {e["command"]} preview" loading="lazy"/><figcaption>{e["capture"]}</figcaption></figure></dialog>'
        )

    source, cards = re.subn(r'<article class="command-card" id="([^"]+)".*?</article>', card, source, flags=re.S)
    source, dialogs = re.subn(r'<dialog class="command-dialog" id="detail-([^"]+)".*?</dialog>', dialog, source, flags=re.S)
    if cards != len(records) or dialogs != len(records):
        raise ValueError("The catalog template and JSON command set do not match")
    return source


if __name__ == "__main__":
    records = json.loads((ROOT / "commands.json").read_text())
    page = ROOT / "commands.html"
    page.write_text(render_catalog(page.read_text(), records))
