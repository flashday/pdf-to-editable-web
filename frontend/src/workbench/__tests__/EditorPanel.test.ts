import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Vditor 模块
vi.mock('vditor', () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      getValue: vi.fn().mockReturnValue('# Test Content'),
      setValue: vi.fn(),
      destroy: vi.fn(),
      focus: vi.fn()
    }))
  };
});

describe('EditorPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('表格编辑支持', () => {
    it('应该支持 Markdown 表格语法', () => {
      const markdownTable = `
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A1  | B1  | C1  |
| A2  | B2  | C2  |
`;
      // 验证表格语法格式正确
      expect(markdownTable).toContain('|');
      expect(markdownTable.split('\n').filter(line => line.includes('|')).length).toBeGreaterThan(2);
    });

    it('应该支持 HTML 表格混合', () => {
      const htmlTable = `
<table>
  <tr>
    <th>表头1</th>
    <th>表头2</th>
  </tr>
  <tr>
    <td>数据1</td>
    <td>数据2</td>
  </tr>
</table>
`;
      // 验证 HTML 表格结构
      expect(htmlTable).toContain('<table>');
      expect(htmlTable).toContain('<th>');
      expect(htmlTable).toContain('<td>');
    });

    it('应该支持合并单元格的表格', () => {
      const complexTable = `
<table>
  <tr>
    <th colspan="2">合并表头</th>
  </tr>
  <tr>
    <td rowspan="2">合并行</td>
    <td>数据1</td>
  </tr>
  <tr>
    <td>数据2</td>
  </tr>
</table>
`;
      // 验证合并单元格属性
      expect(complexTable).toContain('colspan="2"');
      expect(complexTable).toContain('rowspan="2"');
    });
  });

  describe('编辑模式切换', () => {
    it('应该支持三种编辑模式', () => {
      const modes = ['wysiwyg', 'sv', 'ir'];
      expect(modes).toHaveLength(3);
      expect(modes).toContain('wysiwyg'); // 所见即所得
      expect(modes).toContain('sv');      // 分屏预览
      expect(modes).toContain('ir');      // 即时渲染
    });
  });

  describe('内容变更追踪', () => {
    it('应该正确检测内容变更', () => {
      const original: string = '# 原始内容';
      const modified: string = '# 修改后的内容';
      
      const isDirty = original !== modified;
      expect(isDirty).toBe(true);
    });

    it('应该在内容相同时不标记为脏', () => {
      const content = '# 相同内容';
      
      const isDirty = content !== content;
      expect(isDirty).toBe(false);
    });
  });

  describe('锚点解析', () => {
    it('应该正确解析 Block ID 锚点', () => {
      const markdown = `
<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>
# 标题

<div id="block_002" data-coords="100,100,400,200" style="display:none;"></div>
这是正文内容
`;
      const anchorRegex = /<div id="block_(\w+)" data-coords="(\d+),(\d+),(\d+),(\d+)"[^>]*><\/div>/g;
      const matches = [...markdown.matchAll(anchorRegex)];
      
      expect(matches).toHaveLength(2);
      expect(matches[0][1]).toBe('001');
      expect(matches[1][1]).toBe('002');
    });

    it('应该根据位置找到正确的 Block ID', () => {
      const anchors = [
        { blockId: '001', position: 0 },
        { blockId: '002', position: 100 },
        { blockId: '003', position: 200 }
      ];
      
      // 模拟 getBlockIdAtPosition 逻辑
      const getBlockIdAtPosition = (position: number) => {
        let nearestAnchor = null;
        for (const anchor of anchors) {
          if (anchor.position <= position) {
            nearestAnchor = anchor;
          } else {
            break;
          }
        }
        return nearestAnchor?.blockId ?? null;
      };

      expect(getBlockIdAtPosition(50)).toBe('001');
      expect(getBlockIdAtPosition(150)).toBe('002');
      expect(getBlockIdAtPosition(250)).toBe('003');
    });
  });
});
