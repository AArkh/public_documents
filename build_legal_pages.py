#!/usr/bin/env python3
"""
Build policy.html and tos.html from LEGAL_PRIVACY_EN.md and LEGAL_TERMS_EN.md.
Run from project root or public_documents: python build_legal_pages.py
Uses only the standard library (no pip install needed).
"""
import html
import re
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent

LEGAL_PROSE_CSS = """
      .legal-prose { max-width: 65ch; }
      .legal-prose h1 { font-size: 1.875rem; font-weight: 600; margin-top: 0; margin-bottom: 1rem; }
      .legal-prose h2 { font-size: 1.25rem; font-weight: 600; margin-top: 2rem; margin-bottom: 0.75rem; }
      .legal-prose h3 { font-size: 1.125rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.5rem; }
      .legal-prose h4 { font-size: 1rem; font-weight: 600; margin-top: 1.25rem; margin-bottom: 0.5rem; }
      .legal-prose p { font-size: 1rem; line-height: 1.7; color: rgb(64 64 64); margin-bottom: 1rem; }
      .legal-prose ul, .legal-prose ol { margin: 0.75rem 0 1rem 0; padding-left: 1.5rem; }
      .legal-prose li { margin-bottom: 0.35rem; line-height: 1.6; color: rgb(64 64 64); }
      .legal-prose strong { font-weight: 600; color: rgb(38 38 38); }
      .legal-prose a { color: rgb(79 70 229); text-decoration: underline; }
      .legal-prose a:hover { color: rgb(67 56 202); }
      .legal-prose hr { border: 0; border-top: 1px solid rgb(229 231 235); margin: 2rem 0; }
      .legal-prose table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9375rem; }
      .legal-prose th, .legal-prose td { border: 1px solid rgb(229 231 235); padding: 0.5rem 0.75rem; text-align: left; }
      .legal-prose th { font-weight: 600; background: rgb(249 250 251); }
"""


def _inline_md(text: str) -> str:
    """Convert inline markdown: **bold**, [text](url), escape HTML."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def convert_md_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    in_ul = False
    in_ol = False
    in_table = False
    table_rows: list[list[str]] = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        out.append("<table>")
        for row_idx, row in enumerate(table_rows):
            tag = "th" if row_idx == 0 and any(c.strip() for c in row) else "td"
            cells = "".join(f"<{tag}>{_inline_md(c.strip())}</{tag}>" for c in row)
            out.append(f"<tr>{cells}</tr>")
        out.append("</table>")
        table_rows = []
        in_table = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Table row: | a | b |
        if re.match(r"^\s*\|.+\|\s*$", line):
            if not in_table:
                flush_table() if table_rows else None
                in_table = True
            if re.match(r"^\s*\|[\s\-:]+\|\s*$", line):  # separator
                i += 1
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            table_rows.append(cells)
            i += 1
            continue
        else:
            flush_table()

        # Headers
        if stripped.startswith("# "):
            out.append(f"<h1>{_inline_md(stripped[2:])}</h1>")
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{_inline_md(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("### "):
            out.append(f"<h3>{_inline_md(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("#### "):
            out.append(f"<h4>{_inline_md(stripped[5:])}</h4>")
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            out.append("<hr />")
            i += 1
            continue

        # Unordered list
        if stripped.startswith("- ") or re.match(r"^\s*\*\s+", line):
            bullet = stripped.startswith("- ") or stripped.startswith("* ")
            content = stripped[2:].strip() if bullet else stripped.lstrip()[2:].strip()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_md(content)}</li>")
            i += 1
            continue

        # Ordered list
        if re.match(r"^\s*\d+\.\s+", line):
            content = re.sub(r"^\s*\d+\.\s+", "", stripped)
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{_inline_md(content)}</li>")
            i += 1
            continue

        # Empty line: close lists, new paragraph
        if not stripped:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            i += 1
            continue

        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

        out.append(f"<p>{_inline_md(stripped)}</p>")
        i += 1

    flush_table()
    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")

    return "\n".join(out)


def inject_content_into_template(
    template_path: Path,
    main_content_html: str,
    last_updated: str = "March 16, 2026",
) -> str:
    html = template_path.read_text(encoding="utf-8")

    # Inject legal-prose styles before </style>
    if ".legal-prose" not in html:
        html = html.replace("</style>", LEGAL_PROSE_CSS + "\n    </style>")

    # Replace content inside <main>...</main>
    main_open = re.search(r"<main[^>]*>", html)
    main_close = re.search(r"</main>", html)
    if not main_open or not main_close:
        raise ValueError(f"Could not find <main> in {template_path}")

    before_main = html[: main_open.end()]
    after_main = html[main_close.start() :]

    new_main_body = f"""
      <p class="text-sm text-neutral-500 mb-6">
        Last updated: <span>{last_updated}</span>
      </p>
      <div class="legal-prose">
{main_content_html}
      </div>
"""
    return before_main + new_main_body + after_main


def main():
    privacy_md = DIR / "LEGAL_PRIVACY_EN.md"
    terms_md = DIR / "LEGAL_TERMS_EN.md"
    policy_html = DIR / "policy.html"
    tos_html = DIR / "tos.html"

    for md_path, out_path in [(privacy_md, policy_html), (terms_md, tos_html)]:
        if not md_path.exists():
            print(f"Skip: {md_path} not found", file=sys.stderr)
            continue
        content = convert_md_to_html(md_path)
        result = inject_content_into_template(out_path, content)
        out_path.write_text(result, encoding="utf-8")
        print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
