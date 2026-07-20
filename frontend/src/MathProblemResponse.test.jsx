import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MathProblemResponse from './MathProblemResponse.jsx';

function setup(props = {}) {
  const onCorrect = vi.fn();
  const onIncorrect = vi.fn();
  render(
    <MathProblemResponse
      solution="42"
      onCorrect={onCorrect}
      onIncorrect={onIncorrect}
      {...props}
    />,
  );
  return { onCorrect, onIncorrect, user: userEvent.setup() };
}

describe('MathProblemResponse', () => {
  it('calls onCorrect for an exact string match', async () => {
    const { onCorrect, onIncorrect, user } = setup();
    await user.type(screen.getByRole('textbox'), '42');
    await user.click(screen.getByRole('button'));
    expect(onCorrect).toHaveBeenCalledTimes(1);
    expect(onIncorrect).not.toHaveBeenCalled();
  });

  it('accepts a numerically-equal answer with different formatting', async () => {
    // "42.0" !== "42" as strings, but they are numerically equal.
    const { onCorrect, user } = setup();
    await user.type(screen.getByRole('textbox'), '42.0');
    await user.click(screen.getByRole('button'));
    expect(onCorrect).toHaveBeenCalledTimes(1);
  });

  it('calls onIncorrect and shows feedback for a wrong answer', async () => {
    const { onCorrect, onIncorrect, user } = setup();
    await user.type(screen.getByRole('textbox'), '7');
    await user.click(screen.getByRole('button'));
    expect(onCorrect).not.toHaveBeenCalled();
    expect(onIncorrect).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button')).toHaveTextContent('Incorrect!');
  });

  it('submits on Enter', async () => {
    const { onCorrect, user } = setup();
    await user.type(screen.getByRole('textbox'), '42{Enter}');
    expect(onCorrect).toHaveBeenCalledTimes(1);
  });

  it('clears the input after submitting', async () => {
    const { user } = setup();
    const input = screen.getByRole('textbox');
    await user.type(input, '7');
    await user.click(screen.getByRole('button'));
    expect(input).toHaveValue('');
  });

  it('does not require an onIncorrect handler', async () => {
    const { user } = setup({ onIncorrect: undefined });
    await user.type(screen.getByRole('textbox'), '7');
    // Should not throw despite the optional handler being absent.
    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('button')).toHaveTextContent('Incorrect!');
  });
});
