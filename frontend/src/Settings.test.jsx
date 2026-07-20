import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('./auth.js', () => ({
  apiFetch: vi.fn(),
  logout: vi.fn(),
  deleteAccount: vi.fn(),
}));

import { apiFetch, logout, deleteAccount } from './auth.js';
import Settings from './Settings.jsx';

function jsonResponse(payload, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => payload };
}

beforeEach(() => {
  apiFetch.mockReset();
  logout.mockReset();
  deleteAccount.mockReset();
});

describe('Settings — loading', () => {
  it('populates fields from the fetched settings', async () => {
    apiFetch.mockResolvedValueOnce(
      jsonResponse({ language: 'fr', questions_per_day: 15 }),
    );
    render(<Settings onLoggedOut={() => {}} />);
    await waitFor(() =>
      expect(screen.getByRole('combobox')).toHaveValue('fr'),
    );
    expect(screen.getByRole('spinbutton')).toHaveValue(15);
  });

  it('shows an error when the fetch fails', async () => {
    apiFetch.mockResolvedValueOnce(jsonResponse({}, { ok: false, status: 500 }));
    render(<Settings onLoggedOut={() => {}} />);
    await screen.findByText(/Error: HTTP error! Status: 500/);
  });
});

describe('Settings — saving', () => {
  beforeEach(() => {
    apiFetch.mockResolvedValueOnce(
      jsonResponse({ language: 'en', questions_per_day: 10 }),
    );
  });

  it('PATCHes the new values and shows a confirmation', async () => {
    const user = userEvent.setup();
    render(<Settings onLoggedOut={() => {}} />);
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(10));

    apiFetch.mockResolvedValueOnce(
      jsonResponse({ language: 'es', questions_per_day: 20 }),
    );
    await user.selectOptions(screen.getByRole('combobox'), 'es');
    const input = screen.getByRole('spinbutton');
    await user.clear(input);
    await user.type(input, '20');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await screen.findByText('Settings saved.');
    const patchCall = apiFetch.mock.calls.find((c) => c[1]?.method === 'PATCH');
    expect(JSON.parse(patchCall[1].body)).toEqual({
      language: 'es',
      questions_per_day: 20,
    });
  });

  it('rejects a questions-per-day below 1 without calling the API', async () => {
    const user = userEvent.setup();
    render(<Settings onLoggedOut={() => {}} />);
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(10));

    const input = screen.getByRole('spinbutton');
    await user.clear(input);
    await user.type(input, '0');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await screen.findByText(/Number of questions must be at least 1/);
    // Only the initial load call — no PATCH attempted.
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });
});

describe('Settings — account actions', () => {
  beforeEach(() => {
    apiFetch.mockResolvedValueOnce(
      jsonResponse({ language: 'en', questions_per_day: 10 }),
    );
  });

  it('logs out and notifies the parent', async () => {
    const onLoggedOut = vi.fn();
    logout.mockResolvedValueOnce({ ok: true });
    const user = userEvent.setup();
    render(<Settings onLoggedOut={onLoggedOut} />);
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(10));

    await user.click(screen.getByRole('button', { name: 'Log out' }));
    await waitFor(() => expect(onLoggedOut).toHaveBeenCalledTimes(1));
  });

  it('requires confirmation before deleting the account', async () => {
    const onLoggedOut = vi.fn();
    deleteAccount.mockResolvedValueOnce({ ok: true });
    const user = userEvent.setup();
    render(<Settings onLoggedOut={onLoggedOut} />);
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(10));

    // First click reveals the confirmation, does not delete.
    await user.click(screen.getByRole('button', { name: 'Delete account' }));
    expect(deleteAccount).not.toHaveBeenCalled();
    await screen.findByText(/This permanently deletes your account/);

    await user.click(screen.getByRole('button', { name: 'Delete permanently' }));
    await waitFor(() => expect(deleteAccount).toHaveBeenCalledTimes(1));
    expect(onLoggedOut).toHaveBeenCalledTimes(1);
  });

  it('cancels the delete confirmation', async () => {
    const user = userEvent.setup();
    render(<Settings onLoggedOut={() => {}} />);
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(10));

    await user.click(screen.getByRole('button', { name: 'Delete account' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(
      screen.queryByText(/This permanently deletes your account/),
    ).not.toBeInTheDocument();
    expect(deleteAccount).not.toHaveBeenCalled();
  });
});
