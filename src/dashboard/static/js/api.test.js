// Unit tests for the API client wrapper. ``apiCall`` and ``showError`` are
// the funnel every backend call goes through, so it's worth nailing down
// their error-routing behaviour even though it's mostly DOM glue.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiCall, fmtDate, showError } from './api.js';

beforeEach(() => {
  document.body.innerHTML = `
    <div id="error-modal" style="display:none">
      <div id="error-modal-title"></div>
      <div id="error-modal-body"></div>
    </div>
  `;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fmtDate', () => {
  it('reformats ISO YYYY-MM-DD to dd.mm', () => {
    expect(fmtDate('2026-05-06')).toBe('06.05');
  });
  it('returns empty string for empty input', () => {
    expect(fmtDate('')).toBe('');
    expect(fmtDate(null)).toBe('');
  });
  it('passes through non-ISO input verbatim', () => {
    expect(fmtDate('hello')).toBe('hello');
  });
});

describe('showError', () => {
  it('writes title + body into the error modal and shows it', () => {
    showError('Boom', 'something happened');
    const modal = document.getElementById('error-modal');
    expect(modal.style.display).toBe('flex');
    expect(document.getElementById('error-modal-title').textContent).toBe('Boom');
    expect(document.getElementById('error-modal-body').textContent).toBe('something happened');
  });

  it('falls back to alert() when the modal is missing', () => {
    document.body.innerHTML = ''; // strip the modal
    const alertSpy = vi.fn();
    globalThis.alert = alertSpy;
    showError('Boom', 'oops');
    expect(alertSpy).toHaveBeenCalledOnce();
    expect(alertSpy.mock.calls[0][0]).toContain('Boom');
    expect(alertSpy.mock.calls[0][0]).toContain('oops');
  });
});

describe('apiCall', () => {
  it('returns the response on 2xx', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('ok', { status: 200 }));
    const r = await apiCall('/x');
    expect(r.status).toBe(200);
  });

  it('surfaces a 401 error in the modal and throws', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response('{"error":"token required"}', {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await expect(apiCall('/x')).rejects.toThrow(/HTTP 401/);
    expect(document.getElementById('error-modal-title').textContent).toBe('Non authentifié');
  });

  it('surfaces a 500 error with the server-side title', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('boom', { status: 500 }));
    await expect(apiCall('/x')).rejects.toThrow(/HTTP 500/);
    expect(document.getElementById('error-modal-title').textContent).toContain('500');
  });

  it('surfaces a network failure and rethrows', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('offline'));
    await expect(apiCall('/x')).rejects.toThrow(/offline/);
    expect(document.getElementById('error-modal-title').textContent).toBe('Erreur réseau');
  });

  it('parses Pydantic ``detail`` field for nicer messages', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response('{"detail":"name required"}', {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await expect(apiCall('/x')).rejects.toThrow(/name required/);
    expect(document.getElementById('error-modal-body').textContent).toBe('name required');
  });

  // Cover the remaining status-code branches so each titled error is
  // exercised at least once (Sonar new_coverage).
  it.each([
    [403, 'Permission refusée'],
    [404, 'Introuvable'],
    [409, 'Conflit'],
    [418, 'Erreur 418'],
  ])('titles a %i response as "%s"', async (status, title) => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('nope', { status }));
    await expect(apiCall('/x')).rejects.toThrow(new RegExp(`HTTP ${status}`));
    expect(document.getElementById('error-modal-title').textContent).toBe(title);
  });
});
