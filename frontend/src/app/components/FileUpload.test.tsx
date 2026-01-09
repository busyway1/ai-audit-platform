import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileUpload } from './FileUpload';

const mockUploadResult = {
  success: true,
  data: {
    fileName: 'test.xlsx',
    sheetNames: ['Sheet1'],
    columns: ['Business Process', 'Primary FSLI', 'EGA Type'],
    rowCount: 100,
    preview: [
      { 'Business Process': 'Revenue', 'Primary FSLI': 'AR', 'EGA Type': 'Test' },
    ],
  },
};

describe('FileUpload', () => {
  it('renders upload zone', () => {
    render(<FileUpload onUpload={vi.fn()} />);
    expect(screen.getByText(/drag and drop an excel file/i)).toBeInTheDocument();
  });

  it('shows supported formats', () => {
    render(<FileUpload onUpload={vi.fn()} />);
    expect(screen.getByText(/\.xlsx, \.xls/)).toBeInTheDocument();
  });

  it('handles file selection via click', async () => {
    const handleUpload = vi.fn().mockResolvedValue(mockUploadResult);
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(handleUpload).toHaveBeenCalledWith(file);
    });
  });

  it('validates file type', async () => {
    const handleUpload = vi.fn();
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/only excel files are allowed/i)).toBeInTheDocument();
    });
    expect(handleUpload).not.toHaveBeenCalled();
  });

  it('validates file size', async () => {
    const handleUpload = vi.fn();
    render(<FileUpload onUpload={handleUpload} maxSizeMB={1} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    // Create a file larger than 1MB
    const largeContent = new Array(2 * 1024 * 1024).fill('a').join('');
    const file = new File([largeContent], 'large.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText(/file size is too large/i)).toBeInTheDocument();
    });
  });

  it('shows upload progress', async () => {
    const handleUpload = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockUploadResult), 500))
    );
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    expect(screen.getByText('Uploading...')).toBeInTheDocument();
  });

  it('shows success state with preview', async () => {
    const handleUpload = vi.fn().mockResolvedValue(mockUploadResult);
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText('Upload complete!')).toBeInTheDocument();
      expect(screen.getByText('Parsed Result')).toBeInTheDocument();
      // Business Process appears both in column pill and table header
      expect(screen.getAllByText('Business Process').length).toBeGreaterThan(0);
    });
  });

  it('shows error state on upload failure', async () => {
    const handleUpload = vi.fn().mockResolvedValue({
      success: false,
      error: 'Server error',
    });
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText('Upload failed')).toBeInTheDocument();
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });
  });

  it('allows reset after upload', async () => {
    const handleUpload = vi.fn().mockResolvedValue(mockUploadResult);
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText('Upload again')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Upload again'));
    expect(screen.getByText(/drag and drop an excel file/i)).toBeInTheDocument();
  });

  it('handles drag and drop', async () => {
    const handleUpload = vi.fn().mockResolvedValue(mockUploadResult);
    render(<FileUpload onUpload={handleUpload} />);

    const dropZone = screen.getByRole('button');

    // Drag enter
    fireEvent.dragEnter(dropZone);
    expect(screen.getByText('Drop the file here')).toBeInTheDocument();

    // Drag leave
    fireEvent.dragLeave(dropZone);
    expect(screen.getByText(/drag and drop an excel file/i)).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<FileUpload onUpload={vi.fn()} disabled />);
    const dropZone = screen.getByRole('button');
    expect(dropZone).toHaveClass('cursor-not-allowed');
  });

  it('handles exception during upload', async () => {
    const handleUpload = vi.fn().mockRejectedValue(new Error('Network error'));
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(screen.getByText('Upload failed')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('displays custom max size in help text', () => {
    render(<FileUpload onUpload={vi.fn()} maxSizeMB={5} />);
    expect(screen.getByText(/max 5MB/)).toBeInTheDocument();
  });

  it('shows file name and row count in parsed result', async () => {
    const handleUpload = vi.fn().mockResolvedValue(mockUploadResult);
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      // test.xlsx appears twice: once in success message, once in file info
      expect(screen.getAllByText('test.xlsx').length).toBeGreaterThan(0);
      expect(screen.getByText('100')).toBeInTheDocument(); // rowCount
      expect(screen.getByText('Sheet1')).toBeInTheDocument(); // sheetNames
    });
  });

  it('validates file by extension when type is empty', async () => {
    const handleUpload = vi.fn().mockResolvedValue(mockUploadResult);
    render(<FileUpload onUpload={handleUpload} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    // Some browsers may not set the MIME type, so test extension-based validation
    const file = new File(['test'], 'test.xlsx', { type: '' });

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(handleUpload).toHaveBeenCalledWith(file);
    });
  });

  it('does not call onUpload when drag and drop is disabled', async () => {
    const handleUpload = vi.fn();
    render(<FileUpload onUpload={handleUpload} disabled />);

    const dropZone = screen.getByRole('button');
    const file = new File(['test'], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    const dataTransfer = {
      files: [file],
      items: [],
      types: ['Files'],
    };

    fireEvent.drop(dropZone, { dataTransfer });

    // Wait a bit to ensure no async operations happened
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(handleUpload).not.toHaveBeenCalled();
  });
});
