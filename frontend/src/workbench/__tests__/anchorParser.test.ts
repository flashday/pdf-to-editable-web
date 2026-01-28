import { describe, it, expect } from 'vitest';
import {
  parseAnchors,
  getBlockIdAtPosition,
  getAnchorByBlockId,
  getPositionByBlockId,
  generateAnchor,
  generateAnchorComment,
  removeAnchors,
  isValidAnchor
} from '../utils/anchorParser';

describe('anchorParser', () => {
  describe('parseAnchors', () => {
    it('应该正确解析新格式锚点 (@block: 前缀)', () => {
      const markdown = `
<!-- @block:block_001 100,50,400,30 -->
# 标题

<!-- @block:block_002 100,100,400,200 -->
这是正文内容
`;
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(2);
      expect(anchors[0].blockId).toBe('block_001');
      expect(anchors[0].coords).toEqual({ x: 100, y: 50, width: 400, height: 30 });
      expect(anchors[1].blockId).toBe('block_002');
      expect(anchors[1].coords).toEqual({ x: 100, y: 100, width: 400, height: 200 });
    });

    it('应该按位置排序锚点', () => {
      const markdown = `
<!-- @block:block_003 0,200,100,50 -->
第三段

<!-- @block:block_001 0,0,100,50 -->
第一段

<!-- @block:block_002 0,100,100,50 -->
第二段
`;
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(3);
      // 按位置排序，不是按 ID 排序
      expect(anchors[0].blockId).toBe('block_003');
      expect(anchors[1].blockId).toBe('block_001');
      expect(anchors[2].blockId).toBe('block_002');
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

    it('应该忽略旧的 div 格式锚点', () => {
      const markdown = `
<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>
# 标题
`;
      const anchors = parseAnchors(markdown);
      expect(anchors).toHaveLength(0);
    });

    it('应该忽略旧的无前缀注释格式锚点', () => {
      const markdown = `
<!-- block:001 coords:100,50,400,30 -->
# 标题
`;
      const anchors = parseAnchors(markdown);
      expect(anchors).toHaveLength(0);
    });

    it('应该处理带有额外空格的锚点', () => {
      const markdown = `<!--  @block:block_001  100,50,400,30  -->`;
      const anchors = parseAnchors(markdown);
      
      expect(anchors).toHaveLength(1);
      expect(anchors[0].blockId).toBe('block_001');
    });
  });

  describe('getBlockIdAtPosition', () => {
    const anchors = [
      { blockId: 'block_001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: 'block_002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 },
      { blockId: 'block_003', coords: { x: 0, y: 200, width: 100, height: 50 }, position: 200 }
    ];

    it('应该返回位置之前最近的锚点 ID', () => {
      expect(getBlockIdAtPosition(anchors, 50)).toBe('block_001');
      expect(getBlockIdAtPosition(anchors, 150)).toBe('block_002');
      expect(getBlockIdAtPosition(anchors, 250)).toBe('block_003');
    });

    it('应该处理位置正好在锚点上的情况', () => {
      expect(getBlockIdAtPosition(anchors, 0)).toBe('block_001');
      expect(getBlockIdAtPosition(anchors, 100)).toBe('block_002');
      expect(getBlockIdAtPosition(anchors, 200)).toBe('block_003');
    });

    it('应该处理空锚点数组', () => {
      expect(getBlockIdAtPosition([], 50)).toBeNull();
    });

    it('应该处理位置在所有锚点之后的情况', () => {
      expect(getBlockIdAtPosition(anchors, 1000)).toBe('block_003');
    });
  });

  describe('getAnchorByBlockId', () => {
    const anchors = [
      { blockId: 'block_001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: 'block_002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 }
    ];

    it('应该返回匹配的锚点', () => {
      const anchor = getAnchorByBlockId(anchors, 'block_001');
      expect(anchor).not.toBeNull();
      expect(anchor?.blockId).toBe('block_001');
    });

    it('应该返回 null 如果没有匹配', () => {
      const anchor = getAnchorByBlockId(anchors, 'block_999');
      expect(anchor).toBeNull();
    });
  });

  describe('getPositionByBlockId', () => {
    const anchors = [
      { blockId: 'block_001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: 'block_002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 }
    ];

    it('应该返回锚点位置', () => {
      expect(getPositionByBlockId(anchors, 'block_001')).toBe(0);
      expect(getPositionByBlockId(anchors, 'block_002')).toBe(100);
    });

    it('应该返回 -1 如果没有匹配', () => {
      expect(getPositionByBlockId(anchors, 'block_999')).toBe(-1);
    });
  });

  describe('generateAnchor', () => {
    it('应该生成正确的新格式锚点', () => {
      const anchor = generateAnchor('block_001', { x: 100, y: 50, width: 400, height: 30 });
      expect(anchor).toBe('<!-- @block:block_001 100,50,400,30 -->');
    });

    it('应该处理不同的 Block ID 格式', () => {
      const anchor = generateAnchor('my-custom-id', { x: 0, y: 0, width: 100, height: 100 });
      expect(anchor).toBe('<!-- @block:my-custom-id 0,0,100,100 -->');
    });
  });

  describe('generateAnchorComment', () => {
    it('应该生成与 generateAnchor 相同的格式', () => {
      const comment = generateAnchorComment('block_001', { x: 100, y: 50, width: 400, height: 30 });
      const anchor = generateAnchor('block_001', { x: 100, y: 50, width: 400, height: 30 });
      expect(comment).toBe(anchor);
    });
  });

  describe('removeAnchors', () => {
    it('应该移除新格式锚点', () => {
      const markdown = `<!-- @block:block_001 100,50,400,30 -->
# 标题

内容`;
      const result = removeAnchors(markdown);
      expect(result).not.toContain('@block:');
      expect(result).toContain('# 标题');
      expect(result).toContain('内容');
    });

    it('应该清理多余的空行', () => {
      const markdown = `<!-- @block:block_001 100,50,400,30 -->


# 标题



内容`;
      const result = removeAnchors(markdown);
      // 应该最多保留两个连续换行
      expect(result).not.toMatch(/\n{3,}/);
    });
  });

  describe('isValidAnchor', () => {
    it('应该验证有效的新格式锚点', () => {
      const anchor = '<!-- @block:block_001 100,50,400,30 -->';
      expect(isValidAnchor(anchor)).toBe(true);
    });

    it('应该验证带有额外空格的锚点', () => {
      const anchor = '<!--  @block:block_001  100,50,400,30  -->';
      expect(isValidAnchor(anchor)).toBe(true);
    });

    it('应该拒绝旧的 div 格式锚点', () => {
      const anchor = '<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>';
      expect(isValidAnchor(anchor)).toBe(false);
    });

    it('应该拒绝旧的无前缀注释格式锚点', () => {
      const anchor = '<!-- block:001 coords:100,50,400,30 -->';
      expect(isValidAnchor(anchor)).toBe(false);
    });

    it('应该拒绝无效的锚点', () => {
      expect(isValidAnchor('<div>invalid</div>')).toBe(false);
      expect(isValidAnchor('<!-- invalid -->')).toBe(false);
      expect(isValidAnchor('plain text')).toBe(false);
    });

    it('应该拒绝格式不完整的锚点', () => {
      expect(isValidAnchor('<!-- @block:block_001 -->')).toBe(false);
      expect(isValidAnchor('<!-- @block:block_001 100,50,400 -->')).toBe(false);
      expect(isValidAnchor('<!-- @block: 100,50,400,30 -->')).toBe(false);
    });
  });
});
