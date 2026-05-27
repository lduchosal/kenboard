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

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…**
3. Pick `extension/manifest.json`

Reload the extension after editing any file.

## First-run

Click the extension icon → **Settings** (or right-click → *Options*):

| Field | What |
|---|---|
| **Base URL** | Your kenboard instance, e.g. `https://www.kenboard.2113.ch` |
| **API token** | Get one from `/admin/keys` on the kenboard (scope: at least `write` on the target project) |
| **Project ID** | UUID of the project tasks land in |
| **Default who** | Pre-fills the "who" field in the popup |

Click **Test connection** to validate. Save.

## Use

- **Shortcut:** `Ctrl+Shift+K` (macOS: `Cmd+Shift+K`).
- **Or:** click the toolbar icon.

The popup pre-fills the title from the page title and the description with
the source URL + a PNG screenshot of the visible viewport. Edit, hit Save.
Task lands as `todo` in the configured project.

## Notes

- Screenshots can't be captured on `chrome://`, `about:`, `file://`, and
  some Web Store / privileged pages. The popup still posts the task without
  the image when capture fails.
- The screenshot is embedded as a base64 data-URL in the task description.
  Large captures (>~200 KB) may hit kenboard's description size limit —
  uncheck **Include screenshot** if the POST fails on big pages.
- The API token is stored in `chrome.storage.local` (extension-scoped,
  not synced across devices). Treat it like a password.
- Reuses the standard kenboard `POST /api/v1/tasks` endpoint with bearer
  auth — no server-side changes needed for this extension to work.
