import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Header from './Header.jsx';

describe('Header', () => {
  it('marks the current page button as active', () => {
    render(<Header currentPage="settings" linkClicked={() => {}} />);
    expect(screen.getByRole('button', { name: 'Settings' })).toHaveClass('active');
    expect(screen.getByRole('button', { name: 'Practice' })).not.toHaveClass('active');
  });

  it('calls linkClicked with the target page key', async () => {
    const linkClicked = vi.fn();
    const user = userEvent.setup();
    render(<Header currentPage="math" linkClicked={linkClicked} />);
    await user.click(screen.getByRole('button', { name: 'Available Courses' }));
    expect(linkClicked).toHaveBeenCalledWith('courses');
  });
});
