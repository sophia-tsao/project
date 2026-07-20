import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock the network layer so the component's fetch/advance calls are scripted.
// localDay is stubbed to a fixed date so deck-request URLs are deterministic;
// the day-rollover tests override it via mockReturnValue.
vi.mock('./auth.js', () => ({
  apiFetch: vi.fn(),
  localDay: vi.fn(() => '2026-07-20'),
}));
// KaTeX is heavy and irrelevant to behaviour; stub its render to a no-op string.
vi.mock('katex', () => ({ default: { renderToString: () => '' } }));

import { apiFetch, localDay } from './auth.js';
import MathProblem from './MathProblem.jsx';

// Build a Response-like object from a deck payload.
function deckResponse(payload, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => payload };
}

const ACTIVE_DECK = {
  problem: 'What is $2+2$?',
  solution: '4',
  current_number: 1,
  total: 3,
};

beforeEach(() => {
  apiFetch.mockReset();
  localDay.mockReset();
  localDay.mockReturnValue('2026-07-20');
  localStorage.clear();
});

describe('MathProblem — initial load', () => {
  it('renders the active problem after fetching the deck', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse(ACTIVE_DECK));
    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');
    expect(screen.getByText('Attempt 1 of 2')).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith('/deck/?today=2026-07-20');
  });

  it('shows the no-topics prompt when the deck is empty', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse({ no_topics: true }));
    render(<MathProblem />);
    await screen.findByText(/Select topics from the Courses page/);
  });

  it('shows the completion message with pluralized count', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse({ completed: true, total: 5 }));
    render(<MathProblem />);
    await screen.findByText(/You've finished all 5 questions for today/);
  });

  it('uses singular wording for a one-question deck', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse({ completed: true, total: 1 }));
    render(<MathProblem />);
    await screen.findByText(/all 1 question for today/);
  });

  it('renders an error message when the fetch fails', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse({}, { ok: false, status: 500 }));
    render(<MathProblem />);
    await screen.findByText(/Error: HTTP error! Status: 500/);
  });
});

describe('MathProblem — day rollover', () => {
  it('reloads the deck when the local day rolls over and the tab is refocused', async () => {
    // Mounted on the 20th showing yesterday's finished deck, then a fresh deck
    // for the 21st after midnight.
    apiFetch
      .mockResolvedValueOnce(deckResponse({ completed: true, total: 3 }))
      .mockResolvedValueOnce(deckResponse(ACTIVE_DECK));

    render(<MathProblem />);
    await screen.findByText(/You've finished all 3 questions for today/);
    expect(apiFetch).toHaveBeenCalledTimes(1);

    // Cross midnight into the new local day, then the tab regains focus.
    localDay.mockReturnValue('2026-07-21');
    window.dispatchEvent(new Event('focus'));

    await screen.findByText('1 of 3 questions');
    expect(apiFetch).toHaveBeenCalledTimes(2);
    expect(apiFetch).toHaveBeenLastCalledWith('/deck/?today=2026-07-21');
  });

  it('does not reload on refocus within the same day', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse(ACTIVE_DECK));

    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');
    expect(apiFetch).toHaveBeenCalledTimes(1);

    // Same day (localDay unchanged): refocusing must not re-fetch — that would
    // discard local attempt state.
    window.dispatchEvent(new Event('focus'));

    // Give any erroneous fetch a chance to fire before asserting it didn't.
    await Promise.resolve();
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });
});

describe('MathProblem — answering', () => {
  it('advances to the next problem after a correct answer', async () => {
    const user = userEvent.setup();
    apiFetch
      .mockResolvedValueOnce(deckResponse(ACTIVE_DECK))
      .mockResolvedValueOnce(
        deckResponse({ ...ACTIVE_DECK, current_number: 2 }),
      );

    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');

    await user.type(screen.getByRole('textbox'), '4');
    await user.click(screen.getByRole('button'));

    // "Correct!" interstitial shows before the 900ms advance fires.
    expect(screen.getByText('Correct!')).toBeInTheDocument();

    // The advance is triggered by a real 900ms setTimeout, so allow headroom.
    expect(await screen.findByText('2 of 3 questions', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith('/deck/advance/?today=2026-07-20', { method: 'POST' });
  });

  it('bumps the attempt counter on the first wrong answer', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse(ACTIVE_DECK));
    const user = userEvent.setup();
    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');

    await user.type(screen.getByRole('textbox'), '99');
    await user.click(screen.getByRole('button'));

    await screen.findByText('Attempt 2 of 2');
    // No advance call yet — the user still has an attempt left.
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });

  it('advances after exhausting all attempts', async () => {
    apiFetch
      .mockResolvedValueOnce(deckResponse(ACTIVE_DECK))
      .mockResolvedValueOnce(deckResponse({ ...ACTIVE_DECK, current_number: 2 }));
    const user = userEvent.setup();
    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');

    const input = screen.getByRole('textbox');
    const button = screen.getByRole('button');
    await user.type(input, '99');
    await user.click(button); // attempt 1 -> 2
    await screen.findByText('Attempt 2 of 2');
    await user.type(input, '98');
    await user.click(button); // attempt 2 exhausted -> flip, then advance

    // The card flips to reveal the correct answer on its back...
    expect(screen.getByText('Incorrect...')).toBeInTheDocument();
    expect(screen.getByText('The answer is 4')).toBeInTheDocument();

    // ...then advances once the 1400ms flip has been read. Allow headroom.
    await waitFor(
      () =>
        expect(apiFetch).toHaveBeenCalledWith('/deck/advance/?today=2026-07-20', { method: 'POST' }),
      { timeout: 2500 },
    );
  });

  // Regression: the back face used to derive its outcome from the same state
  // that triggered the flip, so clearing that state on advance re-rendered the
  // back to the "Correct!" branch — a flash of "Correct!" while the card
  // rotated back after a wrong answer. The back must keep saying "Incorrect..."
  // through the flip-back onto the next problem.
  it('keeps the incorrect result on the back face while flipping to the next problem', async () => {
    apiFetch
      .mockResolvedValueOnce(deckResponse(ACTIVE_DECK))
      .mockResolvedValueOnce(
        deckResponse({ ...ACTIVE_DECK, solution: '7', current_number: 2 }),
      );
    const user = userEvent.setup();
    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');

    const input = screen.getByRole('textbox');
    const button = screen.getByRole('button');
    await user.type(input, '99');
    await user.click(button); // attempt 1 -> 2
    await screen.findByText('Attempt 2 of 2');
    await user.type(input, '98');
    await user.click(button); // exhausted -> flip to "Incorrect..."

    expect(screen.getByText('Incorrect...')).toBeInTheDocument();

    // Advance loads the next problem; the back face must not flash "Correct!".
    await screen.findByText('2 of 3 questions', {}, { timeout: 2500 });
    expect(screen.queryByText('Correct!')).not.toBeInTheDocument();
    expect(screen.getByText('Incorrect...')).toBeInTheDocument();
  });

  // Regression: the back face read the live `solution`, so when advance loaded
  // the next problem the displayed answer briefly changed to the next
  // problem's solution mid-flip. The answer is frozen at flip time.
  it('freezes the revealed answer to the answered problem while flipping away', async () => {
    apiFetch
      .mockResolvedValueOnce(deckResponse(ACTIVE_DECK)) // solution '4'
      .mockResolvedValueOnce(
        deckResponse({ ...ACTIVE_DECK, solution: '7', current_number: 2 }),
      );
    const user = userEvent.setup();
    render(<MathProblem />);
    await screen.findByText('1 of 3 questions');

    const input = screen.getByRole('textbox');
    const button = screen.getByRole('button');
    await user.type(input, '99');
    await user.click(button); // attempt 1 -> 2
    await screen.findByText('Attempt 2 of 2');
    await user.type(input, '98');
    await user.click(button); // exhausted -> flip showing "The answer is 4"

    expect(screen.getByText('The answer is 4')).toBeInTheDocument();

    // After the next problem (solution '7') loads, the back face must still
    // show '4' — never '7'.
    await screen.findByText('2 of 3 questions', {}, { timeout: 2500 });
    expect(screen.getByText('The answer is 4')).toBeInTheDocument();
    expect(screen.queryByText('The answer is 7')).not.toBeInTheDocument();
  });
});

const CONFETTI_KEY = 'solveki-confetti-2026-07-20';

describe('MathProblem — completion confetti', () => {
  it('fires confetti when the student answers the last card', async () => {
    const user = userEvent.setup();
    apiFetch
      .mockResolvedValueOnce(deckResponse({ ...ACTIVE_DECK, total: 1 }))
      .mockResolvedValueOnce(deckResponse({ completed: true, total: 1 }));

    const { container } = render(<MathProblem />);
    await screen.findByText('1 of 1 questions');

    await user.type(screen.getByRole('textbox'), '4');
    await user.click(screen.getByRole('button'));

    await screen.findByText(/You've finished all 1 question/, {}, { timeout: 2500 });
    expect(container.querySelector('.confetti')).toBeInTheDocument();
  });

  // Regression: maybeCelebrate ran on *every* transition into `completed`,
  // including a passive load that lands on an already-finished deck (the mount
  // fetch, or the day-rollover refetch on refocus). That silently burned the
  // once-per-day localStorage token, so the student's genuine finish later that
  // day showed no confetti. A passive completed-load must neither celebrate nor
  // consume the token.
  it('does not fire — or burn the daily token — on a passive completed-load', async () => {
    apiFetch.mockResolvedValueOnce(deckResponse({ completed: true, total: 3 }));

    const { container } = render(<MathProblem />);
    await screen.findByText(/You've finished all 3 questions/);

    expect(container.querySelector('.confetti')).not.toBeInTheDocument();
    // The token is untouched, so a real finish later today can still celebrate.
    expect(localStorage.getItem(CONFETTI_KEY)).toBeNull();
  });

  it('still celebrates a genuine finish after a passive completed-load earlier that day', async () => {
    const user = userEvent.setup();
    // First: a passive load onto a finished deck (must not consume the token)...
    apiFetch
      .mockResolvedValueOnce(deckResponse({ completed: true, total: 1 }))
      // ...then the student works and finishes a fresh deck.
      .mockResolvedValueOnce(deckResponse({ ...ACTIVE_DECK, total: 1 }))
      .mockResolvedValueOnce(deckResponse({ completed: true, total: 1 }));

    const { container, unmount } = render(<MathProblem />);
    await screen.findByText(/You've finished all 1 question/);
    expect(container.querySelector('.confetti')).not.toBeInTheDocument();
    unmount();

    const { container: c2 } = render(<MathProblem />);
    await screen.findByText('1 of 1 questions');
    await user.type(screen.getByRole('textbox'), '4');
    await user.click(screen.getByRole('button'));

    await screen.findByText(/You've finished all 1 question/, {}, { timeout: 2500 });
    expect(c2.querySelector('.confetti')).toBeInTheDocument();
  });

  it('fires confetti at most once per day', async () => {
    const user = userEvent.setup();
    // A genuine finish that celebrates and sets the token...
    apiFetch
      .mockResolvedValueOnce(deckResponse({ ...ACTIVE_DECK, total: 1 }))
      .mockResolvedValueOnce(deckResponse({ completed: true, total: 1 }));

    const { container, unmount } = render(<MathProblem />);
    await screen.findByText('1 of 1 questions');
    await user.type(screen.getByRole('textbox'), '4');
    await user.click(screen.getByRole('button'));
    await screen.findByText(/You've finished all 1 question/, {}, { timeout: 2500 });
    expect(container.querySelector('.confetti')).toBeInTheDocument();
    unmount();

    // ...a second finish the same day must not celebrate again.
    apiFetch
      .mockResolvedValueOnce(deckResponse({ ...ACTIVE_DECK, total: 1 }))
      .mockResolvedValueOnce(deckResponse({ completed: true, total: 1 }));

    const { container: c2 } = render(<MathProblem />);
    await screen.findByText('1 of 1 questions');
    await user.type(screen.getByRole('textbox'), '4');
    await user.click(screen.getByRole('button'));
    await screen.findByText(/You've finished all 1 question/, {}, { timeout: 2500 });
    expect(c2.querySelector('.confetti')).not.toBeInTheDocument();
  });
});
