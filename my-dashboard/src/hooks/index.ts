/**
 * Hooks Barrel Export
 * 
 * This module provides a centralized export point for all custom React hooks
 * used in the dashboard. This allows for cleaner imports using the @/hooks alias.
 * 
 * Exported hooks:
 * - useChat: Manages chat state, API communication, and file handling
 * - useTheme: Manages application theme (dark/light mode) with persistence
 */
export { useChat } from './useChat';
export { useTheme } from './useTheme';

