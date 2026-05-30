// kenboard paintbrush content script (#541 — replaces the #520 quote mode).
//
// Layout:
//   1.  constants (storage key, ids, CSS, SVG ns)
//   2.  state
//   3.  URL + storage helpers
//   4.  Shadow DOM host (badge + tool palette + drawer + capture pane)
//   5.  SVG overlay (live drawing + persistent shapes, page coords)
//   6.  rectangle tool (drag-to-draw, captures elements under it)
//   7.  text tool (click-to-place, inline composer)
//   8.  drawer (list + delete + push)
//   9.  push: serialise the SVG + extract MD → POST /api/v1/tasks
//  10.  activation flow (Alt+P toggle, ESC cascade, R/T tool switch)
//  11.  SPA navigation + bootstrap

import { buildMarkdown } from "./buildMarkdown.js";
import {
  escapeXml,
  RECT_STROKE,
  RED,
  serialiseSvg as serialiseSvgPure,
  SVG_NS,
  TEXT_SIZE,
} from "./paintbrushSvg.js";

// ---------- 1. constants ----------

const STORAGE_PREFIX = "kb_paint:";
const HOST_ID = "kb-paintbrush-root";
const OVERLAY_ID = "kb-paintbrush-overlay";
// 32-bit signed int max — anything larger silently falls back to ``auto``
// in CSS (the user pointed this out in #556: ``${Z + 1}`` was overflowing
// and the badge/palette/drawer ended up *under* the transparent capture
// pane, intercepting their clicks). We keep a safe ladder *under* the cap.
const Z_SVG = 2147483630;
const Z_CAPTURE = 2147483631;
const Z_UI = 2147483640;
const Z_DRAWER = 2147483645;
const Z_COMPOSER = 2147483646;

const SHADOW_CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  button { font: inherit; cursor: pointer; }

  .capture {
    position: fixed; inset: 0; z-index: ${Z_CAPTURE};
    background: transparent;
    cursor: crosshair;
    display: none;
  }
  .capture.on { display: block; }
  .capture[data-tool="text"] { cursor: text; }

  .badge {
    position: fixed; top: 14px; right: 14px; z-index: ${Z_UI};
    display: none; align-items: center; gap: 6px;
    background: #ffffff; color: #1f2328;
    border: 1px solid #d0d7de; border-radius: 999px;
    padding: 4px 10px; font-size: 12px; font-weight: 600;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
    user-select: none;
  }
  .badge.on { display: inline-flex; }
  .badge:hover { background: #f6f8fa; }
  .badge-dot { width: 8px; height: 8px; border-radius: 50%; background: ${RED}; }

  .palette {
    position: fixed; top: 56px; right: 14px; z-index: ${Z_UI};
    display: none; flex-direction: column; gap: 4px;
    background: #1f2328; color: #ffffff;
    border-radius: 6px; padding: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  }
  .palette.on { display: flex; }
  .palette-btn {
    background: transparent; color: inherit; border: 0;
    padding: 4px 10px; border-radius: 4px; font-size: 12px;
    text-align: left;
  }
  .palette-btn:hover { background: rgba(255,255,255,0.12); }
  .palette-btn.active { background: ${RED}; }

  .composer {
    position: fixed; z-index: ${Z_COMPOSER};
    background: #ffffff; border: 1px solid ${RED}; border-radius: 3px;
    padding: 2px 4px; font-size: ${TEXT_SIZE}px;
    color: ${RED}; min-width: 100px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
  }
  .composer.on { display: block; }
  .composer.off { display: none; }
  .composer input {
    border: 0; outline: 0; background: transparent; color: ${RED};
    font: inherit; width: 100%;
  }

  .drawer {
    position: fixed; top: 0; right: 0; height: 100vh; width: 320px;
    z-index: ${Z_DRAWER};
    background: #ffffff; color: #1f2328;
    border-left: 1px solid #d0d7de;
    box-shadow: -4px 0 16px rgba(0,0,0,0.10);
    transform: translateX(100%); transition: transform 180ms ease-out;
    display: flex; flex-direction: column;
  }
  .drawer.open { transform: translateX(0); }
  @media (prefers-reduced-motion: reduce) { .drawer { transition: none; } }

  .drawer-header { padding: 12px 16px; border-bottom: 1px solid #d0d7de; position: relative; }
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
  .drawer-item-body {
    flex: 1; font-size: 12px; line-height: 1.4;
    border-left: 3px solid ${RED}; padding-left: 8px;
    color: #1f2328;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .drawer-item-kind {
    font-size: 10px; color: #57606a; text-transform: uppercase;
    letter-spacing: 0.05em; margin-right: 4px;
  }
  .drawer-del {
    background: transparent; border: 0; color: ${RED}; font-size: 13px;
    padding: 2px 6px; border-radius: 4px; opacity: 0.6;
  }
  .drawer-del:hover { background: rgba(207,34,46,0.10); opacity: 1; }
  .drawer-footer { padding: 12px 16px; border-top: 1px solid #d0d7de; }
  .drawer-push {
    width: 100%; background: ${RED}; color: #ffffff; border: 0;
    padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;
  }
  .drawer-push:hover:not(:disabled) { background: #a40e1a; }
  .drawer-push:disabled { background: #adbac7; cursor: not-allowed; }
  .drawer-status { font-size: 11px; color: #57606a; margin-top: 6px; min-height: 14px; }
  .drawer-status.success { color: #1a7f37; }
  .drawer-status.error { color: ${RED}; }
`;

// ---------- 2. state ----------

let mode = false;
let tool = "rect"; // "rect" | "text"
/**
 * @typedef {{id:number, type:'rect', x:number, y:number, w:number, h:number,
 *            capturedText:string, note:string|null}} RectShape
 * @typedef {{id:number, type:'text', x:number, y:number, content:string}} TextShape
 * @type {(RectShape | TextShape)[]}
 */
let shapes = [];
let host = null;
let shadow = null;
let capturePane = null;
let svgOverlay = null;
let badgeEl = null;
let paletteEl = null;
let drawerEl = null;
let drawerStatusEl = null;
let drawerPushBtn = null;
let composerEl = null;
let composerInput = null;
let nextId = 1;
let dragStart = null;
let dragPreview = null;
let lastUrl = "";

// ---------- 3. URL + storage helpers ----------

function stripTracking(u) {
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
  if (link?.href) return stripTracking(link.href);
  return stripTracking(location.origin + location.pathname + location.search);
}

function storageKey() {
  return STORAGE_PREFIX + canonicalUrl();
}

async function loadShapes() {
  const key = storageKey();
  const data = await chrome.storage.local.get(key);
  shapes = Array.isArray(data[key]) ? data[key] : [];
  for (const s of shapes) if (s.id >= nextId) nextId = s.id + 1;
}

async function saveShapes() {
  const key = storageKey();
  await chrome.storage.local.set({ [key]: shapes });
}

// ---------- 4. Shadow DOM host ----------

function ensureHost() {
  if (host) return;
  host = document.createElement("div");
  host.id = HOST_ID;
  host.style.cssText = `all: initial; position: static; z-index: ${Z_COMPOSER};`;
  document.documentElement.appendChild(host);
  shadow = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = SHADOW_CSS;
  shadow.appendChild(style);
  buildBadge();
  buildPalette();
  buildCapture();
  buildDrawer();
  buildComposer();
}

// ---------- 5. SVG overlay (page coords via viewBox = scroll) ----------

function ensureOverlay() {
  if (svgOverlay) return;
  svgOverlay = document.createElementNS(SVG_NS, "svg");
  svgOverlay.setAttribute("id", OVERLAY_ID);
  // pointer-events: none → page can be clicked/scrolled normally; the
  // capture pane in the shadow handles drawing input separately.
  svgOverlay.setAttribute(
    "style",
    `position: fixed; inset: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: ${Z_SVG};`,
  );
  document.documentElement.appendChild(svgOverlay);
  updateOverlayViewBox();
  window.addEventListener("scroll", updateOverlayViewBox, { passive: true });
  window.addEventListener("resize", updateOverlayViewBox, { passive: true });
}

function updateOverlayViewBox() {
  if (!svgOverlay) return;
  svgOverlay.setAttribute(
    "viewBox",
    `${window.scrollX} ${window.scrollY} ${window.innerWidth} ${window.innerHeight}`,
  );
}

function renderOverlay() {
  if (!svgOverlay) return;
  svgOverlay.replaceChildren();
  for (const s of shapes) {
    if (s.type === "rect") svgOverlay.appendChild(svgRect(s.x, s.y, s.w, s.h, false));
    else if (s.type === "text") svgOverlay.appendChild(svgText(s.x, s.y, s.content));
  }
  if (dragPreview) {
    svgOverlay.appendChild(
      svgRect(dragPreview.x, dragPreview.y, dragPreview.w, dragPreview.h, true),
    );
  }
}

function svgRect(x, y, w, h, dashed) {
  const r = document.createElementNS(SVG_NS, "rect");
  r.setAttribute("x", String(x));
  r.setAttribute("y", String(y));
  r.setAttribute("width", String(w));
  r.setAttribute("height", String(h));
  r.setAttribute("fill", "transparent");
  r.setAttribute("stroke", RED);
  r.setAttribute("stroke-width", String(RECT_STROKE));
  if (dashed) r.setAttribute("stroke-dasharray", "6 4");
  return r;
}

function svgText(x, y, content) {
  const t = document.createElementNS(SVG_NS, "text");
  t.setAttribute("x", String(x));
  t.setAttribute("y", String(y));
  t.setAttribute("fill", RED);
  t.setAttribute("font-size", String(TEXT_SIZE));
  t.setAttribute("font-family", "sans-serif");
  t.textContent = content;
  return t;
}

// ---------- 6. rectangle tool ----------

function captureUnderRect(rect) {
  // For each rectangle, grab the topmost non-extension elements at the
  // centre + 4 corners, deduped, and collect their innerText. ``rect`` is
  // in page coords; convert back to client coords for elementsFromPoint.
  const sx = window.scrollX;
  const sy = window.scrollY;
  const probes = [
    [rect.x + rect.w / 2, rect.y + rect.h / 2],
    [rect.x + 4, rect.y + 4],
    [rect.x + rect.w - 4, rect.y + 4],
    [rect.x + 4, rect.y + rect.h - 4],
    [rect.x + rect.w - 4, rect.y + rect.h - 4],
  ];
  /** @type {Set<Element>} */
  const seen = new Set();
  for (const [px, py] of probes) {
    const cx = px - sx;
    const cy = py - sy;
    if (cx < 0 || cy < 0 || cx >= window.innerWidth || cy >= window.innerHeight) continue;
    const els = document.elementsFromPoint(cx, cy);
    for (const el of els) {
      if (host?.contains(el) || svgOverlay?.contains(el)) continue;
      // Skip very generic ancestors (html, body) and inline svg overlay siblings.
      if (el === document.documentElement || el === document.body) continue;
      seen.add(el);
      break; // top-most per probe is enough
    }
  }
  const out = [];
  for (const el of seen) {
    const txt = String(el.innerText || el.textContent || "").trim();
    if (txt) out.push(txt.slice(0, 240));
  }
  // De-dup identical strings (a single big <article> is the same on all probes).
  return [...new Set(out)].join("\n").slice(0, 600);
}

function buildCapture() {
  capturePane = document.createElement("div");
  capturePane.className = "capture";
  capturePane.dataset.tool = "rect";
  capturePane.addEventListener("pointerdown", onPointerDown);
  capturePane.addEventListener("pointermove", onPointerMove);
  capturePane.addEventListener("pointerup", onPointerUp);
  capturePane.addEventListener("pointercancel", () => {
    dragStart = null;
    dragPreview = null;
    renderOverlay();
  });
  shadow.appendChild(capturePane);
}

function clientToPage(e) {
  return { x: e.clientX + window.scrollX, y: e.clientY + window.scrollY };
}

function onPointerDown(e) {
  if (!mode) return;
  if (tool === "text") {
    showComposer(clientToPage(e), e.clientX, e.clientY);
    return;
  }
  // Rectangle tool: start drag.
  capturePane.setPointerCapture(e.pointerId);
  const p = clientToPage(e);
  dragStart = p;
  dragPreview = { x: p.x, y: p.y, w: 0, h: 0 };
  renderOverlay();
}

function onPointerMove(e) {
  if (!mode || !dragStart) return;
  const p = clientToPage(e);
  const x = Math.min(dragStart.x, p.x);
  const y = Math.min(dragStart.y, p.y);
  const w = Math.abs(p.x - dragStart.x);
  const h = Math.abs(p.y - dragStart.y);
  dragPreview = { x, y, w, h };
  renderOverlay();
}

function onPointerUp(e) {
  if (!mode || !dragStart || !dragPreview) {
    dragStart = null;
    dragPreview = null;
    return;
  }
  capturePane.releasePointerCapture(e.pointerId);
  const r = dragPreview;
  dragStart = null;
  dragPreview = null;
  // Discard tiny rects (likely accidental clicks).
  if (r.w < 8 || r.h < 8) {
    renderOverlay();
    return;
  }
  const captured = captureUnderRect(r);
  shapes.push({
    id: nextId++,
    type: "rect",
    x: Math.round(r.x),
    y: Math.round(r.y),
    w: Math.round(r.w),
    h: Math.round(r.h),
    capturedText: captured,
    note: null,
  });
  saveShapes();
  renderOverlay();
  renderBadge();
  if (drawerEl?.classList.contains("open")) renderDrawer();
}

// ---------- 7. text tool ----------

function buildComposer() {
  composerEl = document.createElement("div");
  composerEl.className = "composer off";
  composerInput = document.createElement("input");
  composerInput.type = "text";
  composerInput.placeholder = "Annotation";
  composerInput.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Enter") commitComposer();
    else if (e.key === "Escape") hideComposer();
  });
  composerEl.appendChild(composerInput);
  shadow.appendChild(composerEl);
}

let composerPagePoint = null;
function showComposer(pagePoint, clientX, clientY) {
  composerPagePoint = pagePoint;
  composerEl.style.left = `${clientX}px`;
  composerEl.style.top = `${clientY}px`;
  composerEl.classList.remove("off");
  composerEl.classList.add("on");
  composerInput.value = "";
  setTimeout(() => composerInput.focus(), 0);
}

function hideComposer() {
  composerEl?.classList.add("off");
  composerEl?.classList.remove("on");
  composerPagePoint = null;
}

function commitComposer() {
  const content = composerInput.value.trim();
  if (!content || !composerPagePoint) {
    hideComposer();
    return;
  }
  // Attach to nearest rectangle if close, otherwise free-standing text.
  const point = composerPagePoint;
  const nearestRect = nearestRectTo(point);
  if (nearestRect) nearestRect.note = content;
  shapes.push({
    id: nextId++,
    type: "text",
    x: point.x,
    y: point.y,
    content,
  });
  hideComposer();
  saveShapes();
  renderOverlay();
  renderBadge();
  if (drawerEl?.classList.contains("open")) renderDrawer();
}

function nearestRectTo(point) {
  let best = null;
  let bestDist = Infinity;
  for (const s of shapes) {
    if (s.type !== "rect") continue;
    const cx = s.x + s.w / 2;
    const cy = s.y + s.h / 2;
    const dx = point.x - cx;
    const dy = point.y - cy;
    const dist = Math.hypot(dx, dy);
    // Within 1.5x the rect's half-diagonal counts as "near".
    const reach = Math.hypot(s.w, s.h);
    if (dist < bestDist && dist < reach) {
      best = s;
      bestDist = dist;
    }
  }
  return best;
}

// ---------- 8. badge + palette + drawer ----------

function buildBadge() {
  badgeEl = document.createElement("div");
  badgeEl.className = "badge";
  badgeEl.title = "Annotations paintbrush — clic pour ouvrir le panneau (kenboard)";
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
  if (!badgeEl) return;
  badgeEl.querySelector(".badge-text").textContent = `kb · ${shapes.length}`;
  badgeEl.classList.toggle("on", mode);
}

function buildPalette() {
  paletteEl = document.createElement("div");
  paletteEl.className = "palette";
  const r = document.createElement("button");
  r.className = "palette-btn active";
  r.dataset.tool = "rect";
  r.type = "button";
  r.textContent = "▭ Rectangle (R)";
  r.addEventListener("click", () => setTool("rect"));
  const t = document.createElement("button");
  t.className = "palette-btn";
  t.dataset.tool = "text";
  t.type = "button";
  t.textContent = "T Texte (T)";
  t.addEventListener("click", () => setTool("text"));
  paletteEl.appendChild(r);
  paletteEl.appendChild(t);
  shadow.appendChild(paletteEl);
}

function setTool(name) {
  tool = name;
  capturePane.dataset.tool = name;
  for (const btn of paletteEl.querySelectorAll(".palette-btn")) {
    btn.classList.toggle("active", btn.dataset.tool === name);
  }
}

function buildDrawer() {
  drawerEl = document.createElement("div");
  drawerEl.className = "drawer";
  shadow.appendChild(drawerEl);
}

function openDrawer() {
  if (!drawerEl) return;
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
  const nRect = shapes.filter((s) => s.type === "rect").length;
  const nText = shapes.filter((s) => s.type === "text").length;
  count.textContent = `${nRect} rectangle${nRect === 1 ? "" : "s"} · ${nText} note${nText === 1 ? "" : "s"}`;
  header.append(close, title, url, count);
  drawerEl.appendChild(header);

  const list = document.createElement("div");
  list.className = "drawer-list";
  if (shapes.length === 0) {
    const empty = document.createElement("div");
    empty.className = "drawer-empty";
    empty.textContent = "Aucune annotation. Choisissez Rectangle ou Texte dans la palette puis dessinez sur la page.";
    list.appendChild(empty);
  } else {
    for (const s of shapes) {
      const item = document.createElement("div");
      item.className = "drawer-item";
      const body = document.createElement("div");
      body.className = "drawer-item-body";
      const kind = document.createElement("span");
      kind.className = "drawer-item-kind";
      if (s.type === "rect") {
        kind.textContent = "Rect";
        const text = document.createTextNode(
          (s.capturedText || "(pas de texte capturé)") + (s.note ? ` — « ${s.note} »` : ""),
        );
        body.append(kind, text);
      } else {
        kind.textContent = "Note";
        const text = document.createTextNode(s.content);
        body.append(kind, text);
      }
      const del = document.createElement("button");
      del.className = "drawer-del";
      del.type = "button";
      del.title = "Supprimer";
      del.textContent = "🗑";
      del.addEventListener("click", () => {
        shapes = shapes.filter((x) => x.id !== s.id);
        saveShapes();
        renderOverlay();
        renderBadge();
        renderDrawer();
      });
      item.append(body, del);
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
  drawerPushBtn.disabled = shapes.length === 0;
  drawerPushBtn.addEventListener("click", () => {
    pushToKenboard().catch((err) => setDrawerStatus(`Erreur: ${err?.message ?? err}`, "error"));
  });
  drawerStatusEl = document.createElement("div");
  drawerStatusEl.className = "drawer-status";
  footer.append(drawerPushBtn, drawerStatusEl);
  drawerEl.appendChild(footer);
}

function setDrawerStatus(msg, cls = "") {
  if (!drawerStatusEl) return;
  drawerStatusEl.textContent = msg;
  drawerStatusEl.className = "drawer-status" + (cls ? " " + cls : "");
}

// ---------- 9. push: serialise SVG + extract MD ----------

// Caps on the page-skeleton walk (#564). Pages with > MAX_ELEMENTS visible
// elements emit only what fits within the budget; the skeleton degrades
// gracefully to "annotations only" past MAX_SKELETON_BYTES.
const MAX_ELEMENTS = 2000;
const MAX_SKELETON_BYTES = 250_000;

/**
 * Walk the live DOM and emit a lightweight SVG skeleton (#564): one
 * <rect> per visible element (transparent fill, thin grey stroke), <text>
 * for direct text children at their computed font-size, and a gray
 * placeholder for <img>/<video>/<canvas>. Coordinates are page-relative
 * so the result aligns with the paintbrush annotations layer.
 *
 * Bounded by MAX_ELEMENTS and MAX_SKELETON_BYTES — returns "" early if
 * the budget is exceeded.
 */
function isTransparentBg(bg) {
  // ``getComputedStyle`` returns ``rgba(0, 0, 0, 0)`` for unset / explicit
  // transparent backgrounds. The literal "transparent" can also slip
  // through on some engines.
  if (!bg) return true;
  if (bg === "transparent") return true;
  const m = bg.match(/^rgba?\(([^)]+)\)$/);
  if (!m) return false;
  const parts = m[1].split(",").map((s) => s.trim());
  // rgba: 4 parts → check alpha.
  if (parts.length === 4) return parseFloat(parts[3]) === 0;
  return false;
}

function buildSkeletonSvg() {
  // #567: capture is viewport-only — we walk the live DOM but skip
  // anything whose bbox is fully outside the visible area. Coordinates
  // stay page-relative because the annotations layer is in page coords
  // too; ``serialiseSvg`` sets viewBox = the viewport so the SVG opens
  // pre-scrolled to the right spot.
  const sx = window.scrollX;
  const sy = window.scrollY;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const parts = [];
  let bytes = 0;
  let count = 0;
  const all = document.body.getElementsByTagName("*");
  for (let i = 0; i < all.length; i++) {
    if (count >= MAX_ELEMENTS || bytes >= MAX_SKELETON_BYTES) break;
    const el = all[i];
    if (host?.contains(el) || svgOverlay?.contains(el)) continue;
    const tag = el.tagName;
    if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT" || tag === "META" || tag === "LINK" || tag === "HEAD") {
      continue;
    }
    const rect = el.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) continue;
    // Viewport cull: discard anything entirely off-screen at push time.
    if (rect.bottom <= 0 || rect.top >= vh) continue;
    if (rect.right <= 0 || rect.left >= vw) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") continue;
    const opacity = parseFloat(cs.opacity);
    if (Number.isFinite(opacity) && opacity === 0) continue;
    const x = Math.round(rect.left + sx);
    const y = Math.round(rect.top + sy);
    const w = Math.round(rect.width);
    const h = Math.round(rect.height);

    // Background colour: emit a filled rect when non-transparent. DOM
    // order = parent first, so children paint above their container.
    const bg = cs.backgroundColor;
    if (!isTransparentBg(bg)) {
      const part = `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${bg}"/>`;
      parts.push(part);
      bytes += part.length;
    }

    // Image-like placeholder (one element-budget).
    if (tag === "IMG" || tag === "VIDEO" || tag === "CANVAS" || tag === "PICTURE") {
      const ph = `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#d0d7de" stroke="#57606a" stroke-width="0.5"/>`;
      parts.push(ph);
      bytes += ph.length;
      const alt = (el.getAttribute("alt") || tag.toLowerCase()).slice(0, 60);
      const label = `<text x="${x + 4}" y="${y + 14}" font-size="10" fill="#57606a" font-family="sans-serif">${escapeXml(alt)}</text>`;
      parts.push(label);
      bytes += label.length;
      count++;
      continue;
    }

    // Direct text children only (avoid duplicating ancestor text).
    let directText = "";
    for (const node of el.childNodes) {
      if (node.nodeType === 3 /* TEXT_NODE */) {
        const t = node.textContent ? node.textContent.trim() : "";
        if (t) directText += (directText ? " " : "") + t;
      }
    }
    if (directText) {
      const fontSize = Math.max(8, Math.min(48, parseFloat(cs.fontSize) || 14));
      const color = cs.color || "#1f2328";
      const fam = (cs.fontFamily || "sans-serif").split(",")[0].replace(/['"]/g, "").trim() || "sans-serif";
      const text = directText.slice(0, 280);
      const part = `<text x="${x}" y="${y + fontSize}" font-size="${fontSize}" fill="${color}" font-family="${escapeXml(fam)}">${escapeXml(text)}</text>`;
      parts.push(part);
      bytes += part.length;
    }
    count++;
  }
  if (bytes >= MAX_SKELETON_BYTES) {
    console.warn("[kenboard:paintbrush] skeleton truncated — exceeded byte budget");
  }
  return parts.join("");
}

function serialiseSvg() {
  // Thin live-runtime wrapper around the pure serialiser (#549): captures
  // the viewport + walks the live DOM for the skeleton, then defers all
  // string building to ``serialiseSvgPure`` (testable in vitest).
  return serialiseSvgPure({
    shapes,
    scrollX: window.scrollX,
    scrollY: window.scrollY,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    skeleton: buildSkeletonSvg(),
  });
}

async function pushToKenboard() {
  setDrawerStatus("");
  const cfg = await chrome.storage.local.get(["baseUrl", "apiToken", "projectId", "defaultWho"]);
  if (!cfg.baseUrl || !cfg.apiToken || !cfg.projectId) {
    setDrawerStatus("Configurez baseUrl / apiToken / projectId dans les réglages.", "error");
    return;
  }
  if (shapes.length === 0) return;

  if (drawerPushBtn) drawerPushBtn.disabled = true;
  setDrawerStatus("Envoi…");

  // Markdown: one block per rect with its captured text + nearby note.
  const annotations = shapes
    .filter((s) => s.type === "rect")
    .map((s) => ({
      quote: s.capturedText || "(rien capturé sous le rectangle)",
      textFragmentUrl: null,
      note: s.note,
    }));
  // Free-standing text notes (not attached to a rect) get appended as their own annotations.
  const linkedNoteIds = new Set(shapes.filter((s) => s.type === "rect" && s.note).map((s) => s.id));
  for (const s of shapes) {
    if (s.type !== "text") continue;
    const isLinked = shapes.some(
      (r) => r.type === "rect" && r.note === s.content && linkedNoteIds.has(r.id),
    );
    if (isLinked) continue;
    annotations.push({ quote: s.content, textFragmentUrl: null, note: null });
  }
  const description = buildMarkdown({
    pageTitle: document.title,
    pageUrl: canonicalUrl(),
    annotations,
  });

  const attachement = serialiseSvg();
  const title = (document.title || canonicalUrl()).slice(0, 250);

  let resp;
  try {
    resp = await fetch(`${cfg.baseUrl}/api/v1/tasks`, {
      method: "POST",
      credentials: "omit",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${cfg.apiToken}`,
      },
      body: JSON.stringify({
        project_id: cfg.projectId,
        title,
        description,
        attachement,
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
  setDrawerStatus(`Tâche #${task.id} créée.`, "success");
  // Replace push button with Clear / Keep.
  if (drawerPushBtn?.parentNode) {
    const wrap = drawerPushBtn.parentNode;
    drawerPushBtn.remove();
    const clearBtn = document.createElement("button");
    clearBtn.className = "drawer-push";
    clearBtn.type = "button";
    clearBtn.textContent = "Vider les annotations";
    clearBtn.style.background = "#57606a";
    clearBtn.addEventListener("click", () => {
      shapes = [];
      saveShapes();
      renderOverlay();
      renderBadge();
      renderDrawer();
    });
    wrap.insertBefore(clearBtn, drawerStatusEl);
  }
}

// ---------- 10. activation ----------

function activate() {
  if (mode) return;
  ensureHost();
  ensureOverlay();
  mode = true;
  loadShapes().then(() => {
    renderOverlay();
    renderBadge();
    capturePane.classList.add("on");
    paletteEl.classList.add("on");
  });
}

function deactivate() {
  if (!mode) return;
  mode = false;
  hideComposer();
  closeDrawer();
  capturePane?.classList.remove("on");
  paletteEl?.classList.remove("on");
  badgeEl?.classList.remove("on");
}

function isTyping() {
  // When focus is inside our Shadow DOM, ``document.activeElement`` from the
  // outer document returns the **host** (a <div>), not the actual input.
  // We must also check ``shadow.activeElement`` so the R / T tool shortcuts
  // don't eat keystrokes while the user is typing a note (#555).
  if (composerEl?.classList.contains("on")) return true;
  const inShadow = shadow?.activeElement;
  if (inShadow && (inShadow.tagName === "INPUT" || inShadow.tagName === "TEXTAREA")) {
    return true;
  }
  const ae = document.activeElement;
  if (!ae) return false;
  const tag = ae.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || ae.isContentEditable === true;
}

function onKeyDown(e) {
  // Alt+P toggles paintbrush mode. ``e.code`` is layout-independent
  // (macOS Option+P would otherwise come through as "π" via e.key).
  if (e.altKey && e.code === "KeyP") {
    e.preventDefault();
    if (mode) deactivate();
    else activate();
    return;
  }
  if (!mode) return;
  // Tool switch shortcuts (only when mode is on and the user is not typing).
  if (!e.altKey && !e.ctrlKey && !e.metaKey && !isTyping()) {
    if (e.code === "KeyR") {
      e.preventDefault();
      setTool("rect");
      return;
    }
    if (e.code === "KeyT") {
      e.preventDefault();
      setTool("text");
      return;
    }
  }
  // ESC cascades: composer → drawer → mode.
  if (e.key === "Escape") {
    if (composerEl?.classList.contains("on")) {
      hideComposer();
    } else if (drawerEl?.classList.contains("open")) {
      closeDrawer();
    } else {
      deactivate();
    }
  }
}

// ---------- 11. SPA navigation + bootstrap ----------

function onMaybeUrlChange() {
  const cur = canonicalUrl();
  if (cur === lastUrl) return;
  lastUrl = cur;
  shapes = [];
  renderOverlay();
  renderBadge();
  if (mode) {
    loadShapes().then(() => {
      renderOverlay();
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
  console.info("[kenboard:paintbrush] loaded — Alt+P (macOS: Option+P) to activate");
  lastUrl = canonicalUrl();
  document.addEventListener("keydown", onKeyDown, true);
  patchHistory();
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
