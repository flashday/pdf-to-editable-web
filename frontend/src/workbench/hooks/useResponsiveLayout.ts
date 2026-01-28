/**
 * 响应式布局 Hook
 * 任务 21.2: 优化响应式布局
 */
import { useState, useEffect, useCallback } from 'react';

type LayoutMode = 'desktop' | 'tablet' | 'mobile';
type MobileViewMode = 'tab' | 'split';
type ActivePanel = 'pdf' | 'editor';

interface ResponsiveLayoutState {
  layoutMode: LayoutMode;
  mobileViewMode: MobileViewMode;
  activePanel: ActivePanel;
  isTouchDevice: boolean;
  windowWidth: number;
  windowHeight: number;
}

interface ResponsiveLayoutActions {
  setMobileViewMode: (mode: MobileViewMode) => void;
  setActivePanel: (panel: ActivePanel) => void;
  togglePanel: () => void;
}

const BREAKPOINTS = {
  mobile: 768,
  tablet: 1200,
};

export function useResponsiveLayout(): ResponsiveLayoutState & ResponsiveLayoutActions {
  const [state, setState] = useState<ResponsiveLayoutState>(() => ({
    layoutMode: getLayoutMode(window.innerWidth),
    mobileViewMode: 'tab',
    activePanel: 'pdf',
    isTouchDevice: isTouchDevice(),
    windowWidth: window.innerWidth,
    windowHeight: window.innerHeight,
  }));

  // 监听窗口大小变化
  useEffect(() => {
    let timeoutId: number;

    const handleResize = () => {
      clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        setState((prev) => ({
          ...prev,
          layoutMode: getLayoutMode(window.innerWidth),
          windowWidth: window.innerWidth,
          windowHeight: window.innerHeight,
        }));
      }, 100);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timeoutId);
    };
  }, []);

  // 监听触摸设备变化
  useEffect(() => {
    const handleTouchStart = () => {
      setState((prev) => ({ ...prev, isTouchDevice: true }));
    };

    window.addEventListener('touchstart', handleTouchStart, { once: true });
    return () => window.removeEventListener('touchstart', handleTouchStart);
  }, []);

  const setMobileViewMode = useCallback((mode: MobileViewMode) => {
    setState((prev) => ({ ...prev, mobileViewMode: mode }));
  }, []);

  const setActivePanel = useCallback((panel: ActivePanel) => {
    setState((prev) => ({ ...prev, activePanel: panel }));
  }, []);

  const togglePanel = useCallback(() => {
    setState((prev) => ({
      ...prev,
      activePanel: prev.activePanel === 'pdf' ? 'editor' : 'pdf',
    }));
  }, []);

  return {
    ...state,
    setMobileViewMode,
    setActivePanel,
    togglePanel,
  };
}

function getLayoutMode(width: number): LayoutMode {
  if (width < BREAKPOINTS.mobile) return 'mobile';
  if (width < BREAKPOINTS.tablet) return 'tablet';
  return 'desktop';
}

function isTouchDevice(): boolean {
  return (
    'ontouchstart' in window ||
    navigator.maxTouchPoints > 0 ||
    // @ts-ignore
    navigator.msMaxTouchPoints > 0
  );
}

export type { LayoutMode, MobileViewMode, ActivePanel, ResponsiveLayoutState };
