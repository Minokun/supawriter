/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WriterForm } from '@/components/writer/WriterForm';

// Mock API
jest.mock('@/lib/articles', () => ({
  generateArticle: jest.fn(),
}));

describe('WriterForm', () => {
  it('renders form inputs', () => {
    render(<WriterForm />);

    expect(screen.getByLabelText(/文章主题/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/写作风格要求/i)).toBeInTheDocument();
  });

  it('validates required topic', async () => {
    const { generateArticle } = require('@/lib/articles');
    generateArticle.mockResolvedValue({ task_id: 'test_123' });

    render(<WriterForm />);

    const submitButton = screen.getByRole('button', { name: /开始创作/i });
    await userEvent.click(submitButton);

    expect(screen.getByText(/请输入文章主题/i)).toBeInTheDocument();
  });

  it('submits form with valid data', async () => {
    const { generateArticle } = require('@/lib/articles');
    generateArticle.mockResolvedValue({ task_id: 'test_123' });

    const onSubmit = jest.fn();
    render(<WriterForm onSubmit={onSubmit} />);

    const topicInput = screen.getByLabelText(/文章主题/i);
    await userEvent.type(topicInput, '测试主题');

    const submitButton = screen.getByRole('button', { name: /开始创作/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith('test_123');
    });
  });
});
