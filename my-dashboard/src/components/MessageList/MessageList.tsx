/**
 * Message List Component
 * 
 * This component displays the active chat conversation with:
 * - Scrollable message list
 * - Individual message components
 * - Typing indicator when loading
 * - Input form at the bottom
 * - File preview for selected files
 * - Auto-scroll to latest message (via messagesEndRef)
 * 
 * The component is shown when there are messages in the conversation,
 * replacing the WelcomeSection once the user starts chatting.
 */
'use client';

import React from 'react';
import { MessageListProps } from '@/types';
import { Message } from '../Message/Message';
import { TypingIndicator } from '../TypingIndicator/TypingIndicator';
import { InputForm } from '../InputForm/InputForm';
import { FilePreview } from '../FilePreview/FilePreview';
import styles from './MessageList.module.css';

/**
 * Message list component for active conversations.
 * 
 * Renders all messages in the conversation, shows typing indicator
 * when loading, and provides input form for new messages.
 * 
 * @param props - MessageListProps containing messages, input state, and handlers
 */
export const MessageList: React.FC<MessageListProps> = ({ 
  messages, 
  isLoading, 
  isStreaming,
  messagesEndRef,
  inputValue,
  setInputValue,
  onSubmit,
  inputRef,
  fileInputRef,
  onFileSelect,
  onOpenFileDialog,
  selectedFiles,
  onRemoveFile
}) => {
  return (
    <div className={styles.chatContainer}>
      <div className={styles.messagesContainer}>
        {messages.map((message) => (
          <Message
            key={message.id}
            message={message}
          />
        ))}
        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>
      
      <div className={styles.chatInputSection}>
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
          className="chat-input-form"
        />
      </div>
    </div>
  );
};

