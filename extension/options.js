"use strict";

const $ = (id) => document.getElementById(id);

async function load() {
  const cfg = await chrome.storage.local.get([
    "baseUrl",
    "apiToken",
    "projectId",
    "defaultWho",
  ]);
  $("baseUrl").value = cfg.baseUrl || "";
  $("apiToken").value = cfg.apiToken || "";
  $("projectId").value = cfg.projectId || "";
  $("defaultWho").value = cfg.defaultWho || "";
}

function setStatus(msg, cls) {
  const el = $("status");
  el.textContent = msg;
  el.className = cls || "";
}

async function save(e) {
  e.preventDefault();
  await chrome.storage.local.set({
    baseUrl: $("baseUrl").value.trim().replace(/\/$/, ""),
    apiToken: $("apiToken").value.trim(),
    projectId: $("projectId").value.trim(),
    defaultWho: $("defaultWho").value.trim(),
  });
  setStatus("Saved.", "success");
}

async function test() {
  const baseUrl = $("baseUrl").value.trim().replace(/\/$/, "");
  const token = $("apiToken").value.trim();
  if (!baseUrl || !token) {
    setStatus("Fill base_url and api_token first.", "error");
    return;
  }
  setStatus("Testing…");
  try {
    const resp = await fetch(`${baseUrl}/api/v1/projects`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) {
      setStatus(`HTTP ${resp.status}`, "error");
      return;
    }
    const projects = await resp.json();
    setStatus(`OK — ${projects.length} project(s) reachable.`, "success");
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  $("settings").addEventListener("submit", save);
  $("test").addEventListener("click", test);
});
