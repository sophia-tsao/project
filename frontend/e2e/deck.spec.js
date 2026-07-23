import { test, expect } from '@playwright/test';
import { resetUser, selectFirstCourse, setQuestionsPerDay, answerProblem } from './fixtures.js';

// Track the solution for the problem currently on screen. The /deck/ and
// /deck/advance/ responses each carry the solution for the card they return, so
// the most recent one always matches what's displayed. We normalise it the same
// way MathProblem does (strip the LaTeX '$').
function trackSolutions(page) {
  const state = { current: null };
  page.on('response', async (res) => {
    const url = res.url();
    if (!url.includes('/deck/')) return;
    try {
      const body = await res.json();
      if (typeof body.solution === 'string') {
        state.current = body.solution.replace(/\$/g, '');
      }
    } catch {
      // Non-JSON or already-consumed body — ignore.
    }
  });
  return state;
}

test.describe('daily deck', () => {
  test('shows the no-topics prompt when nothing is selected', async ({ page }) => {
    await resetUser(page);
    await page.goto('/#/math');
    await expect(
      page.getByText('Select topics from the Courses page to get started.'),
    ).toBeVisible();
  });

  test('renders a problem once a topic is selected', async ({ page }) => {
    await resetUser(page);
    await selectFirstCourse(page);
    await page.goto('/#/math');
    await expect(page.locator('.math-problem-progress')).toContainText('of');
    await expect(page.locator('.math-problem-input')).toBeVisible();
    await expect(page.locator('.math-problem-attempt')).toContainText('Attempt 1 of 2');
  });

  test('a correct answer advances to the next problem', async ({ page }) => {
    await resetUser(page);
    await selectFirstCourse(page);
    const solutions = trackSolutions(page);

    await page.goto('/#/math');
    await expect(page.locator('.math-problem-progress')).toContainText('1 of');

    await answerProblem(page, solutions.current, { correct: true });
    // A brief "Correct!" confirmation, then the next card.
    await expect(page.locator('.math-problem-correct-text')).toBeVisible();
    await expect(page.locator('.math-problem-progress')).toContainText('2 of');
  });

  test('a wrong answer consumes an attempt; two wrongs advance', async ({ page }) => {
    await resetUser(page);
    await selectFirstCourse(page);
    const solutions = trackSolutions(page);

    await page.goto('/#/math');
    await expect(page.locator('.math-problem-progress')).toContainText('1 of');

    // First wrong attempt: feedback shows, still on question 1, now attempt 2.
    await answerProblem(page, solutions.current, { correct: false });
    await expect(page.locator('.math-problem-submit')).toContainText('Incorrect!');
    await expect(page.locator('.math-problem-attempt')).toContainText('Attempt 2 of 2');
    await expect(page.locator('.math-problem-progress')).toContainText('1 of');

    // Second wrong attempt: out of attempts, the card flips to reveal the
    // answer and waits. Clicking Continue accepts the miss and advances.
    await answerProblem(page, solutions.current, { correct: false });
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.locator('.math-problem-progress')).toContainText('2 of');
  });

  test('overriding an incorrect answer advances to the next question', async ({ page }) => {
    await resetUser(page);
    await selectFirstCourse(page);
    const solutions = trackSolutions(page);

    await page.goto('/#/math');
    await expect(page.locator('.math-problem-progress')).toContainText('1 of');

    // Burn both attempts, then override the miss via "I got this correct".
    await answerProblem(page, solutions.current, { correct: false });
    await expect(page.locator('.math-problem-attempt')).toContainText('Attempt 2 of 2');
    await answerProblem(page, solutions.current, { correct: false });
    await page.getByRole('button', { name: 'I got this correct' }).click();
    await expect(page.locator('.math-problem-progress')).toContainText('2 of');
  });

  test('finishing the deck shows the completion screen', async ({ page }) => {
    await resetUser(page);
    await selectFirstCourse(page);
    await setQuestionsPerDay(page, 2); // keep it short
    const solutions = trackSolutions(page);

    await page.goto('/#/math');
    await expect(page.locator('.math-problem-progress')).toContainText('1 of 2');

    await answerProblem(page, solutions.current, { correct: true });
    await expect(page.locator('.math-problem-progress')).toContainText('2 of 2');

    await answerProblem(page, solutions.current, { correct: true });
    await expect(page.getByText(/You've finished all 2 questions for today/)).toBeVisible();
  });
});
