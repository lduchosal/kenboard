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

function buildDescription(body, sourceUrl, screenshot) {
  const parts = [];
  if (body) parts.push(body);
  parts.push(`---\n\n**Source:** ${sourceUrl}`);
  if (screenshot) {
    parts.push(`![screenshot](${screenshot})`);
  }
  return parts.join("\n\n");
}

async function submit(cfg, tab) {
  const btn = $("submit");
  btn.disabled = true;
  setStatus("Capturing…");

  let screenshot = null;
  if ($("include-screenshot").checked) {
    try {
      screenshot = await chrome.tabs.captureVisibleTab(tab.windowId, {
        format: "png",
      });
    } catch (err) {
      // chrome://, file://, store pages, etc. can't be captured — proceed without.
      setStatus(`Capture skipped: ${err.message}`, "error");
    }
  }

  const description = buildDescription(
    $("description").value.trim(),
    tab.url,
    screenshot,
  );

  setStatus("Posting…");
  let resp;
  try {
    resp = await fetch(`${cfg.baseUrl}/api/v1/tasks`, {
      method: "POST",
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
