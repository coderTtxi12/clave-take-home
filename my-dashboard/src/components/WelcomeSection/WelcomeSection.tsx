/**
 * Welcome Section Component
 * 
 * This component displays the initial welcome screen when there are no
 * messages in the chat. It provides:
 * - Welcome message and description
 * - Input form for starting a conversation
 * - File preview for selected files
 * 
 * The welcome section is shown when messages.length === 0, providing
 * a clean starting point for new conversations.
 */
'use client';

import React from 'react';
import { WelcomeSectionProps } from '@/types';
import { InputForm } from '../InputForm/InputForm';
import { FilePreview } from '../FilePreview/FilePreview';
import styles from './WelcomeSection.module.css';

/**
 * Welcome section component displayed when chat is empty.
 * 
 * Provides a centered welcome message and input form to start
 * a new conversation. Includes file preview for any selected files.
 * 
 * @param props - WelcomeSectionProps containing input state and handlers
 */
export const WelcomeSection: React.FC<WelcomeSectionProps> = ({ 
  inputValue, 
  setInputValue, 
  onSubmit, 
  isLoading, 
  inputRef,
  fileInputRef,
  onFileSelect,
  onOpenFileDialog,
  selectedFiles,
  onRemoveFile
}) => {
  return (
    <div className={styles.welcomeSection}>
      <h2 className={styles.welcomeTitle}>Chat with your restaurant data</h2>
      <p className={styles.welcomeDescription}>
        Query sales, revenue, and performance metrics using natural language
      </p>
      <FilePreview 
        files={selectedFiles}
        onRemoveFile={onRemoveFile}
      />
      <InputForm
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSubmit={onSubmit}
        isLoading={isLoading}
        inputRef={inputRef}
        fileInputRef={fileInputRef}
        onFileSelect={onFileSelect}
        onOpenFileDialog={onOpenFileDialog}
        selectedFiles={selectedFiles}
        placeholder="Ask anything"
        className="centered-input-form"
      />
    </div>
  );
};

