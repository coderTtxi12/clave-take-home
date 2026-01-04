/**
 * Typing Indicator Component
 * 
 * This component displays a visual indicator that the AI is processing
 * a request. It shows:
 * - "Planning" text
 * - Animated typing dots (three dots that pulse)
 * 
 * The component is displayed when isLoading is true, providing visual
 * feedback that the system is working on the user's query.
 */
'use client';

import React from 'react';
import styles from './TypingIndicator.module.css';

/**
 * Typing indicator component shown while AI is processing.
 * 
 * Displays "Planning" text with animated dots to indicate
 * that the system is working on the request.
 */
export const TypingIndicator: React.FC = () => {
  return (
    <div className={`${styles.message} ${styles.ai}`}>
      <div className={styles.messageContent}>
        <div className={styles.planningText}>Planning</div>
        <div className={styles.typingIndicator}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
};

