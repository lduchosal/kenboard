"use strict";

const $ = (id) => document.getElementById(id);

async function loadConfig() {
  const c = await chrome.storage.local.get([
    "baseUrl",
    "apiToken",
    "projectId",
    "defaultWho",
  ]);
  if (!c.baseUrl || !c.apiToken || !c.projectId) {
    return null;
  }
  return c;
}

function setStatus(msg, cls) {
  const el = $("status");
  el.textContent = msg;
  el.className = cls || "";
}

// Runs in the page (injected via chrome.scripting.executeScript). Must be
// self-contained — no closures over popup scope. Returns a plain object of
// the page's structured text: title, url, meta description, a heading
// outline, and the user's current selection. No binary, no screenshot.
function extractPageInfo() {
  const meta = document.querySelector('meta[name="description"]');
  const headings = Array.from(document.querySelectorAll("h1, h2, h3"))
    .map((h) => ({ level: Number(h.tagName[1]), text: h.textContent.trim() }))
    .filter((h) => h.text)
    .slice(0, 40);
  const selection = (window.getSelection && window.getSelection().toString()) || "";
  return {
    title: document.title || "",
    url: location.href,
    description: (meta && meta.content ? meta.content : "").trim(),
    headings,
    selection: selection.trim(),
  };
}

// Compose the task description as markdown: the user's note, then a
// structured textual capture of the page (#514). No image is embedded —
// the description stays plain text so it fits the TEXT column (#511).
function buildDescription(body, sourceUrl, page) {
  const parts = [];
  if (body) parts.push(body);
  const cap = [`**Source:** ${sourceUrl}`];
  if (page) {
    if (page.description) cap.push(page.description);
    if (page.headings && page.headings.length) {
      const outline = page.headings
        .map((h) => `${"  ".repeat(h.level - 1)}- ${h.text}`)
        .join("\n");
      cap.push(`**Outline:**\n\n${outline}`);
    }
    if (page.selection) {
      const quoted = page.selection
        .split("\n")
        .map((l) => `> ${l}`)
        .join("\n");
      cap.push(`**Selection:**\n\n${quoted}`);
    }
  }
  parts.push(`---\n\n${cap.join("\n\n")}`);
  return parts.join("\n\n");
}

async function submit(cfg, tab) {
  const btn = $("submit");
  btn.disabled = true;
  setStatus("Capturing…");

  let page = null;
  if ($("include-capture").checked) {
    try {
      const [res] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractPageInfo,
      });
      page = (res && res.result) || null;
    } catch (err) {
      // chrome://, about:, file://, store pages, etc. can't be scripted —
      // proceed with just the title + source URL.
      setStatus(`Capture skipped: ${err.message}`, "error");
    }
  }

  const description = buildDescription(
    $("description").value.trim(),
    tab.url,
    page,
  );

  setStatus("Posting…");
  let resp;
  try {
    resp = await fetch(`${cfg.baseUrl}/api/v1/tasks`, {
      method: "POST",
      // Strip the kenboard session cookie even if Firefox / Chrome
      // wants to attach it — otherwise the server's auth middleware
      // sees a logged-in user and demands a same-origin Origin header,
      // which we (chrome-extension://…) can't provide → 403 CSRF.
      // Bearer token below is the only auth we want.
      credentials: "omit",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${cfg.apiToken}`,
      },
      body: JSON.stringify({
        project_id: cfg.projectId,
        title: $("title").value.trim(),
        description,
        status: "todo",
        who: $("who").value.trim() || cfg.defaultWho || "",
      }),
    });
  } catch (err) {
    btn.disabled = false;
    setStatus(`Network error: ${err.message}`, "error");
    return;
  }

  if (!resp.ok) {
    const text = await resp.text();
    btn.disabled = false;
    setStatus(`HTTP ${resp.status}: ${text.slice(0, 120)}`, "error");
    return;
  }

  const task = await resp.json();
  setStatus(`Task #${task.id} created`, "success");
  setTimeout(() => window.close(), 800);
}

async function init() {
  const cfg = await loadConfig();
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true,
  });

  if (cfg) {
    $("who").value = cfg.defaultWho || "";
  } else {
    setStatus(
      "Open Settings to configure base_url / api_token / project_id.",
      "error",
    );
    $("submit").disabled = true;
  }
  $("title").value = tab?.title || "";
  $("title").focus();
  $("title").select();

  $("task-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!cfg) {
      chrome.runtime.openOptionsPage();
      return;
    }
    submit(cfg, tab).catch((err) => {
      $("submit").disabled = false;
      setStatus(`Error: ${err.message}`, "error");
    });
  });
  $("open-options").addEventListener("click", (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
}

init();
