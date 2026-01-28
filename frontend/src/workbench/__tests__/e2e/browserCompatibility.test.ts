/**
 * 端到端集成测试 - 浏览器兼容性测试
 * 任务 19.5: 测试浏览器兼容性（Chrome/Edge/Firefox）
 * 
 * **Validates: Requirements 5.1, 5.2**
 * 
 * 注意：这些测试验证代码的浏览器兼容性，
 * 实际的跨浏览器测试需要在真实浏览器环境中运行。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { parseAnchors, getBlockIdAtPosition } from '../../utils/anchorParser';
import { api } from '../../services/api';

// Mock API
vi.mock('../../services/api', () => ({
  api: {
    getLayoutWithAnchors: vi.fn(),
    getMarkdownWithAnchors: vi.fn(),
    saveMarkdown: vi.fn(),
    getImageUrl: vi.fn((jobId: string) => `/temp/${jobId}_page1.png`),
  },
}));

describe('E2E: 浏览器兼容性测试', () => {
  const mockJobId = 'test-job-compat';

  beforeEach(() => {
    useWorkbenchStore.getState().reset();
    
    vi.mocked(api.getLayoutWithAnchors).mockResolvedValue({
      success: true,
      data: {
        blocks: [
          { id: 'block_001', type: 'text', bbox: { x: 0, y: 0, width: 100, height: 50 }, confidence: 0.9, pageNum: 1 },
        ],
        imageWidth: 612,
        imageHeight: 792,
      },
    });

    vi.mocked(api.getMarkdownWithAnchors).mockResolvedValue({
      success: true,
      data: {
        markdown: '<div id="block_001" data-coords="0,0,100,50" style="display:none;"></div>\n# Test',
        anchors: [{ blockId: 'block_001', position: 0 }],
      },
    });
    
    vi.mocked(api.saveMarkdown).mockResolvedValue({
      success: true,
      data: { savedAt: new Date().toISOString(), vectorUpdated: false },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('ES6+ 特性兼容性', () => {
    it('应该支持 async/await', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      expect(result.current.layoutBlocks).toHaveLength(1);
    });

    it('应该支持箭头函数', () => {
      const add = (a: number, b: number) => a + b;
      expect(add(1, 2)).toBe(3);
    });

    it('应该支持解构赋值', () => {
      const obj = { a: 1, b: 2 };
      const { a, b } = obj;
      expect(a).toBe(1);
      expect(b).toBe(2);
    });

    it('应该支持展开运算符', () => {
      const arr1 = [1, 2, 3];
      const arr2 = [...arr1, 4, 5];
      expect(arr2).toEqual([1, 2, 3, 4, 5]);
    });

    it('应该支持模板字符串', () => {
      const name = 'World';
      const greeting = `Hello, ${name}!`;
      expect(greeting).toBe('Hello, World!');
    });

    it('应该支持 Promise', async () => {
      const promise = new Promise<number>((resolve) => {
        setTimeout(() => resolve(42), 10);
      });
      const result = await promise;
      expect(result).toBe(42);
    });

    it('应该支持 Map 和 Set', () => {
      const map = new Map<string, number>();
      map.set('a', 1);
      expect(map.get('a')).toBe(1);

      const set = new Set<number>();
      set.add(1);
      set.add(2);
      expect(set.has(1)).toBe(true);
    });
  });

  describe('DOM API 兼容性', () => {
    it('应该支持 querySelector', () => {
      document.body.innerHTML = '<div id="test">Test</div>';
      const element = document.querySelector('#test');
      expect(element).not.toBeNull();
      expect(element?.textContent).toBe('Test');
    });

    it('应该支持 classList', () => {
      document.body.innerHTML = '<div id="test" class="foo">Test</div>';
      const element = document.querySelector('#test');
      expect(element?.classList.contains('foo')).toBe(true);
      element?.classList.add('bar');
      expect(element?.classList.contains('bar')).toBe(true);
    });

    it('应该支持 dataset', () => {
      document.body.innerHTML = '<div id="test" data-value="123">Test</div>';
      const element = document.querySelector('#test') as HTMLElement;
      expect(element?.dataset.value).toBe('123');
    });

    it('应该支持 addEventListener', () => {
      const handler = vi.fn();
      document.body.innerHTML = '<button id="btn">Click</button>';
      const button = document.querySelector('#btn');
      button?.addEventListener('click', handler);
      button?.dispatchEvent(new Event('click'));
      expect(handler).toHaveBeenCalled();
    });

    it('应该支持 scrollIntoView', () => {
      document.body.innerHTML = '<div id="test">Test</div>';
      const element = document.querySelector('#test');
      // scrollIntoView 在 jsdom 中是 mock 的
      expect(typeof element?.scrollIntoView).toBe('function');
    });
  });

  describe('CSS 特性兼容性', () => {
    it('应该支持 CSS 变量', () => {
      document.body.innerHTML = '<div id="test" style="--custom-color: red;">Test</div>';
      const element = document.querySelector('#test') as HTMLElement;
      expect(element.style.getPropertyValue('--custom-color')).toBe('red');
    });

    it('应该支持 flexbox 属性', () => {
      document.body.innerHTML = '<div id="test" style="display: flex;">Test</div>';
      const element = document.querySelector('#test') as HTMLElement;
      expect(element.style.display).toBe('flex');
    });

    it('应该支持 grid 属性', () => {
      document.body.innerHTML = '<div id="test" style="display: grid;">Test</div>';
      const element = document.querySelector('#test') as HTMLElement;
      expect(element.style.display).toBe('grid');
    });
  });

  describe('Fetch API 兼容性', () => {
    it('应该支持 fetch', () => {
      expect(typeof fetch).toBe('function');
    });

    it('应该支持 Response 对象', () => {
      const response = new Response('test');
      expect(response).toBeInstanceOf(Response);
    });

    it('应该支持 Headers 对象', () => {
      const headers = new Headers();
      headers.set('Content-Type', 'application/json');
      expect(headers.get('Content-Type')).toBe('application/json');
    });
  });

  describe('Storage API 兼容性', () => {
    it('应该支持 localStorage', () => {
      localStorage.setItem('test', 'value');
      expect(localStorage.getItem('test')).toBe('value');
      localStorage.removeItem('test');
    });

    it('应该支持 sessionStorage', () => {
      sessionStorage.setItem('test', 'value');
      expect(sessionStorage.getItem('test')).toBe('value');
      sessionStorage.removeItem('test');
    });
  });

  describe('正则表达式兼容性', () => {
    it('应该正确解析锚点正则', () => {
      const markdown = '<div id="block_001" data-coords="100,200,300,400" style="display:none;"></div>';
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(1);
      // blockId 不包含 block_ 前缀
      expect(anchors[0].blockId).toBe('001');
      expect(anchors[0].coords).toEqual({ x: 100, y: 200, width: 300, height: 400 });
    });

    it('应该处理特殊字符', () => {
      const markdown = '<div id="block_abc123" data-coords="0,0,100,100" style="display:none;"></div>';
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(1);
      // blockId 不包含 block_ 前缀
      expect(anchors[0].blockId).toBe('abc123');
    });
  });

  describe('键盘事件兼容性', () => {
    it('应该支持 KeyboardEvent', () => {
      const event = new KeyboardEvent('keydown', {
        key: 's',
        ctrlKey: true,
      });
      
      expect(event.key).toBe('s');
      expect(event.ctrlKey).toBe(true);
    });

    it('应该支持 metaKey (Mac Cmd)', () => {
      const event = new KeyboardEvent('keydown', {
        key: 's',
        metaKey: true,
      });
      
      expect(event.metaKey).toBe(true);
    });
  });

  describe('URL API 兼容性', () => {
    it('应该支持 URL 对象', () => {
      const url = new URL('https://example.com/path?query=value');
      expect(url.pathname).toBe('/path');
      expect(url.searchParams.get('query')).toBe('value');
    });

    it('应该支持 URLSearchParams', () => {
      const params = new URLSearchParams('?jobId=123&mode=edit');
      expect(params.get('jobId')).toBe('123');
      expect(params.get('mode')).toBe('edit');
    });
  });

  describe('JSON 兼容性', () => {
    it('应该支持 JSON.stringify', () => {
      const obj = { a: 1, b: 'test' };
      const json = JSON.stringify(obj);
      expect(json).toBe('{"a":1,"b":"test"}');
    });

    it('应该支持 JSON.parse', () => {
      const json = '{"a":1,"b":"test"}';
      const obj = JSON.parse(json);
      expect(obj.a).toBe(1);
      expect(obj.b).toBe('test');
    });
  });

  describe('Date API 兼容性', () => {
    it('应该支持 Date.now()', () => {
      const now = Date.now();
      expect(typeof now).toBe('number');
    });

    it('应该支持 ISO 日期字符串', () => {
      const date = new Date('2026-01-28T10:30:00Z');
      expect(date.toISOString()).toBe('2026-01-28T10:30:00.000Z');
    });
  });

  describe('beforeunload 事件兼容性', () => {
    it('应该支持 beforeunload 事件', () => {
      const handler = vi.fn();
      window.addEventListener('beforeunload', handler);
      
      // 触发事件
      const event = new Event('beforeunload');
      window.dispatchEvent(event);
      
      expect(handler).toHaveBeenCalled();
      
      window.removeEventListener('beforeunload', handler);
    });
  });
});
