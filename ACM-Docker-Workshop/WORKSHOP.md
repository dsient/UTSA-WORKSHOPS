# Docker Workshop (Tailscale \+ Caddy Edition)

## 1\. Project Setup

```sh
mkdir docker-vault && cd docker-vault
```

&nbsp;

## 2\. Create app.py

**Create a file named app.py and paste the following Shiny Express application:**

*(Shiny Express needs no `ui.output_ui`: a render function is placed where it is defined. And reactive values cannot be read at module level — there is no session yet — so the first note list is read straight from disk.)*

```py
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
```

&nbsp;

## 3\. Create requirements.txt, Dockerfile, and serve.json

```sh
echo "shiny==1.8.0" > requirements.txt
echo "markdown==3.11.2" >> requirements.txt
```

&nbsp;

**Create a file named `Dockerfile` and paste:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN mkdir -p /app/notes
EXPOSE 5000
CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "5000", "app.py"]
```

&nbsp;

**Create a file named `serve.json` in the project folder:**

```json
{
  "TCP": {
    "443": { "HTTPS": true }
  },
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": {
        "/": {
          "Proxy": "http://caddy:80"
        }
      }
    }
  }
}
```

*(TS\_CERT\_DOMAIN is a built-in Tailscale variable for your MagicDNS name.)*

&nbsp;

## 4\. Build and Run with a Named Volume (Local Access)

```sh
docker build -t my-vault .
docker run -d -p 5000:5000 -v vault_data:/app/notes --name vault my-vault
```

&nbsp;

Open [http\://localhost:5000](http://localhost:5000). Create a folder with **New folder**, a note with **New note**, drag a note into the folder, open the `⋮` menu for **Copy** / **Download** / **Delete**, and watch the markdown preview update live as you type.

Add or edit a note, then stop and remove the container:

```sh
docker stop vault && docker rm vault
# Re-run with the same volume:
docker run -d -p 5000:5000 -v vault_data:/app/notes --name vault my-vault
```

&nbsp;

**Your notes are still there. The volume outlives the container.**

*`"The named volume is initialized from the image's /app/notes content (the welcome note). After that, the volume takes over. Destroying the container doesn't delete the volume."`*

&nbsp;

## 5\. Switch to Multi-Container Compose with Tailscale & Caddy

**Create a file named compose.yaml:**

```yaml
services:
  vault:
    build: .
    volumes:
      - vault_data:/app/notes
    expose:
      - "5000"

  caddy:
    image: caddy:2-alpine
    command: caddy reverse-proxy --from :80 --to vault:5000
    expose:
      - "80"
    depends_on:
      - vault

  tailscale:
    image: tailscale/tailscale:latest
    hostname: docker-vault
    environment:
      - TS_CLIENT_ID=${TS_CLIENT_ID}
      - TS_CLIENT_SECRET=${TS_CLIENT_SECRET}
      - TS_EXTRA_ARGS=--advertise-tags=tag:container
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_SERVE_CONFIG=/config/serve.json
    volumes:
      - tailscale_state:/var/lib/tailscale
      - ./serve.json:/config/serve.json:ro
    depends_on:
      - caddy

volumes:
  vault_data:
  tailscale_state:
```

&nbsp;

*(Compose prefixes volume names with the project name, so this stack starts with its own empty `docker-vault\_vault\_data` volume. The notes you made in section 4 live in the standalone `vault\_data` volume.)*

&nbsp;

### Set up Tailscale and Caddy:

**IMPORTANT: Instead of a standard auth key that expires after 90 days, we use an OAuth client. This credential never expires, so you don't need to rotate keys.**

&nbsp;

First, create your OAuth client in the Tailscale admin console:

**1\. Go to Access Controls \> Tags and create a tag named "container".**

**2\. Go to Settings \> Trust Credentials and add an OAuth client.**

**3\. Give it a name, select these custom scopes:**

![][image1]

![][image2]

Leave every other scope unchecked. Extra scopes will prevent the credential from working as a device auth key.

**4\. Copy the generated Client ID and Client Secret.**

*Set these environment variables (or create a .env file):*

```sh
export TS_CLIENT_ID="your-client-id-here"
export TS_CLIENT_SECRET="tskey-client-your-secret-here"
```

&nbsp;

**Start the stack:**

```sh
docker compose up -d
```

&nbsp;

**Find your MagicDNS name:**

```sh
docker compose exec tailscale tailscale serve status
```

The first line prints your URL, for example:

`https://docker-vault.tail12345.ts.net (tailnet only)`

*(The `hostname: docker-vault` line in compose.yaml is what makes the name predictable. If a previous node with the same name is still registered, Tailscale appends a suffix such as `docker-vault-1` — use whatever the command prints. It is also listed under Machines in the admin console.)*

**Open that URL from any device on your tailnet. Caddy and Tailscale handle HTTPS automatically.**

*"Caddy proxies to vault:5000 using Docker's internal DNS. Tailscale joins your private network and exposes only Caddy; not the vault directly; to the tailnet. This is a common production pattern: a sidecar handles ingress, while the app stays on an internal network."*

**Stop everything:**

`docker compose down`

&nbsp;

**The vault\_data volume persists.&nbsp;**

**The tailscale\_state volume keeps the Tailscale login state, so restarts do not need to re-register from scratch.**

&nbsp;

**Because we used an OAuth client, the Tailscale container will reconnect automatically on subsequent docker compose up commands without any manual intervention or key rotation.**

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>