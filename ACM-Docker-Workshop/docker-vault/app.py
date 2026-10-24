import html
import json
from pathlib import Path

import markdown
from shiny import reactive
from shiny.express import input, render, session, ui

ROOT = Path("/app/notes")
ROOT.mkdir(parents=True, exist_ok=True)
if not any(ROOT.rglob("*.md")):
    (ROOT / "welcome.md").write_text("# Welcome\n\nEdit me!")


def safe(rel: str):
    """Resolve a browser-supplied path, refusing anything outside ROOT."""
    p = (ROOT / rel).resolve()
    return p if p == ROOT or ROOT in p.parents else None


def notes():
    return sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.md"))


def call(input_id, rel):
    """A Shiny input update, escaped so it survives inside an HTML attribute."""
    return html.escape(f"Shiny.setInputValue('{input_id}', {json.dumps(rel)}, {{priority:'event'}});", quote=True)


def unique(folder: str, stem: str, ext: str = ".md") -> Path | None:
    i = 1
    while True:
        p = safe(f"{folder}{stem}_{i}{ext}" if folder else f"{stem}_{i}{ext}")
        if p is None:
            return None
        if not p.exists():
            return p
        i += 1


def free_name(p: Path) -> Path:
    """p, or p with a (2), (3)... suffix if something is already there."""
    if not p.exists():
        return p
    i = 2
    while (cand := p.with_name(f"{p.stem} ({i}){p.suffix}")).exists():
        i += 1
    return cand


def row(name, rel, is_dir, children=""):
    esc = html.escape(rel, quote=True)
    menu = (
        "<span class='menu-wrap'>"
        f"<button class='dots' onclick=\"toggleMenu(event, this)\" title='Options'>&#8942;</button>"
        "<div class='menu-items'>"
    )
    if is_dir:
        menu += (
            f"<a onclick=\"{call('new_note', rel)}\">New note</a>"
            f"<a onclick=\"{call('new_folder', rel)}\">New folder</a>"
            f"<a onclick=\"{call('delete_dir', rel)}\">Delete</a>"
        )
    else:
        menu += (
            f"<a onclick=\"{call('copy_req', rel)}\">Copy</a>"
            f"<a onclick=\"{call('dl_req', rel)}\">Download</a>"
            f"<a onclick=\"{call('delete', rel)}\">Delete</a>"
        )
    menu += "</div></span>"

    if is_dir:
        return (
            f"<details open class='tree-details'><summary class='tree-sum'>"
            f"<span class='tree-name folder' data-rel='{esc}' draggable='true'>{html.escape(name)}</span>"
            f"{menu}</summary><div class='tree-children'>{children}</div></details>"
        )
    return (
        f"<div class='tree-row'>"
        f"<a class='tree-name file' href='#' data-rel='{esc}' draggable='true' onclick=\"{call('open', rel)}\">{html.escape(name)}</a>"
        f"{menu}</div>"
    )


def tree_html(d=ROOT, prefix=""):
    dirs, files = [], []
    for p in sorted(d.iterdir(), key=lambda p: p.name.lower()):
        rel = f"{prefix}{p.name}"
        if p.is_dir():
            dirs.append(row(p.name, rel + "/", True, tree_html(p, rel + "/")))
        else:
            files.append(row(p.name, rel, False))
    return "".join(dirs + files)


start = notes()[0] if notes() else ""
current = reactive.value(start)
download_rel = reactive.value("")
rev = reactive.value(0)
_counter = {"n": 0}


def bump():
    _counter["n"] += 1
    rev.set(_counter["n"])


ui.page_opts(title="Markdown Vault", fillable=True)

ui.tags.head(ui.tags.style("""
:root { --ink: #111; }
.tree-row { display: flex; align-items: center; gap: 8px; border-radius: 6px; }
.tree-row:hover { background: #f2f4f7; }
.tree-name { flex: 1 1 auto; min-width: 0; padding: 6px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; border-radius: 6px; text-decoration: none; color: var(--ink); cursor: pointer; }
.tree-name:hover { background: #e6ebf1; }
.tree-name.folder { font-weight: 600; }
.tree-sum { display: flex; align-items: center; gap: 8px; list-style: none; cursor: pointer; border-radius: 6px; }
.tree-sum:hover { background: #f2f4f7; }
.tree-sum::-webkit-details-marker { display: none; }
.tree-sum::before { content: "▸"; font-size: 11px; width: 12px; color: var(--ink); }
.tree-details[open] > .tree-sum::before { content: "▾"; }
.tree-children { margin-left: 15px; border-left: 2px solid var(--ink); padding-left: 8px; }
.menu-wrap { position: relative; flex: 0 0 auto; }
.dots { border: 2px solid transparent; background: none; border-radius: 6px; font-size: 16px; line-height: 1; padding: 2px 8px; color: var(--ink); cursor: pointer; }
.dots:hover { border-color: var(--ink); background: #fff; }
.menu-items { display: none; position: absolute; right: 0; top: calc(100% + 4px); z-index: 20; min-width: 140px; padding: 5px; background: #fff; border: 2px solid var(--ink); border-radius: 8px; box-shadow: 0 8px 20px rgba(0,0,0,.15); }
.menu-wrap.open .menu-items { display: block; }
.menu-items a { display: block; padding: 8px 10px; border-radius: 5px; font-size: 13px; color: var(--ink); cursor: pointer; }
.menu-items a:hover { background: #eef2f6; }
.toolbar { display: flex; gap: 8px; margin-bottom: 10px; }
.toolbar .btn { flex: 1; border: 2px solid var(--ink); font-weight: 500; }
#tree { border: 2px solid var(--ink); border-radius: 8px; padding: 6px; margin-bottom: 12px; }
#editor { width: 100%; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 14px; line-height: 1.6; border: 2px solid var(--ink); }
#save { align-self: flex-start; margin-top: 10px; padding: 8px 26px; border: 2px solid var(--ink); font-weight: 600; }
.shiny-input-container.shiny-input-textarea { width: 100%; }
#preview { border: 2px solid var(--ink); border-radius: 8px; padding: 14px 18px; margin-top: 12px; background: #fff; }
.form-control, .form-select { border: 2px solid var(--ink); }
/* Shiny suspends outputs that never intersect the viewport, so this must stay
   1px on-screen rather than display:none; the download menu items click it. */
#download { position: fixed; top: 0; left: 0; width: 1px; height: 1px; padding: 0; border: 0; opacity: 0; overflow: hidden; pointer-events: none; }
"""))

with ui.layout_sidebar():
    with ui.sidebar(width=330):
        ui.h2("Notes")
        with ui.div(class_="toolbar"):
            ui.input_action_button("new_note", "New note", class_="btn-sm")
            ui.input_action_button("new_folder", "New folder", class_="btn-sm")

        @render.ui
        def tree():
            rev()
            return ui.HTML(tree_html() or "<div class='text-muted small'>No files yet</div>")

        ui.input_file("upload", "Upload .md", multiple=True, accept=[".md"])

    ui.input_text_area("editor", "", value=(ROOT / start).read_text() if start else "", rows=24)
    ui.input_action_button("save", "Save", class_="btn-primary")

    @render.ui
    def preview():
        return ui.HTML(markdown.markdown(input.editor() or "", extensions=["fenced_code", "tables"]))


ui.HTML("""
<script>
function toggleMenu(e, btn) {
  e.preventDefault(); e.stopPropagation();
  const wrap = btn.closest('.menu-wrap');
  document.querySelectorAll('.menu-wrap.open').forEach(w => { if (w !== wrap) w.classList.remove('open'); });
  wrap.classList.toggle('open');
}
document.addEventListener('click', () => document.querySelectorAll('.menu-wrap.open').forEach(w => w.classList.remove('open')));
Shiny.addCustomMessageHandler('get', (rel) => {
  const a = document.getElementById('download');
  if (a && a.getAttribute('href')) a.click();
});
Shiny.addCustomMessageHandler('copy', (text) => {
  const done = () => {
    const t = document.createElement('div');
    t.textContent = 'Copied to clipboard';
    t.style.cssText = 'position:fixed;bottom:16px;right:16px;background:#111;color:#fff;padding:8px 14px;border-radius:6px;font-size:13px;z-index:99';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 1400);
  };
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => {});
});
document.addEventListener('dragstart', (e) => {
  const el = e.target.closest('[data-rel]');
  if (el) { e.dataTransfer.setData('text/plain', el.dataset.rel); e.dataTransfer.effectAllowed = 'move'; }
});
document.addEventListener('dragover', (e) => {
  const el = e.target.closest('[data-rel]');
  if (el && el.classList.contains('folder')) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; el.style.outline = '2px solid #4c8bf5'; }
});
document.addEventListener('dragleave', (e) => {
  const el = e.target.closest('[data-rel]');
  if (el) el.style.outline = '';
});
document.addEventListener('drop', (e) => {
  const el = e.target.closest('[data-rel]');
  if (!el) return;
  e.preventDefault();
  el.style.outline = '';
  const src = e.dataTransfer.getData('text/plain');
  if (src) Shiny.setInputValue('drop', src + '|' + el.dataset.rel, {priority: 'event'});
});
</script>
""")


@render.download_button(filename=lambda: Path(download_rel() or current()).name or "note.md")
def download():
    p = safe(download_rel() or current())
    if p and p.is_file():
        yield p.read_bytes()


@reactive.effect
@reactive.event(input.open)
def _():
    p = safe(input.open())
    if p and p.is_file():
        current.set(p.relative_to(ROOT).as_posix())
        ui.update_text_area("editor", value=p.read_text())


@reactive.effect
@reactive.event(input.new_note)
def _():
    val = input.new_note()
    folder = val if isinstance(val, str) and val.endswith("/") else ""
    p = unique(folder, "untitled")
    if p:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {p.stem.replace('_', ' ')}\n")
        current.set(p.relative_to(ROOT).as_posix())
        ui.update_text_area("editor", value=p.read_text())
        bump()


@reactive.effect
@reactive.event(input.new_folder)
def _():
    val = input.new_folder()
    folder = val if isinstance(val, str) and val.endswith("/") else ""
    p = unique(folder, "folder", "")
    if p:
        p.mkdir(parents=True, exist_ok=True)
        bump()


@reactive.effect
@reactive.event(input.drop)
def _():
    src_rel, dst_rel = input.drop().split("|", 1)
    src, dst = safe(src_rel), safe(dst_rel)
    if not src or not dst:
        return
    if dst.is_file():
        dst = dst.parent
    if src.is_file() and src.parent != dst:
        dst.mkdir(parents=True, exist_ok=True)
        dst = free_name(dst / src.name)
        src.replace(dst)
        current.set(dst.relative_to(ROOT).as_posix())
        bump()


@reactive.effect
@reactive.event(input.delete)
def _():
    p = safe(input.delete())
    if p and p.is_file():
        p.unlink(missing_ok=True)
        if current() == input.delete():
            current.set("")
            ui.update_text_area("editor", value="")
        bump()


@reactive.effect
@reactive.event(input.delete_dir)
def _():
    p = safe(input.delete_dir())
    if p and p.is_dir() and not any(p.iterdir()):
        p.rmdir()
        bump()


@reactive.effect
@reactive.event(input.copy_req)
async def _():
    p = safe(input.copy_req())
    if p and p.is_file():
        await session.send_custom_message("copy", p.read_text())


@reactive.effect
@reactive.event(input.dl_req)
async def _():
    download_rel.set(input.dl_req())
    await session.send_custom_message("get", input.dl_req())


@reactive.effect
@reactive.event(input.save)
def _():
    p = safe(current())
    if p and p.is_file():
        p.write_text(input.editor())


@reactive.effect
@reactive.event(input.upload)
def _():
    for f in input.upload() or []:
        (ROOT / Path(f["name"]).name).write_text(Path(f["datapath"]).read_text())
    bump()
