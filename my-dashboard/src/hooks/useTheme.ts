/**
 * Theme Management Hook
 * 
 * This custom React hook manages the application theme (dark/light mode).
 * It provides:
 * - Theme state persistence in localStorage
 * - Automatic theme application to document root
 * - Hydration-safe theme initialization (prevents SSR mismatch)
 * - Theme toggle functionality
 * 
 * The theme is stored in localStorage and applied to the document's
 * data-theme attribute, which is used by CSS for theme switching.
 * 
 * Default theme: 'dark'
 */
'use client';

import { useState, useEffect } from 'react';
import { UseThemeReturn } from '@/types';

/**
 * Hook for managing application theme.
 * 
 * Handles theme persistence and prevents hydration mismatches by
 * only applying theme after component mounts on the client.
 * 
 * @returns Object with current theme and toggle function
 */
export const useTheme = (): UseThemeReturn => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [mounted, setMounted] = useState(false);

  // Evitar hydration mismatch
  useEffect(() => {
    setMounted(true);
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light';
    // Si no hay tema guardado, usar 'dark' por defecto
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Establecer 'dark' como predeterminado si no hay tema guardado
      setTheme('dark');
      localStorage.setItem('theme', 'dark');
    }
  }, []);

  useEffect(() => {
    if (mounted) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    }
  }, [theme, mounted]);

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'dark' ? 'light' : 'dark');
  };

  return { theme, toggleTheme };
};

