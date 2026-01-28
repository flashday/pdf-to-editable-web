import { LayoutResponse, MarkdownResponse, SaveResponse } from '../stores/types';

const API_BASE = '/api/convert';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export const api = {
  /**
   * 获取带锚点的布局数据
   */
  async getLayoutWithAnchors(jobId: string): Promise<LayoutResponse> {
    try {
      return await fetchJson<LayoutResponse>(
        `${API_BASE}/${jobId}/layout-with-anchors`
      );
    } catch (error) {
      // 如果新 API 不存在，回退到现有 API
      console.warn('layout-with-anchors API not available, using fallback');
      return this.getLayoutFallback(jobId);
    }
  },

  /**
   * 回退方案：从现有 ppstructure.json 获取布局数据
   */
  async getLayoutFallback(jobId: string): Promise<LayoutResponse> {
    try {
      const response = await fetch(`/temp/${jobId}_ppstructure.json`);
      if (!response.ok) {
        return {
          success: false,
          data: { blocks: [], imageWidth: 0, imageHeight: 0 }
        };
      }
      
      const ppstructure = await response.json();
      const blocks = this.parsePPStructure(ppstructure);
      
      return {
        success: true,
        data: {
          blocks,
          imageWidth: ppstructure.imageWidth || 612,
          imageHeight: ppstructure.imageHeight || 792
        }
      };
    } catch {
      return {
        success: true,
        data: { blocks: [], imageWidth: 612, imageHeight: 792 }
      };
    }
  },

  /**
   * 解析 PP-Structure 输出为 LayoutBlock 格式
   */
  parsePPStructure(data: any[]): any[] {
    if (!Array.isArray(data)) return [];
    
    return data.map((item, index) => ({
      id: `block_${String(index + 1).padStart(3, '0')}`,
      type: this.mapBlockType(item.type),
      bbox: {
        x: item.bbox?.[0] || 0,
        y: item.bbox?.[1] || 0,
        width: (item.bbox?.[2] || 0) - (item.bbox?.[0] || 0),
        height: (item.bbox?.[3] || 0) - (item.bbox?.[1] || 0)
      },
      confidence: item.score || 0.9,
      pageNum: 1,
      text: item.res?.map((r: any) => r.text).join(' ') || ''
    }));
  },

  /**
   * 映射 PP-Structure 类型到标准类型
   */
  mapBlockType(type: string): string {
    const typeMap: Record<string, string> = {
      'text': 'text',
      'title': 'title',
      'table': 'table',
      'figure': 'figure',
      'list': 'list',
      'reference': 'reference',
      'header': 'title',
      'footer': 'text'
    };
    return typeMap[type?.toLowerCase()] || 'text';
  },

  /**
   * 获取带锚点的 Markdown 内容
   */
  async getMarkdownWithAnchors(jobId: string): Promise<MarkdownResponse> {
    try {
      return await fetchJson<MarkdownResponse>(
        `${API_BASE}/${jobId}/markdown-with-anchors`
      );
    } catch (error) {
      // 如果新 API 不存在，回退到现有 API
      console.warn('markdown-with-anchors API not available, using fallback');
      return this.getMarkdownFallback(jobId);
    }
  },

  /**
   * 回退方案：从现有 raw_ocr.md 获取 Markdown
   */
  async getMarkdownFallback(jobId: string): Promise<MarkdownResponse> {
    try {
      // 尝试获取 MD 文件
      const response = await fetch(`/temp/${jobId}_raw_ocr.md`);
      if (response.ok) {
        const markdown = await response.text();
        return {
          success: true,
          data: {
            markdown,
            anchors: []
          }
        };
      }

      // 如果没有 MD，尝试获取 HTML
      const htmlResponse = await fetch(`/temp/${jobId}_raw_ocr.html`);
      if (htmlResponse.ok) {
        const html = await htmlResponse.text();
        return {
          success: true,
          data: {
            markdown: `<!-- HTML Content -->\n${html}`,
            anchors: []
          }
        };
      }

      return {
        success: true,
        data: {
          markdown: '# 无内容\n\n暂无 OCR 识别结果',
          anchors: []
        }
      };
    } catch {
      return {
        success: true,
        data: {
          markdown: '# 加载失败\n\n无法加载 Markdown 内容',
          anchors: []
        }
      };
    }
  },

  /**
   * 保存修正后的 Markdown
   */
  async saveMarkdown(jobId: string, markdown: string, updateVector = false): Promise<SaveResponse> {
    try {
      return await fetchJson<SaveResponse>(
        `${API_BASE}/${jobId}/save-markdown`,
        {
          method: 'POST',
          body: JSON.stringify({ markdown, updateVector })
        }
      );
    } catch (error) {
      // 如果新 API 不存在，使用本地存储作为临时方案
      console.warn('save-markdown API not available, using localStorage fallback');
      localStorage.setItem(`workbench_${jobId}_markdown`, markdown);
      return {
        success: true,
        data: {
          savedAt: new Date().toISOString(),
          vectorUpdated: false
        }
      };
    }
  },

  /**
   * 获取 PDF 页面图像 URL
   */
  getImageUrl(jobId: string, pageNum = 1): string {
    // 添加时间戳避免浏览器追踪保护和缓存问题
    const timestamp = Date.now();
    return `/temp/${jobId}_page${pageNum}.png?t=${timestamp}`;
  }
};
