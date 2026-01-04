/**
 * Components Barrel Export
 * 
 * This module provides a centralized export point for all React components
 * used in the dashboard. This allows for cleaner imports throughout the
 * application using the @/components alias.
 * 
 * Exported components:
 * - Header: Application header with theme toggle and clear chat
 * - WelcomeSection: Initial welcome screen when chat is empty
 * - MessageList: Active conversation view with message history
 * - Message: Individual message component with markdown rendering
 * - InputForm: Chat input form with auto-resize and file upload
 * - FilePreview: File attachment preview component
 * - TypingIndicator: Loading indicator for AI responses
 */
export { Header } from './Header/Header';
export { WelcomeSection } from './WelcomeSection/WelcomeSection';
export { MessageList } from './MessageList/MessageList';
export { Message } from './Message/Message';
export { InputForm } from './InputForm/InputForm';
export { FilePreview } from './FilePreview/FilePreview';
export { TypingIndicator } from './TypingIndicator/TypingIndicator';

