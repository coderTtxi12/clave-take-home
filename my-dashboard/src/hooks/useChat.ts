/**
 * Chat Hook for Data Analyst Agent
 * 
 * This custom React hook manages the chat interface state and interactions
 * with the backend API. It handles:
 * - Message state management
 * - Session management (generates new session on page load)
 * - API communication via Next.js proxy route
 * - File upload handling
 * - Auto-scrolling to latest message
 * - Loading and streaming states
 * 
 * The hook uses a Next.js API proxy route (/api/coding-agent/query) which
 * forwards requests to the backend API. This avoids Mixed Content issues
 * and allows the frontend to use relative URLs.
 * 
 * Session Management:
 * - Generates a new session ID on each page load (not persisted across reloads)
 * - Session ID is sent with each request for conversation continuity
 * - Backend stores conversation history in Redis using session ID
 */
'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, UseChatReturn } from '@/types';

/**
 * Generate a new session ID for the current page session.
 * 
 * IMPORTANT: This generates a NEW session_id on each page load.
 * The session ID is not persisted across page reloads, ensuring
 * a fresh conversation context each time the page is loaded.
 * 
 * @returns A unique session ID string
 */
const getSessionId = (): string => {
  if (typeof window === 'undefined') return '';
  
  try {
    // Always generate a new session ID (don't retrieve from localStorage)
    // This ensures a fresh session on each page reload
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
    
    // Store it in localStorage for the current session (but won't be reused on reload)
    localStorage.setItem('coding_agent_session_id', newSessionId);
    
    return newSessionId;
  } catch (error) {
    // Fallback if localStorage is not available
    console.warn('localStorage not available, using temporary session ID');
    return `session-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
  }
};

/**
 * Get the API endpoint for chat queries.
 * 
 * Always uses the Next.js API proxy route which:
 * - Runs server-side (can use Docker service names)
 * - Avoids Mixed Content issues (browser sees same-origin requests)
 * - No need to expose backend IP addresses to the client
 * 
 * @returns The API endpoint path
 */
const getApiEndpoint = (): string => {
  return '/api/coding-agent/query';
};

/**
 * Main chat hook that manages conversation state and API interactions.
 * 
 * This hook provides:
 * - Message list state
 * - Input value state
 * - Loading and streaming states
 * - File selection and management
 * - Auto-scroll to latest message
 * - Session ID management
 * 
 * @returns Object containing all chat-related state and functions
 */
export const useChat = (): UseChatReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [sessionId, setSessionId] = useState<string>('');

  // Initialize session ID on client side only
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setSessionId(getSessionId());
    }
  }, []);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!inputValue.trim() && selectedFiles.length === 0) || isLoading || isStreaming || !sessionId) return;

    const userInput = inputValue;
    const attachedFiles = [...selectedFiles];
    
    const userMessage: Message = {
      id: Date.now(),
      text: userInput,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString(),
      files: attachedFiles
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setSelectedFiles([]);
    setIsLoading(true);

    // Create AI message placeholder
    const aiMessage: Message = {
      id: Date.now() + 1,
      text: '',
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString(),
      isStreaming: true
    };

    setMessages(prev => [...prev, aiMessage]);
    setIsStreaming(true);

    try {
      // Always use the Next.js API proxy (avoids Mixed Content issues)
      const endpoint = getApiEndpoint();
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userInput,
          session_id: sessionId || getSessionId(), // Fallback if sessionId not ready
          max_steps: 10,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      // Extract answer from response
      let answer = data.answer || 'No response received';
      
      // Update AI message with response
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage?.sender === 'ai' && lastMessage.isStreaming) {
          lastMessage.text = answer;
          lastMessage.imageBase64 = data.image_base64 || undefined;
          lastMessage.imageMime = data.image_mime || undefined;
          lastMessage.isStreaming = false;
        }
        return newMessages;
      });
      
    } catch (error) {
      console.error('Error calling API:', error);
      
      // Show error message
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage?.sender === 'ai' && lastMessage.isStreaming) {
          lastMessage.text = `**Error:** ${error instanceof Error ? error.message : 'Failed to get response from server'}\n\nPlease check that the backend is running.`;
          lastMessage.isStreaming = false;
        }
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSelectedFiles([]);
    // Note: session_id persists in localStorage
    // It only changes when the page is reloaded
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return {
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
  };
};

