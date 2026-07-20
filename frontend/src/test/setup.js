// Vitest setup, loaded once before the test suite (see vite.config.js).
//
// - Adds jest-dom matchers (toBeInTheDocument, toHaveTextContent, ...).
// - Clears mocks and unmounts React trees between tests so state never leaks.

import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
