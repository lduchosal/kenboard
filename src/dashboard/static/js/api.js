// @ts-check
// Centralised API client. Every fetch to the backend goes through ``apiCall``
// so failures (network, 401, 403, 4xx, 5xx) surface as a visible modal
// instead of being swallowed into ``console.warn`` or ``alert()``.

export const API_BASE = '/api/v1';

export function showError(title, body) {
  const modal = document.getElementById('error-modal');
  if (!modal) {
    globalThis.alert(`${title}\n\n${body}`);
    return;
  }
  document.getElementById('error-modal-title').textContent = title;
  document.getElementById('error-modal-body').textContent = body || '';
  modal.style.display = 'flex';
}

export async function apiCall(url, opts = {}) {
  let r;
  try {
    r = await fetch(url, opts);
  } catch (err) {
    showError('Erreur réseau', err?.message || String(err));
    throw err;
  }
  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.error || parsed.detail || text;
    } catch (parseErr) {
      console.debug('apiCall: response body is not JSON', parseErr);
    }
    let title;
    if (r.status === 401) {
      title = 'Non authentifié';
      detail = detail || 'Cette opération nécessite une clé API valide. Voir /admin/keys.';
    } else if (r.status === 403) {
      title = 'Permission refusée';
    } else if (r.status === 404) {
      title = 'Introuvable';
    } else if (r.status === 409) {
      title = 'Conflit';
    } else if (r.status === 422) {
      title = 'Validation';
    } else if (r.status >= 500) {
      title = `Erreur serveur (${r.status})`;
    } else {
      title = `Erreur ${r.status}`;
    }
    showError(title, detail);
    throw new Error(`HTTP ${r.status}: ${detail}`);
  }
  return r;
}

// Format ISO date (YYYY-MM-DD) to dd.mm for display consistency with Jinja.
export function fmtDate(iso) {
  if (!iso) return '';
  const parts = iso.split('-');
  if (parts.length < 3) return iso;
  return `${parts[2]}.${parts[1]}`;
}
