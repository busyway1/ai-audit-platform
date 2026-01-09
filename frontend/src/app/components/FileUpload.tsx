/**
 * FileUpload Component
 * Excel file upload with drag-and-drop and validation.
 */

import React, { useState, useCallback, useRef } from 'react';
import { cn } from './ui/utils';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import {
  Upload,
  FileSpreadsheet,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';

// --- Types ---

interface FileUploadProps {
  onUpload: (file: File) => Promise<UploadResult>;
  accept?: string;
  maxSizeMB?: number;
  disabled?: boolean;
  className?: string;
}

interface UploadResult {
  success: boolean;
  data?: ParsedExcelData;
  error?: string;
}

interface ParsedExcelData {
  fileName: string;
  sheetNames: string[];
  columns: string[];
  rowCount: number;
  preview: Record<string, unknown>[];
}

type UploadStatus = 'idle' | 'dragging' | 'uploading' | 'success' | 'error';

// --- Constants ---

const ACCEPTED_TYPES = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
  'application/vnd.ms-excel', // xls
];

const ACCEPTED_EXTENSIONS = ['.xlsx', '.xls'];

// --- Helper Functions ---

const validateFile = (file: File, maxSizeMB: number): string | null => {
  // Check file type
  const isValidType = ACCEPTED_TYPES.includes(file.type);
  const hasValidExtension = ACCEPTED_EXTENSIONS.some((ext) =>
    file.name.toLowerCase().endsWith(ext)
  );

  if (!isValidType && !hasValidExtension) {
    return 'Only Excel files are allowed (.xlsx, .xls)';
  }

  // Check file size
  const sizeMB = file.size / (1024 * 1024);
  if (sizeMB > maxSizeMB) {
    return `File size is too large (max ${maxSizeMB}MB)`;
  }

  return null;
};

// --- Main Component ---

export const FileUpload: React.FC<FileUploadProps> = ({
  onUpload,
  accept = '.xlsx,.xls',
  maxSizeMB = 10,
  disabled = false,
  className,
}) => {
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<ParsedExcelData | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle file selection
  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setUploadResult(null);

      // Validate file
      const validationError = validateFile(file, maxSizeMB);
      if (validationError) {
        setError(validationError);
        setStatus('error');
        return;
      }

      setSelectedFile(file);
      setStatus('uploading');
      setProgress(0);

      // Simulate progress (actual progress would come from upload API)
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      try {
        const result = await onUpload(file);
        clearInterval(progressInterval);

        if (result.success && result.data) {
          setProgress(100);
          setUploadResult(result.data);
          setStatus('success');
        } else {
          setError(result.error || 'Upload failed');
          setStatus('error');
        }
      } catch (err) {
        clearInterval(progressInterval);
        setError(err instanceof Error ? err.message : 'An error occurred during upload');
        setStatus('error');
      }
    },
    [maxSizeMB, onUpload]
  );

  // Handle drag events
  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setStatus('dragging');
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setStatus('idle');
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setStatus('idle');

      if (disabled) return;

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFile(files[0]);
      }
    },
    [disabled, handleFile]
  );

  // Handle click to select file
  const handleClick = useCallback(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.click();
    }
  }, [disabled]);

  // Handle file input change
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
    },
    [handleFile]
  );

  // Reset state
  const handleReset = useCallback(() => {
    setStatus('idle');
    setProgress(0);
    setError(null);
    setSelectedFile(null);
    setUploadResult(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  }, []);

  return (
    <div className={cn('w-full', className)}>
      {/* Drop Zone */}
      <div
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center transition-all cursor-pointer',
          status === 'idle' && 'border-gray-300 hover:border-blue-400 hover:bg-blue-50',
          status === 'dragging' && 'border-blue-500 bg-blue-50',
          status === 'uploading' && 'border-blue-500 bg-blue-50 cursor-wait',
          status === 'success' && 'border-green-500 bg-green-50',
          status === 'error' && 'border-red-500 bg-red-50',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        aria-label="File upload area"
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled}
        />

        {/* Idle State */}
        {status === 'idle' && (
          <div className="space-y-4">
            <Upload className="w-12 h-12 mx-auto text-gray-400" />
            <div>
              <p className="text-lg font-medium text-gray-700">
                Drag and drop an Excel file or click to upload
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Supported formats: .xlsx, .xls (max {maxSizeMB}MB)
              </p>
            </div>
          </div>
        )}

        {/* Dragging State */}
        {status === 'dragging' && (
          <div className="space-y-4">
            <Upload className="w-12 h-12 mx-auto text-blue-500 animate-bounce" />
            <p className="text-lg font-medium text-blue-600">
              Drop the file here
            </p>
          </div>
        )}

        {/* Uploading State */}
        {status === 'uploading' && selectedFile && (
          <div className="space-y-4">
            <Loader2 className="w-12 h-12 mx-auto text-blue-500 animate-spin" />
            <div>
              <p className="text-lg font-medium text-blue-600">Uploading...</p>
              <p className="text-sm text-gray-500">{selectedFile.name}</p>
            </div>
            <Progress value={progress} className="w-64 mx-auto" />
          </div>
        )}

        {/* Success State */}
        {status === 'success' && uploadResult && (
          <div className="space-y-4">
            <CheckCircle className="w-12 h-12 mx-auto text-green-500" />
            <div>
              <p className="text-lg font-medium text-green-600">
                Upload complete!
              </p>
              <p className="text-sm text-gray-500">{uploadResult.fileName}</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {status === 'error' && (
          <div className="space-y-4">
            <AlertCircle className="w-12 h-12 mx-auto text-red-500" />
            <p className="text-lg font-medium text-red-600">Upload failed</p>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Upload Result Preview */}
      {uploadResult && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-green-600" />
              Parsed Result
            </h4>
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <X className="w-4 h-4 mr-1" />
              Upload again
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">File name:</span>
              <span className="ml-2 font-medium">{uploadResult.fileName}</span>
            </div>
            <div>
              <span className="text-gray-500">Rows:</span>
              <span className="ml-2 font-medium">
                {uploadResult.rowCount.toLocaleString()}
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">Sheets:</span>
              <span className="ml-2 font-medium">
                {uploadResult.sheetNames.join(', ')}
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">Columns:</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {uploadResult.columns.map((col) => (
                  <span
                    key={col}
                    className="px-2 py-0.5 bg-white border rounded text-xs"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Preview Table */}
          {uploadResult.preview.length > 0 && (
            <div className="mt-4">
              <h5 className="text-sm font-medium text-gray-700 mb-2">
                Preview (first 3 rows)
              </h5>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border">
                  <thead className="bg-gray-100">
                    <tr>
                      {uploadResult.columns.slice(0, 5).map((col) => (
                        <th key={col} className="px-2 py-1 border text-left">
                          {col}
                        </th>
                      ))}
                      {uploadResult.columns.length > 5 && (
                        <th className="px-2 py-1 border text-left">...</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {uploadResult.preview.slice(0, 3).map((row, i) => (
                      <tr key={i}>
                        {uploadResult.columns.slice(0, 5).map((col) => (
                          <td key={col} className="px-2 py-1 border truncate max-w-32">
                            {String(row[col] ?? '')}
                          </td>
                        ))}
                        {uploadResult.columns.length > 5 && (
                          <td className="px-2 py-1 border">...</td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;

// Export types for external use
export type { FileUploadProps, UploadResult, ParsedExcelData, UploadStatus };
