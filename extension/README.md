# kenboard quick-task — browser extension

Capture the current tab as a kenboard task with one keystroke. Sideload
for personal use (no Chrome Web Store).

## Download

Each tagged kenboard release attaches a ready-to-sideload zip to its
GitHub Release:

<https://github.com/lduchosal/kenboard/releases>

Pick the latest, download `kenboard-extension-<version>.zip`, unzip it
locally, then follow **Install** below pointing to the unzipped folder.

(Alternatively, clone the kenboard repo and point Load unpacked at
`extension/` directly — same content, just unversioned.)

## Install

### Chrome / Edge / Brave

1. Open `chrome://extensions/`
2. Toggle **Developer mode** (top-right)
3. Click **Load unpacked**
4. Select this `extension/` directory

### Firefox (temporary — for development)

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…**
3. Pick `extension/manifest.json`

Reload the extension after editing any file. **Note:** a temporary
add-on is dropped every time Firefox restarts — for a permanent install
use the signed `.xpi` below.

### Firefox (persistent)

Release Firefox only installs **signed** add-ons permanently. The
manifest carries a stable id (`browser_specific_settings.gecko.id`) so it
can be signed via Mozilla without publishing to the public store.

**Easiest:** tagged releases attach a signed `.xpi` (filename ends in
`-<version>.xpi`) next to the zip, when the publisher has AMO credentials
configured — grab it from
<https://github.com/lduchosal/kenboard/releases>, then jump to step 4.

To sign one yourself:

1. Create API credentials at
   <https://addons.mozilla.org/developers/addon/api/key/>.
2. Put them in a gitignored `.amo-credentials` file at the repo root
   (or export them as env vars):
   ```sh
   AMO_JWT_ISSUER="user:NNNN:NN"
   AMO_JWT_SECRET="…"
   ```
3. Sign in the **unlisted** channel (private — not listed on the store):
   ```sh
   sh scripts/sign-firefox-extension.sh
   ```
   This produces a signed `.xpi` in `web-ext-artifacts/` at the repo root.
4. In Firefox open `about:addons` → gear icon → **Install Add-on From
   File** → pick the `.xpi`. It now survives restarts.

(Fallback without an AMO account: Firefox **Developer Edition / Nightly /
ESR** can install an unsigned `.xpi` after setting
`xpinstall.signatures.required = false` in `about:config`. Release
Firefox cannot.)

## First-run

Click the extension icon → **Settings** (or right-click → *Options*):

| Field | What |
|---|---|
| **Onboarding link** | Fastest path: on a kenboard category, click **Copy onboard link**, paste it here — Base URL, Project ID and API token are filled in automatically. |
| **Base URL** | Your kenboard instance, e.g. `https://www.kenboard.2113.ch` |
| **API token** | Get one from `/admin/keys` on the kenboard (scope: at least `write` on the target project) |
| **Project ID** | UUID of the project tasks land in |
| **Default who** | Pre-fills the "who" field in the popup |

The onboarding link has the shape
`https://…/onboard/cat/<cat>/project/<project>?token=<key>`; pasting it
populates the three connection fields. Click **Test connection** to
validate, then **Save**.

## Use

### Quick task (popup)

- **Shortcut:** `Ctrl+Shift+K` (macOS: `Cmd+Shift+K`).
- **Or:** click the toolbar icon.

The popup pre-fills the title from the page title and the description with
a **structured text capture** of the page: source URL, meta description,
a heading outline (h1–h3), and any text you've selected on the page. Edit,
hit Save. Task lands as `todo` in the configured project.

## Notes

- The capture is **plain markdown text**, never an image — it stays small
  and keeps the board's task descriptions readable and the DB lean.
- The page outline / selection can't be read on `chrome://`, `about:`,
  `file://`, and some privileged pages. The popup still posts the task with
  just the title + source URL when scripting the page fails.
- Select text on the page before opening the popup to quote it in the task.
  Uncheck **Include page capture** to post only your note + the source URL.
- The API token is stored in `chrome.storage.local` (extension-scoped,
  not synced across devices). Treat it like a password.
- Reuses the standard kenboard `POST /api/v1/tasks` endpoint with bearer
  auth — no server-side changes needed for this extension to work.

### Annotate a page (#520)

Pile up quotes and notes across a page, then push them all to kenboard as
**one** markdown task — pure text, never an image.

- **Activate:** press `Alt+K` on any normal page. A small `kb · 0` badge
  appears at the top-right of the viewport.
- **Highlight:** select text. A small toolbar appears next to your
  selection with `🖍 Surligner`. Click it — the text is highlighted in
  place and the badge count goes up.
- **Open the drawer:** click the badge. A side drawer slides in from the
  right with the list of annotations for this page.
- **Push to kenboard:** click `Pousser sur kenboard` in the drawer
  footer. The extension posts a single task whose description is a
  markdown block: source link + one blockquote per highlight, each with
  a `[citer](URL#:~:text=…)` link that scrolls a fresh tab back to the
  exact quote.
- **Exit:** press `Esc` (closes the toolbar → drawer → annotation mode in
  that order).

Highlights persist locally per **canonical URL** (`chrome.storage.local`)
and are re-applied automatically on page reload or SPA route change. They
are never sent anywhere until you click *Pousser sur kenboard*.

The annotation UI lives inside a Shadow DOM so it can't be styled by the
host page and doesn't leak its own CSS into the page.
