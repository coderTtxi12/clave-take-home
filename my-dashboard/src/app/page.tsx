/**
 * Main Application Page
 * 
 * This is the root page component for the Data Analyst Agent dashboard.
 * It orchestrates the main UI components and handles drag-and-drop file uploads.
 * 
 * Features:
 * - Theme switching (dark/light mode)
 * - Chat interface with message history
 * - File upload via drag-and-drop or file picker
 * - Welcome screen when no messages exist
 * - Message list view when conversation is active
 * 
 * The page uses the useChat hook for conversation management and the useTheme
 * hook for theme persistence. It conditionally renders either the WelcomeSection
 * (empty state) or MessageList (active conversation) based on message count.
 */
'use client';

import React, { useState } from 'react';
import { useTheme, useChat } from '@/hooks';
import { Header, WelcomeSection, MessageList } from '@/components';

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  const {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    isStreaming,
    selectedFiles,
    messagesEndRef,
    inputRef,
    fileInputRef,
    handleSubmit,
    handleFileSelect,
    removeFile,
    openFileDialog,
    clearChat
  } = useChat();

  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const syntheticEvent = {
        target: { files }
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      handleFileSelect(syntheticEvent);
    }
  };

  return (
    <div 
      className="app"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <Header
        theme={theme}
        toggleTheme={toggleTheme}
        onClearChat={clearChat}
      />

      <main className="main-content">
        {messages.length === 0 ? (
          <WelcomeSection
            inputValue={inputValue}
            setInputValue={setInputValue}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            inputRef={inputRef}
            fileInputRef={fileInputRef}
            onFileSelect={handleFileSelect}
            onOpenFileDialog={openFileDialog}
            selectedFiles={selectedFiles}
            onRemoveFile={removeFile}
          />
        ) : (
          <MessageList
            messages={messages}
            isLoading={isLoading}
            isStreaming={isStreaming}
            messagesEndRef={messagesEndRef}
            inputValue={inputValue}
            setInputValue={setInputValue}
            onSubmit={handleSubmit}
            inputRef={inputRef}
            fileInputRef={fileInputRef}
            onFileSelect={handleFileSelect}
            onOpenFileDialog={openFileDialog}
            selectedFiles={selectedFiles}
            onRemoveFile={removeFile}
          />
        )}
      </main>
    </div>
  );
}
