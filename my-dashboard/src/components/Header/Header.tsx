/**
 * Header Component
 * 
 * The application header displays:
 * - Application title (clickable to clear chat)
 * - Theme toggle button (dark/light mode)
 * - Clear chat button
 * 
 * The header is fixed at the top of the page and provides
 * quick access to common actions.
 */
'use client';

import React from 'react';
import { HeaderProps } from '@/types';
import styles from './Header.module.css';

/**
 * Header component for the dashboard.
 * 
 * @param theme - Current theme ('dark' or 'light')
 * @param toggleTheme - Function to toggle between themes
 * @param onClearChat - Function to clear the chat history
 */
export const Header: React.FC<HeaderProps> = ({ theme, toggleTheme, onClearChat }) => {
  const handleTitleClick = () => {
    onClearChat();
  };

  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <h1 className={styles.headerTitle} onClick={handleTitleClick}>
          Data Analyst Agent
        </h1>
      </div>
      <div className={styles.headerRight}>
        <button 
          className={styles.themeToggle} 
          onClick={toggleTheme} 
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          <span className="material-icons">
            {theme === 'dark' ? 'light_mode' : 'dark_mode'}
          </span>
        </button>
        <button 
          className={styles.headerButton} 
          onClick={onClearChat} 
          title="Clear chat"
        >
          <span className="material-icons">refresh</span>
        </button>
      </div>
    </header>
  );
};

