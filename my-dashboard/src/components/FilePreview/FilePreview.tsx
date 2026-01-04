/**
 * File Preview Component
 * 
 * This component displays a preview of selected files before they are
 * attached to a message. It provides:
 * - Thumbnail previews for images
 * - File type icons for non-image files
 * - File name and size display
 * - Remove file functionality
 * 
 * The component automatically generates thumbnails for image files
 * and uses Material Icons for other file types.
 */
'use client';

import React, { useState, useEffect } from 'react';
import { FilePreviewProps } from '@/types';
import styles from './FilePreview.module.css';

/**
 * Get the appropriate Material Icon name for a file type.
 * 
 * Maps file MIME types to Material Icons for visual representation.
 * 
 * @param file - File object to get icon for
 * @returns Material Icon name string
 */
const getFileIcon = (file: File): string => {
  const type = file.type;
  if (type.startsWith('image/')) return 'image';
  if (type.startsWith('video/')) return 'movie';
  if (type.startsWith('audio/')) return 'audiotrack';
  if (type.includes('pdf')) return 'picture_as_pdf';
  if (type.includes('word') || type.includes('document')) return 'description';
  if (type.includes('excel') || type.includes('spreadsheet')) return 'table_chart';
  if (type.includes('powerpoint') || type.includes('presentation')) return 'slideshow';
  if (type.includes('zip') || type.includes('rar')) return 'folder_zip';
  return 'insert_drive_file';
};

/**
 * Format file size in bytes to human-readable string.
 * 
 * Converts bytes to appropriate unit (Bytes, KB, MB, GB) with
 * 2 decimal places precision.
 * 
 * @param bytes - File size in bytes
 * @returns Formatted file size string (e.g., "1.5 MB")
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Create a thumbnail preview for image files.
 * 
 * For image files, creates a data URL that can be used as an image source.
 * For non-image files, returns null (icon will be used instead).
 * 
 * @param file - File object to create thumbnail for
 * @returns Promise resolving to data URL string or null
 */
const createThumbnail = (file: File): Promise<string | null> => {
  return new Promise((resolve) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      resolve(null);
    }
  });
};

interface FileThumbnailProps {
  file: File;
  index: number;
  onRemove: () => void;
}

/**
 * Individual file thumbnail component.
 * 
 * Displays a single file with:
 * - Image thumbnail (if image file)
 * - File type icon (if non-image)
 * - File name (truncated if too long)
 * - File size
 * - Remove button
 * 
 * @param file - File object to display
 * @param index - Index of file in the list
 * @param onRemove - Callback function to remove this file
 */
const FileThumbnail: React.FC<FileThumbnailProps> = ({ file, onRemove }) => {
  const [thumbnail, setThumbnail] = useState<string | null>(null);

  useEffect(() => {
    createThumbnail(file).then(setThumbnail);
  }, [file]);

  return (
    <div className={styles.fileThumbnail}>
      <div className={styles.fileThumbnailContent}>
        {thumbnail ? (
          <img src={thumbnail} alt={file.name} className={styles.fileThumbnailImage} />
        ) : (
          <div className={styles.fileThumbnailIcon}>
            <span className="material-icons">{getFileIcon(file)}</span>
          </div>
        )}
        <div className={styles.fileThumbnailInfo}>
          <div className={styles.fileName} title={file.name}>
            {file.name.length > 15 ? `${file.name.substring(0, 15)}...` : file.name}
          </div>
          <div className={styles.fileSize}>{formatFileSize(file.size)}</div>
        </div>
      </div>
      <button 
        className={styles.removeFileBtn}
        onClick={onRemove}
        title="Remove file"
      >
        <span className="material-icons">close</span>
      </button>
    </div>
  );
};

/**
 * File preview component that displays all selected files.
 * 
 * Renders a list of file thumbnails with previews for images
 * and icons for other file types. Each file can be removed
 * individually.
 * 
 * Returns null if no files are selected (doesn't render anything).
 * 
 * @param files - Array of File objects to preview
 * @param onRemoveFile - Callback function to remove a file by index
 */
export const FilePreview: React.FC<FilePreviewProps> = ({ files, onRemoveFile }) => {
  if (!files || files.length === 0) return null;

  return (
    <div className={styles.filePreviewContainer}>
      <div className={styles.filePreviewList}>
        {files.map((file, index) => (
          <FileThumbnail
            key={`${file.name}-${index}`}
            file={file}
            index={index}
            onRemove={() => onRemoveFile(index)}
          />
        ))}
      </div>
    </div>
  );
};

