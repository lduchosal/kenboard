// kenboard annotations — content script (#520).
//
// Layout of this file (one self-contained MV3 content script):
//   1.  constants (storage keys, ids, CSS)
//   2.  state
//   3.  URL + storage helpers
//   4.  Shadow DOM host (encapsulated CSS for our UI)
//   5.  highlight rendering (in-page <span>, not in shadow)
//   6.  re-apply on page load + on SPA route change
//   7.  selection adder (floating toolbar)
//   8.  badge (top-right pill, count)
//   9.  drawer (annotation list + push button)
//  10.  markdown push to /api/v1/tasks
//  11.  activation flow (Alt+K toggle, ESC to exit, popup message)
//  12.  bootstrap

import { fromRange as quoteFromRange, toRange as quoteToRange } from "dom-anchor-text-quote";
import { fromRange as posFromRange, toRange as posToRange } from "dom-anchor-text-position";

import { buildMarkdown } from "./buildMarkdown.js";

// ---------- 1. constants ----------

const STORAGE_PREFIX = "kb_anno:";
const HOST_ID = "kb-annotate-root";
const PAGE_STYLE_ID = "kb-annotate-page-style";
const HL_CLASS = "kb-hl";
const Z = 2147483647; // max int32 — sits above everything

// CSS injected into the Shadow DOM (encapsulated). Owns the badge, adder,
// drawer. None of these rules leak into the page.
const SHADOW_CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  button { font: inherit; cursor: pointer; }

  .badge {
    position: fixed; top: 16px; right: 16px; z-index: ${Z};
    display: none; align-items: center; gap: 6px;
    background: #ffffff; color: #1f2328;
    border: 1px solid #d0d7de; border-radius: 999px;
    padding: 4px 10px; font-size: 12px; font-weight: 600;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
    user-select: none;
  }
  .badge.on { display: inline-flex; }
  .badge:hover { background: #f6f8fa; }
  .badge-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #0969da;
  }

  .adder {
    position: fixed; z-index: ${Z};
    display: none; gap: 4px;
    background: #1f2328; color: #ffffff;
    border-radius: 6px; padding: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  }
  .adder.on { display: inline-flex; }
  .adder-btn {
    background: transparent; color: inherit; border: 0;
    padding: 4px 10px; border-radius: 4px; font-size: 12px;
  }
  .adder-btn:hover { background: rgba(255,255,255,0.12); }
  .adder-btn.dismiss { padding: 4px 8px; color: rgba(255,255,255,0.55); }

  .drawer {
    position: fixed; top: 0; right: 0; height: 100vh; width: 320px;
    z-index: ${Z};
    background: #ffffff; color: #1f2328;
    border-left: 1px solid #d0d7de;
    box-shadow: -4px 0 16px rgba(0,0,0,0.10);
    transform: translateX(100%); transition: transform 180ms ease-out;
    display: flex; flex-direction: column;
  }
  .drawer.open { transform: translateX(0); }
  @media (prefers-reduced-motion: reduce) {
    .drawer { transition: none; }
  }
  .drawer-header { padding: 12px 16px; border-bottom: 1px solid #d0d7de; }
  .drawer-title { font-size: 13px; font-weight: 600; margin-bottom: 2px; word-break: break-word; }
  .drawer-url { font-size: 11px; color: #57606a; word-break: break-all; }
  .drawer-count { font-size: 11px; color: #57606a; margin-top: 4px; }
  .drawer-close {
    position: absolute; top: 8px; right: 8px;
    background: transparent; border: 0; color: #57606a;
    width: 24px; height: 24px; border-radius: 50%; font-size: 14px;
  }
  .drawer-close:hover { background: #f6f8fa; }
  .drawer-list { flex: 1; overflow-y: auto; padding: 8px 0; }
  .drawer-empty { padding: 16px; color: #57606a; font-size: 12px; text-align: center; }
  .drawer-item {
    padding: 8px 16px; border-bottom: 1px solid #f0f2f5;
    display: flex; gap: 8px; align-items: flex-start;
  }
  .drawer-item:hover { background: #f6f8fa; }
  .drawer-quote {
    flex: 1; font-size: 12px; line-height: 1.4;
    border-left: 3px solid rgba(9,105,218,0.4); padding-left: 8px;
    color: #1f2328;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .drawer-del {
    background: transparent; border: 0; color: #cf222e; font-size: 13px;
    padding: 2px 6px; border-radius: 4px; opacity: 0.6;
  }
  .drawer-del:hover { background: rgba(207,34,46,0.10); opacity: 1; }
  .drawer-footer { padding: 12px 16px; border-top: 1px solid #d0d7de; }
  .drawer-push {
    width: 100%; background: #0969da; color: #ffffff; border: 0;
    padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;
  }
  .drawer-push:hover:not(:disabled) { background: #0860c4; }
  .drawer-push:disabled { background: #adbac7; cursor: not-allowed; }
  .drawer-status { font-size: 11px; color: #57606a; margin-top: 6px; min-height: 14px; }
  .drawer-status.success { color: #1a7f37; }
  .drawer-status.error { color: #cf222e; }
`;

// CSS injected into the *page* (not shadow) — styles the highlight spans
// we wrap around selected text. mix-blend-mode keeps the highlight visible
// on both light and dark backgrounds.
const PAGE_CSS = `
  .${HL_CLASS} {
    background-color: rgba(9, 105, 218, 0.22);
    mix-blend-mode: multiply;
    border-radius: 2px;
    box-shadow: 0 1px 0 rgba(9, 105, 218, 0.35);
    cursor: pointer;
  }
`;

// ---------- 2. state ----------

let mode = false;
/** @type {Array<{id:number, quote:any, position:any, createdAt:string}>} */
let annotations = [];
let host = null;
let shadow = null;
let badgeEl = null;
let adderEl = null;
let drawerEl = null;
let drawerStatusEl = null;
let drawerPushBtn = null;
let nextId = 1;
let currentRange = null;
let selectionDebounce = null;
let lastUrl = "";

// ---------- 3. URL + storage helpers ----------

/** Strip tracking params (utm_*, fbclid, gclid, mc_*) from a URL. */
function stripTrackingParams(u) {
  try {
    const url = new URL(u);
    const drop = [];
    url.searchParams.forEach((_, k) => {
      if (k.startsWith("utm_") || k.startsWith("mc_") || k === "fbclid" || k === "gclid" || k === "yclid") {
        drop.push(k);
      }
    });
    for (const k of drop) url.searchParams.delete(k);
    return url.toString();
  } catch {
    return u;
  }
}

function canonicalUrl() {
  const link = document.querySelector('link[rel="canonical"]');
  if (link?.href) return stripTrackingParams(link.href);
  return stripTrackingParams(location.origin + location.pathname + location.search);
}

function storageKey() {
  return STORAGE_PREFIX + canonicalUrl();
}

/** Build a text-fragment URL that scrolls a fresh tab to the quoted text. */
function textFragmentUrl(quote) {
  const exact = String(quote?.exact ?? "").slice(0, 200);
  if (!exact) return null;
  return canonicalUrl() + "#:~:text=" + encodeURIComponent(exact);
}

async function loadAnnotations() {
  const key = storageKey();
  const data = await chrome.storage.local.get(key);
  annotations = Array.isArray(data[key]) ? data[key] : [];
  // Make sure nextId stays unique within this page session.
  for (const a of annotations) if (a.id >= nextId) nextId = a.id + 1;
}

async function saveAnnotations() {
  const key = storageKey();
  await chrome.storage.local.set({ [key]: annotations });
}

// ---------- 4. Shadow DOM host ----------

function ensureHost() {
  if (host) return;
  host = document.createElement("div");
  host.id = HOST_ID;
  // Inline reset so the page can't style us before the Shadow DOM is built.
  host.style.cssText = `all: initial; position: static; z-index: ${Z};`;
  document.documentElement.appendChild(host);
  shadow = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = SHADOW_CSS;
  shadow.appendChild(style);

  // Page-level highlight CSS (must live outside the shadow to style page DOM).
  if (!document.getElementById(PAGE_STYLE_ID)) {
    const pageStyle = document.createElement("style");
    pageStyle.id = PAGE_STYLE_ID;
    pageStyle.textContent = PAGE_CSS;
    (document.head || document.documentElement).appendChild(pageStyle);
  }
}

// ---------- 5. highlight rendering ----------

/**
 * Wrap each text-node slice of ``range`` in a <span class="kb-hl">. Robust
 * across element boundaries (which surroundContents() can't handle).
 */
function wrapRange(range, dataId) {
  const ancestor = range.commonAncestorContainer;
  const root = ancestor.nodeType === Node.ELEMENT_NODE ? ancestor : ancestor.parentNode;
  if (!root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  /** @type {Text[]} */
  const inRange = [];
  while (walker.nextNode()) {
    const n = /** @type {Text} */ (walker.currentNode);
    if (range.intersectsNode(n)) inRange.push(n);
  }
  for (let n of inRange) {
    let startOffset = 0;
    let endOffset = n.length;
    if (n === range.startContainer) startOffset = range.startOffset;
    if (n === range.endContainer) endOffset = range.endOffset;
    if (startOffset >= endOffset) continue;

    let target = n;
    if (startOffset > 0) {
      target = n.splitText(startOffset);
      endOffset -= startOffset;
    }
    if (endOffset < target.length) {
      target.splitText(endOffset);
    }
    // Don't wrap inside our own host or other kb-hl spans.
    if (host && host.contains(target)) continue;
    if (target.parentElement?.classList.contains(HL_CLASS)) continue;

    const span = document.createElement("span");
    span.className = HL_CLASS;
    span.dataset.kbId = String(dataId);
    const parent = target.parentNode;
    if (!parent) continue;
    parent.insertBefore(span, target);
    span.appendChild(target);
  }
}

function unwrapHighlight(id) {
  const spans = document.querySelectorAll(`.${HL_CLASS}[data-kb-id="${id}"]`);
  for (const s of spans) {
    const parent = s.parentNode;
    if (!parent) continue;
    while (s.firstChild) parent.insertBefore(s.firstChild, s);
    parent.removeChild(s);
  }
}

function unwrapAllHighlights() {
  for (const s of document.querySelectorAll(`.${HL_CLASS}`)) {
    const parent = s.parentNode;
    if (!parent) continue;
    while (s.firstChild) parent.insertBefore(s.firstChild, s);
    parent.removeChild(s);
  }
}

// ---------- 6. anchor / re-apply ----------

function reapplyAll() {
  for (const ann of annotations) {
    try {
      // Quote first — survives small DOM edits.
      let range = quoteToRange(document.body, ann.quote, { hint: ann.position?.start ?? 0 });
      if (!range && ann.position) range = posToRange(document.body, ann.position);
      if (range) wrapRange(range, ann.id);
    } catch (err) {
      console.warn("[kenboard:annotate] re-anchor failed for #", ann.id, err);
    }
  }
}

// ---------- 7. selection adder ----------

function buildAdder() {
  adderEl = document.createElement("div");
  adderEl.className = "adder";
  const hl = document.createElement("button");
  hl.className = "adder-btn";
  hl.type = "button";
  hl.textContent = "🖍 Surligner";
  hl.addEventListener("mousedown", (e) => e.preventDefault());
  hl.addEventListener("click", () => {
    if (currentRange) addHighlightFromRange(currentRange);
    hideAdder();
  });
  const close = document.createElement("button");
  close.className = "adder-btn dismiss";
  close.type = "button";
  close.textContent = "✕";
  close.addEventListener("mousedown", (e) => e.preventDefault());
  close.addEventListener("click", hideAdder);
  adderEl.appendChild(hl);
  adderEl.appendChild(close);
  shadow.appendChild(adderEl);
}

function showAdder(range) {
  if (!adderEl) buildAdder();
  const rect = range.getBoundingClientRect();
  if (!rect.width && !rect.height) return;
  // Position near the end of the selection, clamped to viewport.
  const W = 180;
  const H = 32;
  let x = rect.right + 4;
  let y = rect.bottom + 4;
  if (x + W > window.innerWidth - 8) x = Math.max(8, window.innerWidth - W - 8);
  if (y + H > window.innerHeight - 8) y = Math.max(8, rect.top - H - 4);
  adderEl.style.left = `${x}px`;
  adderEl.style.top = `${y}px`;
  adderEl.classList.add("on");
}

function hideAdder() {
  adderEl?.classList.remove("on");
}

function onSelectionChange() {
  if (!mode) return;
  clearTimeout(selectionDebounce);
  selectionDebounce = setTimeout(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.toString().trim().length < 2) {
      hideAdder();
      return;
    }
    const range = sel.getRangeAt(0);
    // Don't trigger inside our shadow host or inside password fields.
    const node = range.commonAncestorContainer;
    if (host?.contains(node)) return;
    const editable = (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement)?.closest?.(
      'input[type="password"], [contenteditable]',
    );
    if (editable) return;
    currentRange = range.cloneRange();
    showAdder(range);
  }, 200);
}

function addHighlightFromRange(range) {
  /** @type {any} */
  let quote;
  /** @type {any} */
  let position;
  try {
    quote = quoteFromRange(document.body, range);
    position = posFromRange(document.body, range);
  } catch (err) {
    console.warn("[kenboard:annotate] could not anchor selection", err);
    return;
  }
  if (!quote?.exact) {
    console.warn("[kenboard:annotate] empty quote from range, skipping");
    return;
  }
  const ann = {
    id: nextId++,
    quote,
    position,
    createdAt: new Date().toISOString(),
  };
  annotations.push(ann);
  wrapRange(range, ann.id);
  saveAnnotations();
  renderBadge();
  if (drawerEl?.classList.contains("open")) renderDrawer();
  window.getSelection()?.removeAllRanges();
}

// ---------- 8. badge ----------

function buildBadge() {
  badgeEl = document.createElement("div");
  badgeEl.className = "badge";
  badgeEl.title = "Annotations kenboard — clic pour ouvrir le panneau";
  const dot = document.createElement("span");
  dot.className = "badge-dot";
  const txt = document.createElement("span");
  txt.className = "badge-text";
  badgeEl.appendChild(dot);
  badgeEl.appendChild(txt);
  badgeEl.addEventListener("click", openDrawer);
  shadow.appendChild(badgeEl);
}

function renderBadge() {
  if (!badgeEl) buildBadge();
  badgeEl.querySelector(".badge-text").textContent = `kb · ${annotations.length}`;
  badgeEl.classList.toggle("on", mode);
}

// ---------- 9. drawer ----------

function buildDrawer() {
  drawerEl = document.createElement("div");
  drawerEl.className = "drawer";
  shadow.appendChild(drawerEl);
}

function openDrawer() {
  if (!drawerEl) buildDrawer();
  renderDrawer();
  drawerEl.classList.add("open");
}

function closeDrawer() {
  drawerEl?.classList.remove("open");
}

function renderDrawer() {
  if (!drawerEl) return;
  drawerEl.replaceChildren();

  const header = document.createElement("div");
  header.className = "drawer-header";
  const close = document.createElement("button");
  close.className = "drawer-close";
  close.type = "button";
  close.textContent = "✕";
  close.title = "Fermer";
  close.addEventListener("click", closeDrawer);
  const title = document.createElement("div");
  title.className = "drawer-title";
  title.textContent = document.title || canonicalUrl();
  const url = document.createElement("div");
  url.className = "drawer-url";
  url.textContent = canonicalUrl();
  const count = document.createElement("div");
  count.className = "drawer-count";
  count.textContent = `${annotations.length} annotation${annotations.length === 1 ? "" : "s"}`;
  header.appendChild(close);
  header.appendChild(title);
  header.appendChild(url);
  header.appendChild(count);
  drawerEl.appendChild(header);

  const list = document.createElement("div");
  list.className = "drawer-list";
  if (annotations.length === 0) {
    const empty = document.createElement("div");
    empty.className = "drawer-empty";
    empty.textContent = "Aucune annotation. Sélectionnez du texte sur la page puis cliquez « 🖍 Surligner ».";
    list.appendChild(empty);
  } else {
    for (const ann of annotations) {
      const item = document.createElement("div");
      item.className = "drawer-item";
      const q = document.createElement("div");
      q.className = "drawer-quote";
      q.textContent = String(ann.quote?.exact ?? "");
      const del = document.createElement("button");
      del.className = "drawer-del";
      del.type = "button";
      del.title = "Supprimer cette annotation";
      del.textContent = "🗑";
      del.addEventListener("click", () => {
        annotations = annotations.filter((a) => a.id !== ann.id);
        unwrapHighlight(ann.id);
        saveAnnotations();
        renderBadge();
        renderDrawer();
      });
      item.appendChild(q);
      item.appendChild(del);
      list.appendChild(item);
    }
  }
  drawerEl.appendChild(list);

  const footer = document.createElement("div");
  footer.className = "drawer-footer";
  drawerPushBtn = document.createElement("button");
  drawerPushBtn.className = "drawer-push";
  drawerPushBtn.type = "button";
  drawerPushBtn.textContent = "Pousser sur kenboard";
  drawerPushBtn.disabled = annotations.length === 0;
  drawerPushBtn.addEventListener("click", () => {
    pushToKenboard().catch((err) => setDrawerStatus(`Erreur: ${err?.message ?? err}`, "error"));
  });
  drawerStatusEl = document.createElement("div");
  drawerStatusEl.className = "drawer-status";
  footer.appendChild(drawerPushBtn);
  footer.appendChild(drawerStatusEl);
  drawerEl.appendChild(footer);
}

function setDrawerStatus(msg, cls = "") {
  if (!drawerStatusEl) return;
  drawerStatusEl.textContent = msg;
  drawerStatusEl.className = "drawer-status" + (cls ? " " + cls : "");
}

// ---------- 10. push to kenboard ----------

async function pushToKenboard() {
  setDrawerStatus("");
  const cfg = await chrome.storage.local.get(["baseUrl", "apiToken", "projectId", "defaultWho"]);
  if (!cfg.baseUrl || !cfg.apiToken || !cfg.projectId) {
    setDrawerStatus("Configurez baseUrl / apiToken / projectId dans les réglages.", "error");
    return;
  }
  if (annotations.length === 0) return;

  if (drawerPushBtn) drawerPushBtn.disabled = true;
  setDrawerStatus("Envoi…");

  const description = buildMarkdown({
    pageTitle: document.title,
    pageUrl: canonicalUrl(),
    annotations: annotations.map((a) => ({
      quote: String(a.quote?.exact ?? ""),
      textFragmentUrl: textFragmentUrl(a.quote),
    })),
  });
  const title = (document.title || canonicalUrl()).slice(0, 250);

  let resp;
  try {
    resp = await fetch(`${cfg.baseUrl}/api/v1/tasks`, {
      method: "POST",
      // Same as popup.js: strip the session cookie so the auth middleware
      // stays on the bearer path (avoids the same-origin CSRF check).
      credentials: "omit",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${cfg.apiToken}`,
      },
      body: JSON.stringify({
        project_id: cfg.projectId,
        title,
        description,
        status: "todo",
        who: cfg.defaultWho || "",
      }),
    });
  } catch (err) {
    if (drawerPushBtn) drawerPushBtn.disabled = false;
    setDrawerStatus(`Erreur réseau: ${err.message}`, "error");
    return;
  }
  if (!resp.ok) {
    const text = await resp.text();
    if (drawerPushBtn) drawerPushBtn.disabled = false;
    setDrawerStatus(`HTTP ${resp.status}: ${text.slice(0, 120)}`, "error");
    return;
  }
  const task = await resp.json();
  setDrawerStatus(`Tâche #${task.id} créée. Vider les annotations ?`, "success");
  // Replace the push button with Clear / Keep.
  if (drawerPushBtn?.parentNode) {
    const wrap = drawerPushBtn.parentNode;
    drawerPushBtn.remove();
    const clearBtn = document.createElement("button");
    clearBtn.className = "drawer-push";
    clearBtn.type = "button";
    clearBtn.textContent = "Vider les annotations";
    clearBtn.style.background = "#cf222e";
    clearBtn.addEventListener("click", () => {
      for (const a of annotations) unwrapHighlight(a.id);
      annotations = [];
      saveAnnotations();
      renderBadge();
      renderDrawer();
    });
    wrap.insertBefore(clearBtn, drawerStatusEl);
    const keepBtn = document.createElement("button");
    keepBtn.className = "drawer-push";
    keepBtn.type = "button";
    keepBtn.textContent = "Garder pour itérer";
    keepBtn.style.background = "#57606a";
    keepBtn.style.marginTop = "6px";
    keepBtn.addEventListener("click", () => {
      setDrawerStatus(`Tâche #${task.id} créée.`, "success");
      renderDrawer();
    });
    wrap.insertBefore(keepBtn, drawerStatusEl);
  }
}

// ---------- 11. activation ----------

function activate() {
  if (mode) return;
  ensureHost();
  mode = true;
  loadAnnotations().then(() => {
    reapplyAll();
    renderBadge();
  });
}

function deactivate() {
  if (!mode) return;
  mode = false;
  hideAdder();
  closeDrawer();
  badgeEl?.classList.remove("on");
}

function onKeyDown(e) {
  // Alt+K toggles annotation mode on/off. Use `e.code` (physical key,
  // layout-independent) — `e.key` on macOS Option+K is "˚" because the
  // OS injects the dead-key character before the JS event fires.
  if (e.altKey && e.code === "KeyK") {
    e.preventDefault();
    if (mode) deactivate();
    else activate();
    return;
  }
  // ESC: dismiss adder first, then drawer, then exit mode.
  if (e.key === "Escape" && mode) {
    if (adderEl?.classList.contains("on")) {
      hideAdder();
    } else if (drawerEl?.classList.contains("open")) {
      closeDrawer();
    } else {
      deactivate();
    }
  }
}

// ---------- 12. SPA navigation + bootstrap ----------

function onMaybeUrlChange() {
  const cur = canonicalUrl();
  if (cur === lastUrl) return;
  lastUrl = cur;
  unwrapAllHighlights();
  annotations = [];
  renderBadge();
  if (mode) {
    loadAnnotations().then(() => {
      reapplyAll();
      renderBadge();
      if (drawerEl?.classList.contains("open")) renderDrawer();
    });
  }
}

function patchHistory() {
  const orig = history.pushState;
  history.pushState = function (...args) {
    const r = orig.apply(this, args);
    queueMicrotask(onMaybeUrlChange);
    return r;
  };
  const origReplace = history.replaceState;
  history.replaceState = function (...args) {
    const r = origReplace.apply(this, args);
    queueMicrotask(onMaybeUrlChange);
    return r;
  };
  window.addEventListener("popstate", onMaybeUrlChange);
}

function bootstrap() {
  // Visible boot marker so you can confirm the content script actually
  // injected (DevTools console → look for this line). If you don't see it,
  // the bundle didn't load (privileged page, blocked by the site, etc.).
  console.info("[kenboard:annotate] loaded — Alt+K to activate");
  lastUrl = canonicalUrl();
  document.addEventListener("keydown", onKeyDown, true);
  document.addEventListener("selectionchange", onSelectionChange);
  patchHistory();
  // Popup → content: a future "Annoter cette page" button can trigger this.
  if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg?.type === "kb-annotate-start") activate();
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
} else {
  bootstrap();
}
