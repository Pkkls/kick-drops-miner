# Kick Drops Miner

Windows desktop app that automatically progresses the watch-time required to
unlock **Kick drops** (rewards tied to watching a stream): scans active
campaigns, lets you pick channels to watch, plays them automatically (AFK,
muted), and shows live progress.

Inspired by [HyperBeats/KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner).

![status](https://img.shields.io/badge/status-MVP-orange) ![platform](https://img.shields.io/badge/platform-Windows-blue) ![python](https://img.shields.io/badge/python-3.10%2B-green)

---

## Table of contents

- [What it does](#what-it-does)
- [Privacy guarantees](#privacy-guarantees)
- [Installation](#installation)
- [Step-by-step tutorial](#step-by-step-tutorial)
- [Technical architecture](#technical-architecture)
- [Technical glossary](#technical-glossary)
- [Troubleshooting](#troubleshooting)
- [Disclaimer](#disclaimer)

---

## What it does

| Feature | Detail |
|---|---|
| **Campaign scan** | Lists all active drop campaigns on Kick (game, rewards, eligible channels). |
| **Mining queue** | Add Kick channels to a list, each with a minutes target. |
| **Automated playback** | A dedicated Chrome opens the channel, mutes it, and lets it play until the target is reached. |
| **Live/offline status** | Each channel in the list shows in real time whether the streamer is live. |
| **Drag-and-drop** | Reorder the queue by dragging rows with the mouse. |
| **Drop progress** | Shows real progress for each campaign (via your connected account). |

## Privacy guarantees

- **No third-party server, no telemetry.** The only network peer is Kick.
- **Egress allowlist enforced in code** (`core/egress.py`): every HTTP request
  and Chrome navigation goes through `assert_allowed()`, which only permits
  `*.kick.com` and raises an error (`EgressError`) on anything else.
- **Local login**: you sign in inside a dedicated Chrome window, isolated from
  your main browser. Session cookies stay on your disk (`data/`, git-ignored)
  and are never sent anywhere except to Kick.
- **Open, auditable code.**

This is not an OS-level firewall — it's an application-level barrier in the
code. For external proof, run the app behind a proxy (mitmproxy / Fiddler):
only `kick.com` should ever show up in the traffic.

## Installation

Requirements: **Windows 10/11**, **Python 3.10+**, **Google Chrome** installed.

```powershell
git clone https://github.com/Pkkls/kick-drops-miner.git
cd kick-drops-miner
run.bat
```

`run.bat` creates the virtual environment, installs dependencies, and launches
the app — just double-click it for every later launch.

Manual installation (equivalent):

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
<img width="991" height="789" alt="image" src="https://github.com/user-attachments/assets/82f8b3c4-42a6-4074-9609-a2e72e938a26" />
<img width="1048" height="780" alt="image" src="https://github.com/user-attachments/assets/9973cb2b-e48f-4d87-b7bf-b47f72ba8ea4" />
A very small browser windows will  open , in 144p <img width="498" height="344" alt="image" src="https://github.com/user-attachments/assets/c7cc250b-09c8-471f-a05b-6947374c7b8e" />
This terminal has to stay open <img width="598" height="211" alt="image" src="https://github.com/user-attachments/assets/4f860cbf-950e-499e-8280-e6377837d863" />

## Step-by-step tutorial

### 1. Sign in to Kick

Click **"Sign in (cookies)"** in the sidebar.

- The app first tries to automatically import your session if you're already
  logged in to Chrome or Brave on this machine.
- If automatic import fails (the most common case — see the
  [glossary](#technical-glossary) on cookie encryption), a dedicated Chrome
  window opens: log in normally to Kick in that window, then close it.
  Cookies are saved automatically.
- Once connected, your Kick username appears in green under the button.

### 2. Check available drop campaigns

Click **"Drop campaigns"**. The window lists every active campaign: game,
rewards, and your progress if you're logged in.

### 3. Add channels to the queue

Click **"Add link"**, paste a Kick URL (`https://kick.com/streamer_name`),
choose a minutes target. Repeat for every channel you want to mine.

Double-click a URL in the list to open it in your browser (useful to check
the content before starting).

### 4. Reorder the queue (optional)

Drag a row up or down with the mouse to change the play order.

### 5. Start mining

Click **"Start queue"**. The app:
1. Checks that the first channel is actually live (status shown in the column).
2. Opens a dedicated headless Chrome, loads the session, and plays the stream muted.
3. Once the minutes target is reached, moves on to the next channel.
4. If a channel is offline, it's flagged and retried later.

Only one stream runs at a time (a server-side limitation on Kick's end).

### 6. Stop

**"Stop selection"** stops the currently running stream without touching the
rest of the queue.

## Technical architecture

```
ui/app.py        → Interface (customtkinter), mining queue, live/offline display
core/api.py       → Direct HTTP calls to the Kick API (campaigns, progress, live status)
core/worker.py    → StreamWorker: drives a headless Chrome to watch a stream
core/browser.py   → Chrome driver creation (undetected-chromedriver) + cookie handling
core/egress.py    → Network allowlist: blocks any destination outside *.kick.com
core/config.py    → Local config persistence (data/config.json)
utils/helpers.py  → Shared helpers (paths, URL parsing, translations)
```

**Why a real Chrome instead of plain HTTP requests?**
Kick is protected by Cloudflare. A bare HTTP request (no real browser) gets
blocked. For *reads* (campaigns, progress, live status), the app works around
this by sending the right headers and session cookies directly over HTTP — no
browser needed there. But to actually *progress* a drop's watch-time, Kick
requires a real video player running in a logged-in browser — hence the
dedicated headless Chrome used for mining.

**Why exclude Cloudflare cookies (`__cf_bm`, `_cfuvid`, `cf_clearance`) when
injecting a session?**
Those cookies are tied to the fingerprint of the browser that obtained them
(IP, user-agent, behavior). Re-injecting them into a *different* browser (the
app's dedicated Chrome) breaks that new browser's Cloudflare validation. Only
the actual Kick auth cookies (`session_token`, `kick_session`, etc.) are
reused; Cloudflare issues its own fresh cookies for the new Chrome session.

## Technical glossary

| Term | Explanation |
|---|---|
| **Selenium** | A library that lets code drive a browser (open a page, click, read content) as if a human were doing it. |
| **undetected-chromedriver (UC)** | A modified Selenium variant so sites can't tell a script is driving the browser (sites often block standard "automated" browsers). |
| **Headless** | Chrome running with no visible window — used for mining in the background. |
| **Cloudflare** | The anti-bot/anti-DDoS service Kick uses. It analyzes browser behavior and blocks requests that look like an automated script. |
| **Cookie** | A small piece of data a site stores in your browser to remember you (logged-in session, preferences). Stealing or reusing a session cookie can let someone impersonate an account — hence the care taken to never expose them. |
| **DPAPI** | Windows' "Data Protection API": the encryption system Chrome/Brave use to protect cookies stored on disk, tied to the Windows user account. |
| **session_token / kick_session** | Cookies that identify your logged-in Kick session. These are the only ones reused by the app to authenticate against the API. |
| **Egress allowlist** | A whitelist of allowed network destinations. Here, only `*.kick.com` — any attempt at another domain is blocked by the code itself (`core/egress.py`). |
| **Watch-time** | Cumulative stream viewing time, tracked server-side by Kick, which unlocks drops once a campaign's threshold is reached. |
| **AFK (Away From Keyboard)** | Here: leaving a stream playing with no human interaction to accumulate watch-time. |
| **Drag-and-drop** | Dragging an item with the mouse to move it (used to reorder the mining queue). |

## Troubleshooting

- **"Sign in" opens Chrome then closes immediately**: make sure Chrome is
  installed and up to date. The app auto-detects the installed version.
- **Every stream shows "OFFLINE" even though they're live**: your session has
  probably expired — sign in again via "Sign in (cookies)".
- **"Start queue" does nothing**: check the live status shown in the column;
  if everything is marked OFFLINE, the queue is waiting for a channel to go
  live before starting.
- **Automatic cookie import fails**: this is expected on recent Chrome
  (stronger cookie encryption, "v20"). The app automatically falls back to
  the manual login window.

## Disclaimer

Automated AFK drop mining violates Kick's terms of service. Use at your own
risk (the account involved may be subject to action).
