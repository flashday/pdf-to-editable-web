/**
 * Feature: workbench-v2-optimization, Property 8: 旧格式锚点不被解析
 * **Validates: Requirements 4.5**
 * 
 * 属性：对于任意使用旧格式（div 格式或无 @block: 前缀的注释格式）的锚点字符串，
 * parseAnchors 应该返回空数组。
 * 
 * 旧格式包括：
 * 1. Div 格式: <div id="block_xxx" data-coords="x,y,w,h" style="display:none;"></div>
 * 2. 无 @block: 前缀的注释格式: <!-- block:xxx coords:x,y,w,h -->
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { parseAnchors } from '../../utils/anchorParser';

// 生成有效的 Block ID（使用 block_xxx 格式）
const blockIdArb = fc.stringMatching(/^block_[0-9a-f]{3,8}$/);

// 生成有效的坐标（非负整数）
const coordsArb = fc.record({
  x: fc.integer({ min: 0, max: 10000 }),
  y: fc.integer({ min: 0, max: 10000 }),
  width: fc.integer({ min: 1, max: 5000 }),
  height: fc.integer({ min: 1, max: 5000 }),
});

// 生成旧格式 div 锚点字符串
function generateOldDivFormat(
  blockId: string,
  coords: { x: number; y: number; width: number; height: number }
): string {
  return `<div id="${blockId}" data-coords="${coords.x},${coords.y},${coords.width},${coords.height}" style="display:none;"></div>`;
}

// 生成旧格式注释锚点字符串（无 @block: 前缀）
function generateOldCommentFormat(
  blockId: string,
  coords: { x: number; y: number; width: number; height: number }
): string {
  return `<!-- block:${blockId} coords:${coords.x},${coords.y},${coords.width},${coords.height} -->`;
}

// 生成另一种旧格式注释（空格分隔坐标）
function generateOldCommentFormatAlt(
  blockId: string,
  coords: { x: number; y: number; width: number; height: number }
): string {
  return `<!-- block:${blockId} ${coords.x},${coords.y},${coords.width},${coords.height} -->`;
}

describe('Property 8: 旧格式锚点不被解析', () => {
  /**
   * 核心属性测试：旧格式 div 锚点不被解析
   */
  it('属性：旧格式 div 锚点不被解析', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        (blockId, coords) => {
          // 生成旧格式 div 锚点
          const oldDivAnchor = generateOldDivFormat(blockId, coords);
          
          // 解析锚点
          const anchors = parseAnchors(oldDivAnchor);
          
          // 应该返回空数组
          expect(anchors).toEqual([]);
          expect(anchors.length).toBe(0);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 核心属性测试：旧格式注释锚点（带 coords: 前缀）不被解析
   */
  it('属性：旧格式注释锚点（带 coords: 前缀）不被解析', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        (blockId, coords) => {
          // 生成旧格式注释锚点
          const oldCommentAnchor = generateOldCommentFormat(blockId, coords);
          
          // 解析锚点
          const anchors = parseAnchors(oldCommentAnchor);
          
          // 应该返回空数组
          expect(anchors).toEqual([]);
          expect(anchors.length).toBe(0);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 核心属性测试：旧格式注释锚点（无 @block: 前缀）不被解析
   */
  it('属性：旧格式注释锚点（无 @block: 前缀）不被解析', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        (blockId, coords) => {
          // 生成旧格式注释锚点（无 @block: 前缀，但格式类似新格式）
          const oldCommentAnchor = generateOldCommentFormatAlt(blockId, coords);
          
          // 解析锚点
          const anchors = parseAnchors(oldCommentAnchor);
          
          // 应该返回空数组（因为缺少 @block: 前缀）
          expect(anchors).toEqual([]);
          expect(anchors.length).toBe(0);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 混合内容测试：旧格式锚点嵌入在 Markdown 内容中不被解析
   */
  it('属性：旧格式锚点嵌入在 Markdown 内容中不被解析', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        fc.string({ minLength: 0, maxLength: 200 }),
        fc.string({ minLength: 0, maxLength: 200 }),
        (blockId, coords, prefix, suffix) => {
          // 过滤掉可能产生新格式锚点的内容
          const safePrefix = prefix.replace(/@block:/g, '');
          const safeSuffix = suffix.replace(/@block:/g, '');
          
          // 生成包含旧格式锚点的 Markdown
          const oldDivAnchor = generateOldDivFormat(blockId, coords);
          const markdown = `${safePrefix}\n${oldDivAnchor}\n${safeSuffix}`;
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 应该返回空数组
          expect(anchors).toEqual([]);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 混合内容测试：旧格式注释锚点嵌入在 Markdown 内容中不被解析
   */
  it('属性：旧格式注释锚点嵌入在 Markdown 内容中不被解析', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        fc.string({ minLength: 0, maxLength: 200 }),
        fc.string({ minLength: 0, maxLength: 200 }),
        (blockId, coords, prefix, suffix) => {
          // 过滤掉可能产生新格式锚点的内容
          const safePrefix = prefix.replace(/@block:/g, '');
          const safeSuffix = suffix.replace(/@block:/g, '');
          
          // 生成包含旧格式注释锚点的 Markdown
          const oldCommentAnchor = generateOldCommentFormat(blockId, coords);
          const markdown = `${safePrefix}\n${oldCommentAnchor}\n${safeSuffix}`;
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 应该返回空数组
          expect(anchors).toEqual([]);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 多个旧格式锚点测试：多个旧格式锚点都不被解析
   */
  it('属性：多个旧格式锚点都不被解析', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({ blockId: blockIdArb, coords: coordsArb }),
          { minLength: 1, maxLength: 10 }
        ),
        (blocks) => {
          // 生成包含多个旧格式锚点的 Markdown
          const markdown = blocks.map(({ blockId, coords }, index) => {
            // 交替使用不同的旧格式
            if (index % 3 === 0) {
              return generateOldDivFormat(blockId, coords);
            } else if (index % 3 === 1) {
              return generateOldCommentFormat(blockId, coords);
            } else {
              return generateOldCommentFormatAlt(blockId, coords);
            }
          }).join('\n\n段落内容\n\n');
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 应该返回空数组
          expect(anchors).toEqual([]);
          expect(anchors.length).toBe(0);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界测试：空字符串返回空数组
   */
  it('属性：空字符串返回空数组', () => {
    const anchors = parseAnchors('');
    expect(anchors).toEqual([]);
  });

  /**
   * 边界测试：纯文本内容（无任何锚点格式）返回空数组
   */
  it('属性：纯文本内容返回空数组', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 500 }),
        (text) => {
          // 过滤掉可能产生新格式锚点的内容
          const safeText = text.replace(/@block:/g, '').replace(/<!--/g, '');
          
          const anchors = parseAnchors(safeText);
          
          expect(anchors).toEqual([]);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 对比测试：确保新格式仍然被正确解析（作为对照）
   */
  it('对比：新格式锚点仍然被正确解析', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        (blockId, coords) => {
          // 生成新格式锚点
          const newFormatAnchor = `<!-- @block:${blockId} ${coords.x},${coords.y},${coords.width},${coords.height} -->`;
          
          // 解析锚点
          const anchors = parseAnchors(newFormatAnchor);
          
          // 新格式应该被正确解析
          expect(anchors.length).toBe(1);
          expect(anchors[0].blockId).toBe(blockId);
          expect(anchors[0].coords.x).toBe(coords.x);
          expect(anchors[0].coords.y).toBe(coords.y);
          expect(anchors[0].coords.width).toBe(coords.width);
          expect(anchors[0].coords.height).toBe(coords.height);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 混合格式测试：新旧格式混合时只解析新格式
   */
  it('属性：新旧格式混合时只解析新格式', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        blockIdArb,
        coordsArb,
        coordsArb,
        (oldBlockId, newBlockId, oldCoords, newCoords) => {
          // 确保两个 Block ID 不同
          const uniqueNewBlockId = newBlockId === oldBlockId 
            ? `${newBlockId}_new` 
            : newBlockId;
          
          // 生成混合格式的 Markdown
          const oldDivAnchor = generateOldDivFormat(oldBlockId, oldCoords);
          const oldCommentAnchor = generateOldCommentFormat(oldBlockId, oldCoords);
          const newFormatAnchor = `<!-- @block:${uniqueNewBlockId} ${newCoords.x},${newCoords.y},${newCoords.width},${newCoords.height} -->`;
          
          const markdown = `
${oldDivAnchor}
旧格式 div 锚点上方的内容

${oldCommentAnchor}
旧格式注释锚点上方的内容

${newFormatAnchor}
新格式锚点上方的内容
`;
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 应该只解析出新格式的锚点
          expect(anchors.length).toBe(1);
          expect(anchors[0].blockId).toBe(uniqueNewBlockId);
          expect(anchors[0].coords.x).toBe(newCoords.x);
          expect(anchors[0].coords.y).toBe(newCoords.y);
          expect(anchors[0].coords.width).toBe(newCoords.width);
          expect(anchors[0].coords.height).toBe(newCoords.height);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
