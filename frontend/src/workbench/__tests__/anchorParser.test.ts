import { describe, it, expect } from 'vitest';
import {
  parseAnchors,
  getBlockIdAtPosition,
  getAnchorByBlockId,
  getPositionByBlockId,
  generateAnchorHtml,
  generateAnchorComment,
  removeAnchors,
  isValidAnchor
} from '../utils/anchorParser';

describe('anchorParser', () => {
  describe('parseAnchors', () => {
    it('应该正确解析 div 格式锚点', () => {
      const markdown = `
<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>
# 标题

<div id="block_002" data-coords="100,100,400,200" style="display:none;"></div>
这是正文内容
`;
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(2);
      expect(anchors[0].blockId).toBe('001');
      expect(anchors[0].coords).toEqual({ x: 100, y: 50, width: 400, height: 30 });
      expect(anchors[1].blockId).toBe('002');
      expect(anchors[1].coords).toEqual({ x: 100, y: 100, width: 400, height: 200 });
    });

    it('应该正确解析注释格式锚点', () => {
      const markdown = `
<!-- block:001 coords:100,50,400,30 -->
# 标题

<!-- block:002 coords:100,100,400,200 -->
这是正文内容
`;
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(2);
      expect(anchors[0].blockId).toBe('001');
      expect(anchors[1].blockId).toBe('002');
    });

    it('应该按位置排序锚点', () => {
      const markdown = `
<div id="block_003" data-coords="0,200,100,50" style="display:none;"></div>
第三段

<div id="block_001" data-coords="0,0,100,50" style="display:none;"></div>
第一段

<div id="block_002" data-coords="0,100,100,50" style="display:none;"></div>
第二段
`;
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(3);
      // 按位置排序，不是按 ID 排序
      expect(anchors[0].blockId).toBe('003');
      expect(anchors[1].blockId).toBe('001');
      expect(anchors[2].blockId).toBe('002');
    });

    it('应该处理空内容', () => {
      const anchors = parseAnchors('');
      expect(anchors).toHaveLength(0);
    });

    it('应该处理没有锚点的内容', () => {
      const markdown = '# 标题\n\n这是正文内容';
      const anchors = parseAnchors(markdown);
      expect(anchors).toHaveLength(0);
    });
  });

  describe('getBlockIdAtPosition', () => {
    const anchors = [
      { blockId: '001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: '002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 },
      { blockId: '003', coords: { x: 0, y: 200, width: 100, height: 50 }, position: 200 }
    ];

    it('应该返回位置之前最近的锚点 ID', () => {
      expect(getBlockIdAtPosition(anchors, 50)).toBe('001');
      expect(getBlockIdAtPosition(anchors, 150)).toBe('002');
      expect(getBlockIdAtPosition(anchors, 250)).toBe('003');
    });

    it('应该处理位置正好在锚点上的情况', () => {
      expect(getBlockIdAtPosition(anchors, 0)).toBe('001');
      expect(getBlockIdAtPosition(anchors, 100)).toBe('002');
      expect(getBlockIdAtPosition(anchors, 200)).toBe('003');
    });

    it('应该处理空锚点数组', () => {
      expect(getBlockIdAtPosition([], 50)).toBeNull();
    });

    it('应该处理位置在所有锚点之后的情况', () => {
      expect(getBlockIdAtPosition(anchors, 1000)).toBe('003');
    });
  });

  describe('getAnchorByBlockId', () => {
    const anchors = [
      { blockId: '001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: '002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 }
    ];

    it('应该返回匹配的锚点', () => {
      const anchor = getAnchorByBlockId(anchors, '001');
      expect(anchor).not.toBeNull();
      expect(anchor?.blockId).toBe('001');
    });

    it('应该返回 null 如果没有匹配', () => {
      const anchor = getAnchorByBlockId(anchors, '999');
      expect(anchor).toBeNull();
    });
  });

  describe('getPositionByBlockId', () => {
    const anchors = [
      { blockId: '001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: '002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 }
    ];

    it('应该返回锚点位置', () => {
      expect(getPositionByBlockId(anchors, '001')).toBe(0);
      expect(getPositionByBlockId(anchors, '002')).toBe(100);
    });

    it('应该返回 -1 如果没有匹配', () => {
      expect(getPositionByBlockId(anchors, '999')).toBe(-1);
    });
  });

  describe('generateAnchorHtml', () => {
    it('应该生成正确的锚点 HTML', () => {
      const html = generateAnchorHtml('001', { x: 100, y: 50, width: 400, height: 30 });
      expect(html).toBe('<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>');
    });
  });

  describe('generateAnchorComment', () => {
    it('应该生成正确的锚点注释', () => {
      const comment = generateAnchorComment('001', { x: 100, y: 50, width: 400, height: 30 });
      expect(comment).toBe('<!-- block:001 coords:100,50,400,30 -->');
    });
  });

  describe('removeAnchors', () => {
    it('应该移除 div 格式锚点', () => {
      const markdown = `<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>
# 标题

内容`;
      const result = removeAnchors(markdown);
      expect(result).not.toContain('block_001');
      expect(result).toContain('# 标题');
      expect(result).toContain('内容');
    });

    it('应该移除注释格式锚点', () => {
      const markdown = `<!-- block:001 coords:100,50,400,30 -->
# 标题

内容`;
      const result = removeAnchors(markdown);
      expect(result).not.toContain('block:001');
      expect(result).toContain('# 标题');
    });
  });

  describe('isValidAnchor', () => {
    it('应该验证有效的 div 格式锚点', () => {
      const anchor = '<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>';
      expect(isValidAnchor(anchor)).toBe(true);
    });

    it('应该验证有效的注释格式锚点', () => {
      const anchor = '<!-- block:001 coords:100,50,400,30 -->';
      expect(isValidAnchor(anchor)).toBe(true);
    });

    it('应该拒绝无效的锚点', () => {
      expect(isValidAnchor('<div>invalid</div>')).toBe(false);
      expect(isValidAnchor('<!-- invalid -->')).toBe(false);
      expect(isValidAnchor('plain text')).toBe(false);
    });
  });
});
