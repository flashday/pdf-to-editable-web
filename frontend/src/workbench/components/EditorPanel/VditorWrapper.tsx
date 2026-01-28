import React, { useEffect, useRef, useCallback } from 'react';
import Vditor from 'vditor';
import 'vditor/dist/index.css';
import styles from './VditorWrapper.module.css';

interface VditorWrapperProps {
  content: string;
  onChange: (content: string) => void;
  onCursorChange?: (position: number) => void;
  mode?: 'wysiwyg' | 'sv' | 'ir';
  placeholder?: string;
}

const VditorWrapper: React.FC<VditorWrapperProps> = ({
  content,
  onChange,
  onCursorChange,
  mode = 'wysiwyg',
  placeholder = '在此编辑 Markdown 内容...'
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const vditorRef = useRef<Vditor | null>(null);
  const isInitializedRef = useRef(false);
  const lastContentRef = useRef(content);

  // 初始化 Vditor
  useEffect(() => {
    if (!containerRef.current || isInitializedRef.current) return;

    isInitializedRef.current = true;

    vditorRef.current = new Vditor(containerRef.current, {
      height: '100%',
      mode: mode,
      placeholder: placeholder,
      cache: { enable: false },
      value: content,
      
      // 工具栏配置
      toolbar: [
        'headings',
        'bold',
        'italic',
        'strike',
        '|',
        'list',
        'ordered-list',
        'check',
        '|',
        'quote',
        'code',
        'inline-code',
        '|',
        {
          name: 'table',
          tipPosition: 's'
        },
        'link',
        '|',
        'undo',
        'redo',
        '|',
        'edit-mode',
        'fullscreen',
        'outline'
      ],

      // 表格配置
      tab: '    ',
      typewriterMode: false,

      // 内容变更回调
      input: (value: string) => {
        if (value !== lastContentRef.current) {
          lastContentRef.current = value;
          onChange(value);
        }
      },

      // 编辑器就绪回调
      after: () => {
        if (vditorRef.current && content) {
          vditorRef.current.setValue(content);
        }
      },

      // 光标位置变化回调
      select: (_value: string) => {
        if (onCursorChange && vditorRef.current) {
          const selection = window.getSelection();
          if (selection && selection.rangeCount > 0) {
            // 获取光标在文档中的位置
            const range = selection.getRangeAt(0);
            const preCaretRange = range.cloneRange();
            preCaretRange.selectNodeContents(containerRef.current!);
            preCaretRange.setEnd(range.startContainer, range.startOffset);
            const position = preCaretRange.toString().length;
            onCursorChange(position);
          }
        }
      },

      // 表格配置
      preview: {
        markdown: {
          toc: true,
          mark: true,
          footnotes: true,
          autoSpace: true
        },
        hljs: {
          enable: true,
          style: 'github'
        }
      },

      // HTML 渲染配置 - 支持 HTML 表格混合
      hint: {
        parse: true,
        delay: 200
      },

      // 允许 HTML 标签
      upload: {
        accept: 'image/*'
      },

      // 主题配置
      theme: 'classic',
      
      // 语言配置
      lang: 'zh_CN'
    });

    return () => {
      if (vditorRef.current) {
        vditorRef.current.destroy();
        vditorRef.current = null;
        isInitializedRef.current = false;
      }
    };
  }, []);

  // 外部内容更新时同步到编辑器
  useEffect(() => {
    if (vditorRef.current && content !== lastContentRef.current) {
      lastContentRef.current = content;
      vditorRef.current.setValue(content);
    }
  }, [content]);

  // 滚动到指定锚点
  const scrollToAnchor = useCallback((anchorId: string) => {
    if (!containerRef.current) return;
    
    const element = containerRef.current.querySelector(`#${anchorId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // 添加高亮效果
      element.classList.add(styles.highlight);
      setTimeout(() => {
        element.classList.remove(styles.highlight);
      }, 2000);
    }
  }, []);

  // 获取当前编辑器内容
  const getValue = useCallback(() => {
    return vditorRef.current?.getValue() || '';
  }, []);

  // 设置编辑器内容
  const setValue = useCallback((value: string) => {
    if (vditorRef.current) {
      lastContentRef.current = value;
      vditorRef.current.setValue(value);
    }
  }, []);

  // 暴露方法给父组件
  React.useImperativeHandle(
    React.useRef({ scrollToAnchor, getValue, setValue }),
    () => ({ scrollToAnchor, getValue, setValue })
  );

  return (
    <div className={styles.container}>
      <div ref={containerRef} className={styles.editor} />
    </div>
  );
};

export default VditorWrapper;
