#!/usr/bin/env python3
"""NetPaw static site generator — Python stdlib only.

Renders /root/wt-netpaw-site/out from GitHub at build time:
  - Home, Download, Docs (auto wiki), footer
  - install.ps1 (one-command MSI install w/ hash + signature check)

Env:
  GITHUB_TOKEN  optional; avoids API rate limits.
  OUT           output dir (default: out).
"""
import hashlib
import html
import json
import os
import re
import shutil
import urllib.request
from datetime import datetime, timezone

REPO = "smol-kitten/NetPaw"
API = f"https://api.github.com/repos/{REPO}"
RELEASES_URL = f"https://github.com/{REPO}/releases"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT", os.path.join(HERE, "out"))
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# User-facing docs rendered into the wiki sidebar (excluding internal ops docs:
# ACCESS, PLAN-*, GAP-*, RESEARCH — those carry internal pointers/credentials).
DOCS = [
    ("overview", "Overview", "README.md"),
    ("features", "Features", "docs/features.md"),
    ("usage", "Usage", "docs/usage.md"),
    ("enterprise", "Enterprise", "docs/ENTERPRISE.md"),
    ("pack-format", "Profile packs", "docs/PACK-FORMAT.md"),
    ("telemetry", "Telemetry", "docs/TELEMETRY.md"),
    ("signed-release", "Signed releases", "docs/signed-release.md"),
]


def api(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "netpaw-site-builder",
    })
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def raw_get(path):
    req = urllib.request.Request(RAW + "/" + path, headers={"User-Agent": "netpaw-site-builder"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "netpaw-site-builder"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def hsize(n):
    val = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024 or unit == "GB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= 1024
    return f"{val:.1f} GB"


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest().upper()


def rel_date(iso):
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return iso


def esc(s):
    return html.escape(str(s), quote=True)


def pprint_clip(label, code):
    return (
        "<div class='clip'>"
        f"<div class='clip-head'><span>{esc(label)}</span>"
        "<button type='button' class='copy' data-copy>Copy</button></div>"
        f"<pre><code>{esc(code)}</code></pre></div>"
    )


def layout(title, active, body):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="NetPaw — static-IP network profiles for Windows, one hotkey away. Direct downloads, verified hashes, and a signed one-command installer.">
<link rel="stylesheet" href="/static/css/site.css">
<link rel="icon" href="/static/img/paw.svg" type="image/svg+xml">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap topbar-in">
    <a class="brand" href="/">
      <img class="brand-paw" src="/static/img/paw.svg" alt="" width="24" height="24">
      <span>Net<b>Paw</b></span>
    </a>
    <nav class="nav" aria-label="Primary">
      <a href="/" class="{active == 'home' and 'on' or ''}">Home</a>
      <a href="/download/" class="{active == 'download' and 'on' or ''}">Download</a>
      <a href="/docs/" class="{active == 'docs' and 'on' or ''}">Docs</a>
      <a href="https://github.com/{REPO}" rel="noopener">GitHub</a>
    </nav>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="foot">
  <div class="wrap foot-in">
    <div class="foot-col">
      <img class="brand-paw" src="/static/img/paw.svg" alt="" width="20" height="20">
      <span class="foot-brand">Net<b>Paw</b></span>
      <p class="muted">Static-IP profiles for Windows network admins — free, MIT, open source.</p>
    </div>
    <nav class="foot-col" aria-label="Footer">
      <a href="https://github.com/{REPO}" rel="noopener">Repository</a>
      <a href="{RELEASES_URL}" rel="noopener">Releases</a>
      <a href="https://github.com/{REPO}/issues" rel="noopener">Issues</a>
    </nav>
    <div class="foot-col muted">
      <p>Static site. No trackers, no cookies, no JS needed to read it.</p>
      <a href="https://github.com/smol-kitten/netpaw-site" rel="noopener">This site's source</a>
    </div>
  </div>
  <div class="wrap foot-sub muted"><span>Rendered from GitHub at build time · MIT</span></div>
</footer>
<script src="/static/js/site.js"></script>
</body>
</html>
"""


def home_body(release):
    assets = release["assets"]
    msi = next((a for a in assets if a["name"].endswith(".msi") and "-telemetry" not in a["name"]), None)
    ver = release["tag_name"]
    date = rel_date(release["published_at"])
    msi_size = hsize(msi["size"]) if msi else "—"
    return f"""
    <section class="row">
      <div class="card">
        <h2>Why NetPaw</h2>
        <ul class="feat">
          <li><b>Switch networks in one keystroke.</b> Profiles per adapter — IP, gateway, DNS, routes, VLAN — from the tray.</li>
          <li><b>Diagnose, don't guess.</b> Info card shows what's wrong (link / gateway / DNS / internet) with plain-language advice and one-click fixes.</li>
          <li><b>Find things on the wire.</b> Network map, ARP neighbours, LLDP port, Wake-on-LAN, reach mode that jumps you onto an IP's subnet.</li>
          <li><b>Safe &amp; transparent.</b> Every change is a plain <code>netsh</code> command you can preview. Free (MIT), Windows 10/11, .NET 10.</li>
        </ul>
      </div>
    </section>

    <section class="row card hero-cta">
      <div>
        <h2>Get NetPaw {esc(ver)}</h2>
        <p class="muted">Released {date} · MSI installer · {msi_size} · signed from v0.13.1</p>
      </div>
      <div class="cta">
        <a class="btn" href="/download/">Download</a>
        <a class="btn ghost" href="/docs/">Read the docs</a>
      </div>
    </section>

    <section class="row card shots">
      <figure><img src="/static/img/panel.png" alt="NetPaw quick panel" loading="lazy"><figcaption>Quick panel — type a vendor, a profile, or an IP</figcaption></figure>
      <figure><img src="/static/img/main.png" alt="NetPaw main window" loading="lazy"><figcaption>Optional main window</figcaption></figure>
    </section>
    """


def download_body(release, hashes, older):
    ver = release["tag_name"]
    date = rel_date(release["published_at"])
    msi = next((a for a in release["assets"] if a["name"].endswith(".msi") and "-telemetry" not in a["name"]), None)
    msi_name = msi["name"] if msi else "NetPaw-<version>.msi"
    msi_url = msi["browser_download_url"] if msi else ""
    msi_size = hsize(msi["size"]) if msi else "—"
    msi_hash = hashes.get(msi_name, "")

    rows = []
    for a in sorted(release["assets"], key=lambda x: x["name"]):
        h = hashes.get(a["name"], "")
        hcell = f"<code class='sh'>{esc(h)}</code>" if h else "<span class='muted'>see SIGNATURES.md</span>"
        rows.append(f"<tr><td class='aname'>{esc(a['name'])}</td><td>{hsize(a['size'])}</td><td>{hcell}</td></tr>")

    older_rows = []
    for r in older[:15]:
        asize = ""
        for a in r.get("assets", []):
            if a["name"].endswith(".msi") and "-telemetry" not in a["name"]:
                asize = hsize(a["size"])
                break
        older_rows.append(
            f"<li><a href='{RELEASES_URL}/tag/{esc(r['tag_name'])}' rel='noopener'>{esc(r['tag_name'])}</a>"
            f" · {rel_date(r['published_at'])} · {asize} MSI</li>")
    older_html = ("<details class='older'><summary>Older releases</summary><ul>"
                  + "".join(older_rows) + "</ul></details>") if older_rows else ""

    return f"""
    <h1>Download NetPaw</h1>
    <p class="lead">Grab the installer, then verify it. Every file is served from GitHub Releases — this site never rehosts binaries.</p>

    <section class="card">
      <div class="latest-head">
        <h2>Latest release — {esc(ver)}</h2>
        <span class="pill">released {date}</span>
      </div>
      <p class="muted">Signed release files. Verification recipe: <a href="/docs/signed-release/" rel="noopener">docs/signed-release</a>.</p>
      <p><a class="btn sm" href="{RELEASES_URL}/tag/{esc(ver)}" rel="noopener">Release notes</a></p>
      <div class="table-scroll"><table>
        <thead><tr><th>File</th><th>Size</th><th>SHA-256</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table></div>
    </section>
    {older_html}

    <h2 id="install">Install</h2>

    <section class="card">
      <h3>A — winget (via catwinget)</h3>
      <p class="muted">Add the self-hosted catwinget source once, then install with winget. Dependencies (e.g. .NET Desktop Runtime) resolve in-source.</p>
      {pprint_clip("Add the catwinget source (once)", "winget source add --name catwinget --arg https://winget.goes.moe --type Microsoft.Rest")}
      {pprint_clip("Install NetPaw", "winget install smol-kitten.NetPaw --source catwinget")}
    </section>

    <section class="card">
      <h3>B — one-command MSI (PowerShell)</h3>
      <p class="muted">
        Downloads the latest MSI, checks its SHA-256 against the published value below, checks the Authenticode
        signature, then installs silently. From v0.13.1 the MSI is Authenticode-signed with the catboy.systems
        <b>staging</b> root — Windows may show "unknown publisher" until that root is imported. The same script
        is served as <code>/install.ps1</code>; the expanded version is shown below so you never pipe something
        you haven't read.
      </p>
      {pprint_clip("One command (download, verify, install)", 'powershell -Command "irm https://netpaw.catboy.systems/install.ps1 | iex"')}
      {pprint_clip("Verify only (download + hash + signature, no install)", 'powershell -Command "irm https://netpaw.catboy.systems/install.ps1 | iex -VerifyOnly"')}
      <details class="expanded"><summary>Show the expanded script — what the one-liner actually runs</summary>
{pprint_clip("install.ps1 (readable)", install_ps1(ver, msi_url, msi_hash))}
      </details>
    </section>

    <section class="card">
      <h3>C — manual</h3>
      <p class="muted">Download the MSI by hand, confirm the hash and signature, then install.</p>
      {pprint_clip("Download", f"curl -L -o NetPaw.msi https://github.com/{REPO}/releases/latest/download/{esc(msi_name)}")}
      {pprint_clip("Check SHA-256", "Get-FileHash NetPaw.msi -Algorithm SHA256")}
      {pprint_clip("Check signature", "Get-AuthenticodeSignature NetPaw.msi")}
      <p class="muted">Expected SHA-256 of <code>{esc(msi_name)}</code>: <code class="sh">{esc(msi_hash)}</code> · size {msi_size}. Install: <code>msiexec /i NetPaw.msi /qb</code>.</p>
    </section>

    <p class="muted">Notes: the MSI needs the <a href="https://dotnet.microsoft.com/download/dotnet/10.0" rel="noopener">.NET 10 Desktop Runtime</a> unless you use a standalone build. Only the <code>-telemetry</code> MSI contains telemetry code. The standalone <code>.zip</code> builds need no .NET at all.</p>
    """


def install_ps1(ver, url, sha256):
    return f"""<#
NetPaw one-command installer — {ver}
Downloads the MSI, verifies SHA-256, reports the Authenticode status, installs silently.
Use -VerifyOnly to check without installing.
#>
param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'

$url    = '{url}'
$sha256 = '{sha256}'

Write-Host 'Downloading NetPaw {ver} ...'
Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\\NetPaw-{ver}.msi"
$msi = "$env:TEMP\\NetPaw-{ver}.msi"

$got = (Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash.ToUpper()
if ($got -ne $sha256) {{
    Write-Error "SHA-256 mismatch:`n  expected {sha256}`n  got      $got"
    exit 1
}}
Write-Host "SHA-256 OK: $got"

$sig = Get-AuthenticodeSignature -LiteralPath $msi
Write-Host ("Signature status: " + $sig.Status)
if ($sig.Status -ne 'Valid') {{
    Write-Warning 'Not trusted by this machine (catboy.systems staging root). Optional:'
    Write-Warning '  iwr https://github.com/smol-kitten/netpaw/releases/latest/download/r0.crt -OutFile r0.crt'
    Write-Warning '  Import-Certificate -FilePath r0.crt -CertStoreLocation Cert:\\CurrentUser\\Root'
}}

if ($VerifyOnly) {{ Write-Host 'Verify-only: not installing.'; exit 0 }}

Write-Host 'Installing silently ...'
Start-Process msiexec.exe -ArgumentList '/i', $msi, '/quiet', '/norestart' -Wait
Write-Host 'NetPaw installed.'
"""


def strip_md(md):
    md = md.replace("\r\n", "\n")
    fence_re = re.compile(r"```(\w*)\n(.*?)```", re.S)
    fences = {}

    def hf(m):
        idx = len(fences)
        fences[idx] = f"<pre><code>{esc(m.group(2))}</code></pre>"
        return f"\x00{idx}\x00"

    md = fence_re.sub(hf, md)
    md = re.sub(r"`([^`]+)`", lambda m: f"<code>{esc(m.group(1))}</code>", md)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                lambda m: f"<a href='{esc(m.group(2))}'>{esc(m.group(1))}</a>", md)
    lines = md.split("\n")
    out = []
    in_list = False
    for line in lines:
        s = line.strip()
        if s == "":
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if s.startswith("#"):
            if in_list:
                out.append("</ul>")
                in_list = False
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{min(level,4)}>{esc(line.lstrip('#').strip())}</h{min(level,4)}>")
        elif re.match(r"^[-*] ", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{s[2:].strip()}</li>")
        elif re.match(r"^\d+\.", s):
            if not in_list:
                out.append("<ol>")
                in_list = True
            out.append(f"<li>{re.sub(r'^\\d+\\.\\s*', '', s)}</li>")
        elif s.startswith(">"):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<blockquote>{esc(s.lstrip('>').strip())}</blockquote>")
        elif s.startswith("|"):
            if set(s.replace("|", "").strip()) == set("-:") or set(s.replace("|", "").strip()) <= set("-:"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not out or not out[-1].startswith("<p") and not out[-1].startswith("<table"):
                out.append("<table><tr>" + "".join(f"<th>{esc(c)}</th>" for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{s}</p>")
    if in_list:
        out.append("</ul>")
    text = "\n".join(out)
    for idx, htmlblk in fences.items():
        text = text.replace(f"\x00{idx}\x00", htmlblk)
    return text


def main():
    os.makedirs(OUT, exist_ok=True)
    releases = api("/releases?per_page=30")
    release = releases[0]
    older = [r for r in releases[1:] if not r.get("prerelease")]
    ver = release["tag_name"]

    hashes = {}
    for a in release["assets"]:
        if a["name"] == "SIGNATURES.md":
            raw = fetch(a["browser_download_url"]).decode("utf-8", "replace")
            for line in raw.splitlines():
                m = re.match(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-fA-F]{64})\s*\|", line)
                if m:
                    hashes[m.group(1)] = m.group(2).upper()
        elif a["name"].endswith(".winget.json"):
            try:
                wj = json.loads(fetch(a["browser_download_url"]))
                if wj.get("installerSha256"):
                    hashes[os.path.basename(wj["installerUrl"])] = wj["installerSha256"].upper()
            except Exception:
                pass
    # Fallback: compute hash of any small asset not already covered.
    for a in release["assets"]:
        if a["name"] in hashes or a["size"] > 5_000_000:
            continue
        try:
            hashes[a["name"]] = sha256_hex(fetch(a["browser_download_url"]))
        except Exception:
            pass

    # Vendor screenshots into static/img if absent.
    imgdir = os.path.join(HERE, "static", "img")
    os.makedirs(imgdir, exist_ok=True)
    for name in ("panel.png", "main.png"):
        dst = os.path.join(imgdir, name)
        if not os.path.exists(dst):
            try:
                data = fetch(f"https://raw.githubusercontent.com/{REPO}/main/docs/{name}")
                open(dst, "wb").write(data)
                print("vendored screenshot", name)
            except Exception as e:
                print("WARN screenshot", name, e)

    # Home
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(layout("NetPaw — static-IP profiles for Windows, one hotkey away", "home", f"""
        <section class="hero">
          <h1 class="hero-title">Switch networks <span class="grad">one hotkey</span> away.</h1>
          <p class="hero-sub">NetPaw is a tiny Windows tray app that swaps your static-IP profiles in a keystroke —
          and tells you <em>what's wrong</em> when it still doesn't work.</p>
          <div class="hero-cta">
            <a class="btn" href="/download/">Download for Windows</a>
            <a class="btn ghost" href="https://github.com/{REPO}" rel="noopener">View on GitHub</a>
          </div>
        </section>
        {home_body(release)}
        """))

    # Download
    dldir = os.path.join(OUT, "download")
    os.makedirs(dldir, exist_ok=True)
    with open(os.path.join(dldir, "index.html"), "w") as f:
        f.write(layout(f"Download NetPaw {ver}", "download", download_body(release, hashes, older)))

    # install.ps1
    msi = next((a for a in release["assets"] if a["name"].endswith(".msi") and "-telemetry" not in a["name"]), None)
    msi_url = msi["browser_download_url"] if msi else ""
    msi_name = msi["name"] if msi else "NetPaw.msi"
    msi_hash = hashes.get(msi_name, "")
    ps1 = "# NetPaw install.ps1 — the exact script shown on /download/. \n" + install_ps1(ver, msi_url, msi_hash)
    with open(os.path.join(OUT, "install.ps1"), "w") as f:
        f.write(ps1)

    # Docs wiki
    os.makedirs(os.path.join(OUT, "docs"), exist_ok=True)
    docindex = "".join(f"<li><a href='/docs/{s}/'>{esc(t)}</a></li>" for (s, t, _) in DOCS)
    with open(os.path.join(OUT, "docs", "index.html"), "w") as f:
        f.write(layout("NetPaw Docs", "docs", f"""
        <h1>Documentation</h1>
        <p class="lead">The NetPaw wiki renders the project's README and docs straight from GitHub at build time. Each page links back to its source file and commit.</p>
        <div class="card doc-index"><ul>{docindex}</ul></div>
        """))
    for slug, title, path in DOCS:
        body = strip_md(raw_get(path))
        commit = ""
        try:
            c = api(f"/commits?path={path}&per_page=1")
            commit = c[0]["sha"][:12] if c else ""
        except Exception:
            pass
        sidebar = "".join(
            f"<li><a href='/docs/{s}/' class='{'on' if s == slug else ''}'>{esc(t)}</a></li>"
            for (s, t, _) in DOCS)
        pagetext = f"""
        <div class="docs-layout">
          <aside class="docs-side"><nav><ul>{sidebar}</ul></nav></aside>
          <article class="docs-body docs-prose">{body}
            <div class="doc-meta muted">Source: <a href="https://github.com/{REPO}/blob/main/{esc(path)}" rel="noopener">edit on GitHub</a> · commit <code>{esc(commit)}</code></div>
          </article>
        </div>"""
        p = os.path.join(OUT, "docs", slug, "index.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(layout(f"{title} · NetPaw Docs", "docs", pagetext))

    # static -> out/static
    if os.path.exists(os.path.join(HERE, "static")):
        shutil.copytree(os.path.join(HERE, "static"), os.path.join(OUT, "static"), dirs_exist_ok=True)
    print("Latest:", ver, "| hashes for:", sorted(hashes))
    print("build complete ->", OUT)


if __name__ == "__main__":
    main()
