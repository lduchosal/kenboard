(() => {
  // extension/content/buildMarkdown.js
  function buildMarkdown({ pageTitle, pageUrl, annotations }) {
    const label = (pageTitle || pageUrl || "").trim() || pageUrl || "";
    const lines = ["## Annotations", "", `**Source:** [${label}](${pageUrl})`, ""];
    const items = Array.isArray(annotations) ? annotations : [];
    for (let i = 0; i < items.length; i++) {
      const a = items[i];
      const quote = String(a?.quote ?? "");
      const quoteLines = quote.split("\n").map((l) => `> ${l}`).join("\n");
      lines.push(quoteLines);
      if (a?.textFragmentUrl) {
        lines.push("");
        lines.push(`[citer](${a.textFragmentUrl})`);
      }
      if (a?.note) {
        lines.push("");
        lines.push(`**Note :** ${String(a.note)}`);
      }
      if (i < items.length - 1) {
        lines.push("");
        lines.push("---");
        lines.push("");
      }
    }
    return lines.join("\n");
  }

  // extension/content/annotate.src.js
  var STORAGE_PREFIX = "kb_paint:";
  var HOST_ID = "kb-paintbrush-root";
  var OVERLAY_ID = "kb-paintbrush-overlay";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var Z_SVG = 2147483630;
  var Z_CAPTURE = 2147483631;
  var Z_UI = 2147483640;
  var Z_DRAWER = 2147483645;
  var Z_COMPOSER = 2147483646;
  var RED = "#cf222e";
  var RECT_STROKE = 5;
  var TEXT_SIZE = 12;
  var SHADOW_CSS = `
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
  var mode = false;
  var tool = "rect";
  var shapes = [];
  var host = null;
  var shadow = null;
  var capturePane = null;
  var svgOverlay = null;
  var badgeEl = null;
  var paletteEl = null;
  var drawerEl = null;
  var drawerStatusEl = null;
  var drawerPushBtn = null;
  var composerEl = null;
  var composerInput = null;
  var nextId = 1;
  var dragStart = null;
  var dragPreview = null;
  var lastUrl = "";
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
  function ensureOverlay() {
    if (svgOverlay) return;
    svgOverlay = document.createElementNS(SVG_NS, "svg");
    svgOverlay.setAttribute("id", OVERLAY_ID);
    svgOverlay.setAttribute(
      "style",
      `position: fixed; inset: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: ${Z_SVG};`
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
      `${window.scrollX} ${window.scrollY} ${window.innerWidth} ${window.innerHeight}`
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
        svgRect(dragPreview.x, dragPreview.y, dragPreview.w, dragPreview.h, true)
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
  function captureUnderRect(rect) {
    const sx = window.scrollX;
    const sy = window.scrollY;
    const probes = [
      [rect.x + rect.w / 2, rect.y + rect.h / 2],
      [rect.x + 4, rect.y + 4],
      [rect.x + rect.w - 4, rect.y + 4],
      [rect.x + 4, rect.y + rect.h - 4],
      [rect.x + rect.w - 4, rect.y + rect.h - 4]
    ];
    const seen = /* @__PURE__ */ new Set();
    for (const [px, py] of probes) {
      const cx = px - sx;
      const cy = py - sy;
      if (cx < 0 || cy < 0 || cx >= window.innerWidth || cy >= window.innerHeight) continue;
      const els = document.elementsFromPoint(cx, cy);
      for (const el of els) {
        if (host?.contains(el) || svgOverlay?.contains(el)) continue;
        if (el === document.documentElement || el === document.body) continue;
        seen.add(el);
        break;
      }
    }
    const out = [];
    for (const el of seen) {
      const txt = String(el.innerText || el.textContent || "").trim();
      if (txt) out.push(txt.slice(0, 240));
    }
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
      note: null
    });
    saveShapes();
    renderOverlay();
    renderBadge();
    if (drawerEl?.classList.contains("open")) renderDrawer();
  }
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
  var composerPagePoint = null;
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
    const point = composerPagePoint;
    const nearestRect = nearestRectTo(point);
    if (nearestRect) nearestRect.note = content;
    shapes.push({
      id: nextId++,
      type: "text",
      x: point.x,
      y: point.y,
      content
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
      const reach = Math.hypot(s.w, s.h);
      if (dist < bestDist && dist < reach) {
        best = s;
        bestDist = dist;
      }
    }
    return best;
  }
  function buildBadge() {
    badgeEl = document.createElement("div");
    badgeEl.className = "badge";
    badgeEl.title = "Annotations paintbrush \u2014 clic pour ouvrir le panneau (kenboard)";
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
    badgeEl.querySelector(".badge-text").textContent = `kb \xB7 ${shapes.length}`;
    badgeEl.classList.toggle("on", mode);
  }
  function buildPalette() {
    paletteEl = document.createElement("div");
    paletteEl.className = "palette";
    const r = document.createElement("button");
    r.className = "palette-btn active";
    r.dataset.tool = "rect";
    r.type = "button";
    r.textContent = "\u25AD Rectangle (R)";
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
    close.textContent = "\u2715";
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
    count.textContent = `${nRect} rectangle${nRect === 1 ? "" : "s"} \xB7 ${nText} note${nText === 1 ? "" : "s"}`;
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
            (s.capturedText || "(pas de texte captur\xE9)") + (s.note ? ` \u2014 \xAB ${s.note} \xBB` : "")
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
        del.textContent = "\u{1F5D1}";
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
  function serialiseSvg() {
    const PAD = 16;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const s of shapes) {
      if (s.type === "rect") {
        minX = Math.min(minX, s.x);
        minY = Math.min(minY, s.y);
        maxX = Math.max(maxX, s.x + s.w);
        maxY = Math.max(maxY, s.y + s.h);
      } else {
        minX = Math.min(minX, s.x);
        minY = Math.min(minY, s.y - TEXT_SIZE);
        maxX = Math.max(maxX, s.x + 240);
        maxY = Math.max(maxY, s.y + TEXT_SIZE);
      }
    }
    if (!isFinite(minX)) return "";
    const vx = minX - PAD;
    const vy = minY - PAD;
    const vw = maxX - minX + 2 * PAD;
    const vh = maxY - minY + 2 * PAD;
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("xmlns", SVG_NS);
    svg.setAttribute("viewBox", `${vx} ${vy} ${vw} ${vh}`);
    svg.setAttribute("width", String(Math.min(900, vw)));
    for (const s of shapes) {
      if (s.type === "rect") svg.appendChild(svgRect(s.x, s.y, s.w, s.h, false));
      else svg.appendChild(svgText(s.x, s.y, s.content));
    }
    return new XMLSerializer().serializeToString(svg);
  }
  async function pushToKenboard() {
    setDrawerStatus("");
    const cfg = await chrome.storage.local.get(["baseUrl", "apiToken", "projectId", "defaultWho"]);
    if (!cfg.baseUrl || !cfg.apiToken || !cfg.projectId) {
      setDrawerStatus("Configurez baseUrl / apiToken / projectId dans les r\xE9glages.", "error");
      return;
    }
    if (shapes.length === 0) return;
    if (drawerPushBtn) drawerPushBtn.disabled = true;
    setDrawerStatus("Envoi\u2026");
    const annotations = shapes.filter((s) => s.type === "rect").map((s) => ({
      quote: s.capturedText || "(rien captur\xE9 sous le rectangle)",
      textFragmentUrl: null,
      note: s.note
    }));
    const linkedNoteIds = new Set(shapes.filter((s) => s.type === "rect" && s.note).map((s) => s.id));
    for (const s of shapes) {
      if (s.type !== "text") continue;
      const isLinked = shapes.some(
        (r) => r.type === "rect" && r.note === s.content && linkedNoteIds.has(r.id)
      );
      if (isLinked) continue;
      annotations.push({ quote: s.content, textFragmentUrl: null, note: null });
    }
    const description = buildMarkdown({
      pageTitle: document.title,
      pageUrl: canonicalUrl(),
      annotations
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
          Authorization: `Bearer ${cfg.apiToken}`
        },
        body: JSON.stringify({
          project_id: cfg.projectId,
          title,
          description,
          attachement,
          status: "todo",
          who: cfg.defaultWho || ""
        })
      });
    } catch (err) {
      if (drawerPushBtn) drawerPushBtn.disabled = false;
      setDrawerStatus(`Erreur r\xE9seau: ${err.message}`, "error");
      return;
    }
    if (!resp.ok) {
      const text = await resp.text();
      if (drawerPushBtn) drawerPushBtn.disabled = false;
      setDrawerStatus(`HTTP ${resp.status}: ${text.slice(0, 120)}`, "error");
      return;
    }
    const task = await resp.json();
    setDrawerStatus(`T\xE2che #${task.id} cr\xE9\xE9e.`, "success");
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
    if (e.altKey && e.code === "KeyP") {
      e.preventDefault();
      if (mode) deactivate();
      else activate();
      return;
    }
    if (!mode) return;
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
    history.pushState = function(...args) {
      const r = orig.apply(this, args);
      queueMicrotask(onMaybeUrlChange);
      return r;
    };
    const origReplace = history.replaceState;
    history.replaceState = function(...args) {
      const r = origReplace.apply(this, args);
      queueMicrotask(onMaybeUrlChange);
      return r;
    };
    window.addEventListener("popstate", onMaybeUrlChange);
  }
  function bootstrap() {
    console.info("[kenboard:paintbrush] loaded \u2014 Alt+P (macOS: Option+P) to activate");
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
})();
