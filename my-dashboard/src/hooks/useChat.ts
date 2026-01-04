'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, UseChatReturn } from '@/types';

// Generate or retrieve session ID from localStorage
// IMPORTANT: Generate a NEW session_id on each page load
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

// Always use the Next.js API proxy
// The proxy runs server-side and can use Docker service names (api:8000)
// The browser only sees same-origin requests (no IP needed)
const getApiEndpoint = (): string => {
  return '/api/coding-agent/query';
};

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

