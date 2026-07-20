import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  apiFetch,
  fetchMe,
  loginWithGoogle,
  logout,
  deleteAccount,
} from './auth.js';

// A minimal Response-like stub so we don't depend on a real network layer.
function mockResponse({ ok = true, status = 200, json = {} } = {}) {
  return { ok, status, json: async () => json };
}

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('sends credentials and prefixes the API base URL', async () => {
    fetch.mockResolvedValue(mockResponse());
    await apiFetch('/auth/me/');
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = fetch.mock.calls[0];
    expect(url).toMatch(/\/auth\/me\/$/);
    expect(options.credentials).toBe('include');
  });

  it('merges caller options over the defaults', async () => {
    fetch.mockResolvedValue(mockResponse());
    await apiFetch('/auth/logout/', { method: 'POST' });
    const [, options] = fetch.mock.calls[0];
    expect(options.method).toBe('POST');
    expect(options.credentials).toBe('include');
  });

  it('returns the response even on a non-ok status (no throw)', async () => {
    fetch.mockResolvedValue(mockResponse({ ok: false, status: 500 }));
    const res = await apiFetch('/boom/');
    expect(res.status).toBe(500);
  });

  it('rethrows network-level failures', async () => {
    fetch.mockRejectedValue(new Error('offline'));
    await expect(apiFetch('/auth/me/')).rejects.toThrow('offline');
  });
});

describe('fetchMe', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));

  it('returns parsed JSON on success', async () => {
    fetch.mockResolvedValue(mockResponse({ json: { authenticated: true } }));
    await expect(fetchMe()).resolves.toEqual({ authenticated: true });
  });

  it('throws on a non-ok status', async () => {
    fetch.mockResolvedValue(mockResponse({ ok: false, status: 401 }));
    await expect(fetchMe()).rejects.toThrow('401');
  });
});

describe('loginWithGoogle', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));

  it('POSTs the credential as JSON and returns the parsed body', async () => {
    fetch.mockResolvedValue(mockResponse({ json: { authenticated: true } }));
    const data = await loginWithGoogle('token-abc');
    const [, options] = fetch.mock.calls[0];
    expect(options.method).toBe('POST');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual({ credential: 'token-abc' });
    expect(data).toEqual({ authenticated: true });
  });

  it('throws the server-provided error message when present', async () => {
    fetch.mockResolvedValue(
      mockResponse({ ok: false, status: 401, json: { error: 'bad token' } }),
    );
    await expect(loginWithGoogle('x')).rejects.toThrow('bad token');
  });

  it('falls back to a status-based message when no error field', async () => {
    fetch.mockResolvedValue(mockResponse({ ok: false, status: 500, json: {} }));
    await expect(loginWithGoogle('x')).rejects.toThrow('500');
  });
});

describe('logout / deleteAccount', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));

  it('logout POSTs and returns JSON', async () => {
    fetch.mockResolvedValue(mockResponse({ json: { ok: true } }));
    await expect(logout()).resolves.toEqual({ ok: true });
    expect(fetch.mock.calls[0][1].method).toBe('POST');
  });

  it('deleteAccount uses the DELETE method', async () => {
    fetch.mockResolvedValue(mockResponse({ json: { ok: true } }));
    await deleteAccount();
    expect(fetch.mock.calls[0][1].method).toBe('DELETE');
  });

  it('deleteAccount throws on a non-ok status', async () => {
    fetch.mockResolvedValue(mockResponse({ ok: false, status: 401 }));
    await expect(deleteAccount()).rejects.toThrow('401');
  });
});
