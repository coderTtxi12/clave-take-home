/**
 * TypeScript Type Definitions
 * 
 * This module contains all TypeScript interfaces and types used throughout
 * the dashboard application. It provides type safety and IntelliSense support
 * for:
 * - Message data structures
 * - Component props
 * - Hook return types
 * - API response types
 */

/**
 * Message interface representing a single chat message.
 * 
 * Messages can be from either the user or the AI assistant, and may
 * include attached files, images, and streaming state.
 */
export interface Message {
  id: number;
  text: string;
  sender: 'user' | 'ai';
  timestamp: string;
  files?: File[];
  isStreaming?: boolean;
  imageBase64?: string;  // Base64 encoded image from API
  imageMime?: string;    // MIME type of the image
}

/**
 * Component Props Interfaces
 * 
 * These interfaces define the props for each React component,
 * ensuring type safety and clear component contracts.
 */

/**
 * Props for the Header component.
 */
export interface HeaderProps {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  onClearChat: () => void;
}

export interface WelcomeSectionProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenFileDialog: () => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
}

export interface MessageListProps extends WelcomeSectionProps {
  messages: Message[];
  isStreaming: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

export interface MessageProps {
  message: Message;
}

export interface InputFormProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenFileDialog: () => void;
  selectedFiles: File[];
  placeholder?: string;
  className?: string;
}

export interface FilePreviewProps {
  files: File[];
  onRemoveFile: (index: number) => void;
}

/**
 * Hook Return Type Interfaces
 * 
 * These interfaces define the return types for custom React hooks,
 * ensuring consistent API across hook implementations.
 */

/**
 * Return type for the useChat hook.
 * 
 * Contains all state and functions needed for chat functionality.
 */
export interface UseChatReturn {
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  isLoading: boolean;
  isStreaming: boolean;
  selectedFiles: File[];
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  handleSubmit: (e: React.FormEvent) => Promise<void>;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  removeFile: (index: number) => void;
  openFileDialog: () => void;
  clearChat: () => void;
}

export interface UseThemeReturn {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
}

