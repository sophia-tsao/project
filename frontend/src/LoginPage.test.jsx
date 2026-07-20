import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('./auth.js', () => ({ loginWithGoogle: vi.fn() }));

import { loginWithGoogle } from './auth.js';
import LoginPage from './LoginPage.jsx';

// Capture the callback GSI is initialized with so tests can simulate Google
// invoking it with a credential.
let capturedCallback = null;

beforeEach(() => {
  loginWithGoogle.mockReset();
  capturedCallback = null;
  window.google = {
    accounts: {
      id: {
        initialize: vi.fn(({ callback }) => {
          capturedCallback = callback;
        }),
        renderButton: vi.fn(),
      },
    },
  };
});

afterEach(() => {
  delete window.google;
});

describe('LoginPage', () => {
  it('shows the landing view first', () => {
    render(<LoginPage onLoggedIn={() => {}} />);
    expect(
      screen.getByRole('button', { name: 'Log in / Register' }),
    ).toBeInTheDocument();
  });

  it('renders the Google button after entering the login view', async () => {
    const user = userEvent.setup();
    render(<LoginPage onLoggedIn={() => {}} />);
    await user.click(screen.getByRole('button', { name: 'Log in / Register' }));

    await waitFor(() =>
      expect(window.google.accounts.id.renderButton).toHaveBeenCalled(),
    );
    expect(screen.getByText('Log in or register to continue')).toBeInTheDocument();
  });

  it('calls onLoggedIn with the user after a successful credential exchange', async () => {
    const onLoggedIn = vi.fn();
    loginWithGoogle.mockResolvedValueOnce({ user: { name: 'Ada' } });
    const user = userEvent.setup();
    render(<LoginPage onLoggedIn={onLoggedIn} />);
    await user.click(screen.getByRole('button', { name: 'Log in / Register' }));
    await waitFor(() => expect(capturedCallback).toBeInstanceOf(Function));

    await capturedCallback({ credential: 'google-jwt' });

    expect(loginWithGoogle).toHaveBeenCalledWith('google-jwt');
    await waitFor(() =>
      expect(onLoggedIn).toHaveBeenCalledWith({ name: 'Ada' }),
    );
  });

  it('surfaces an error when the credential exchange fails', async () => {
    loginWithGoogle.mockRejectedValueOnce(new Error('bad token'));
    const user = userEvent.setup();
    render(<LoginPage onLoggedIn={() => {}} />);
    await user.click(screen.getByRole('button', { name: 'Log in / Register' }));
    await waitFor(() => expect(capturedCallback).toBeInstanceOf(Function));

    await capturedCallback({ credential: 'x' });

    await screen.findByText('bad token');
  });

  it('returns to the landing view via Back', async () => {
    const user = userEvent.setup();
    render(<LoginPage onLoggedIn={() => {}} />);
    await user.click(screen.getByRole('button', { name: 'Log in / Register' }));
    await screen.findByText('Log in or register to continue');

    await user.click(screen.getByRole('button', { name: 'Back' }));
    expect(
      screen.getByRole('button', { name: 'Log in / Register' }),
    ).toBeInTheDocument();
  });
});
