/**
 * 键盘快捷键提示组件
 * 任务 21.3: 添加键盘快捷键提示
 */
import React, { useState, useEffect, useCallback } from 'react';
import styles from './KeyboardShortcuts.module.css';

interface Shortcut {
  keys: string[];
  description: string;
  category: 'general' | 'editor' | 'navigation';
}

const SHORTCUTS: Shortcut[] = [
  // 通用
  { keys: ['Ctrl', 'S'], description: '保存文档', category: 'general' },
  { keys: ['Ctrl', 'Z'], description: '撤销', category: 'general' },
  { keys: ['Ctrl', 'Shift', 'Z'], description: '重做', category: 'general' },
  { keys: ['Ctrl', '/'], description: '显示快捷键帮助', category: 'general' },
  { keys: ['Esc'], description: '关闭弹窗/取消操作', category: 'general' },
  
  // 编辑器
  { keys: ['Ctrl', 'B'], description: '加粗', category: 'editor' },
  { keys: ['Ctrl', 'I'], description: '斜体', category: 'editor' },
  { keys: ['Ctrl', 'K'], description: '插入链接', category: 'editor' },
  { keys: ['Ctrl', 'Shift', 'C'], description: '插入代码块', category: 'editor' },
  
  // 导航
  { keys: ['Ctrl', '↑'], description: '上一个 Block', category: 'navigation' },
  { keys: ['Ctrl', '↓'], description: '下一个 Block', category: 'navigation' },
  { keys: ['Ctrl', '+'], description: '放大', category: 'navigation' },
  { keys: ['Ctrl', '-'], description: '缩小', category: 'navigation' },
  { keys: ['Ctrl', '0'], description: '重置缩放', category: 'navigation' },
];

interface KeyboardShortcutsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KeyboardShortcutsDialog: React.FC<KeyboardShortcutsProps> = ({
  isOpen,
  onClose,
}) => {
  // 按 Esc 关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const categories = {
    general: '通用',
    editor: '编辑器',
    navigation: '导航',
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>键盘快捷键</h2>
          <button className={styles.closeButton} onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>
        <div className={styles.content}>
          {(Object.keys(categories) as Array<keyof typeof categories>).map((category) => (
            <div key={category} className={styles.category}>
              <h3>{categories[category]}</h3>
              <ul>
                {SHORTCUTS.filter((s) => s.category === category).map((shortcut, index) => (
                  <li key={index}>
                    <span className={styles.keys}>
                      {shortcut.keys.map((key, i) => (
                        <React.Fragment key={i}>
                          <kbd>{key}</kbd>
                          {i < shortcut.keys.length - 1 && <span>+</span>}
                        </React.Fragment>
                      ))}
                    </span>
                    <span className={styles.description}>{shortcut.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className={styles.footer}>
          <span>按 <kbd>Ctrl</kbd> + <kbd>/</kbd> 随时查看快捷键</span>
        </div>
      </div>
    </div>
  );
};

// 快捷键提示按钮
export const KeyboardShortcutsButton: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  // 监听 Ctrl+/ 快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <button
        className={styles.helpButton}
        onClick={() => setIsOpen(true)}
        title="键盘快捷键 (Ctrl+/)"
        aria-label="显示键盘快捷键"
      >
        <span className={styles.helpIcon}>⌨</span>
      </button>
      <KeyboardShortcutsDialog isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
};

// Hook: 注册自定义快捷键
export function useKeyboardShortcut(
  keys: string[],
  callback: () => void,
  deps: React.DependencyList = []
): void {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const pressedKeys: string[] = [];
      if (e.ctrlKey) pressedKeys.push('Ctrl');
      if (e.shiftKey) pressedKeys.push('Shift');
      if (e.altKey) pressedKeys.push('Alt');
      if (e.key && !['Control', 'Shift', 'Alt'].includes(e.key)) {
        pressedKeys.push(e.key.toUpperCase());
      }

      const normalizedKeys = keys.map((k) => k.toUpperCase());
      const match =
        pressedKeys.length === normalizedKeys.length &&
        pressedKeys.every((k) => normalizedKeys.includes(k));

      if (match) {
        e.preventDefault();
        callback();
      }
    },
    [keys, callback, ...deps]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

export default KeyboardShortcutsDialog;
