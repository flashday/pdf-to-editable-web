/**
 * Feature: workbench-v2-optimization, Property 3: 锚点解析 Round-Trip
 * **Validates: Requirements 2.4, 4.2, 4.3**
 * 
 * 属性：对于任意有效的 Block ID 和坐标，使用 generateAnchor 生成锚点字符串后，
 * 再使用 parseAnchors 解析，应该得到相同的 Block ID 和坐标值。
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { generateAnchor, parseAnchors } from '../../utils/anchorParser';

// 生成有效的 Block ID（使用新格式 block_xxx）
const blockIdArb = fc.stringMatching(/^block_[0-9a-f]{3,8}$/);

// 生成有效的坐标（非负整数）
const coordsArb = fc.record({
  x: fc.integer({ min: 0, max: 10000 }),
  y: fc.integer({ min: 0, max: 10000 }),
  width: fc.integer({ min: 1, max: 5000 }),
  height: fc.integer({ min: 1, max: 5000 }),
});

// 生成有效的 Block ID 和坐标组合
const blockWithCoordsArb = fc.record({
  blockId: blockIdArb,
  coords: coordsArb,
});

describe('Property 3: 锚点解析 Round-Trip', () => {
  /**
   * 核心属性测试：generateAnchor -> parseAnchors 应该保持数据一致
   */
  it('属性：单个锚点的 round-trip 保持 Block ID 和坐标一致', () => {
    fc.assert(
      fc.property(
        blockWithCoordsArb,
        ({ blockId, coords }) => {
          // 生成锚点字符串
          const anchorStr = generateAnchor(blockId, coords);
          
          // 解析锚点
          const anchors = parseAnchors(anchorStr);
          
          // 应该解析出恰好一个锚点
          expect(anchors.length).toBe(1);
          
          const parsedAnchor = anchors[0];
          
          // Block ID 应该一致
          expect(parsedAnchor.blockId).toBe(blockId);
          
          // 坐标应该一致
          expect(parsedAnchor.coords.x).toBe(coords.x);
          expect(parsedAnchor.coords.y).toBe(coords.y);
          expect(parsedAnchor.coords.width).toBe(coords.width);
          expect(parsedAnchor.coords.height).toBe(coords.height);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 多个锚点的 round-trip 测试
   */
  it('属性：多个锚点的 round-trip 保持所有数据一致', () => {
    fc.assert(
      fc.property(
        fc.array(blockWithCoordsArb, { minLength: 1, maxLength: 20 }),
        (blocks) => {
          // 确保 Block ID 唯一
          const uniqueBlocks = blocks.filter((block, index, self) =>
            self.findIndex(b => b.blockId === block.blockId) === index
          );
          
          // 生成包含多个锚点的 Markdown 内容
          const markdown = uniqueBlocks.map(({ blockId, coords }) => {
            const anchor = generateAnchor(blockId, coords);
            return `${anchor}\n段落内容\n`;
          }).join('\n');
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 解析出的锚点数量应该与唯一 Block 数量一致
          expect(anchors.length).toBe(uniqueBlocks.length);
          
          // 验证每个锚点的数据一致性
          for (const block of uniqueBlocks) {
            const parsedAnchor = anchors.find(a => a.blockId === block.blockId);
            
            expect(parsedAnchor).toBeDefined();
            
            if (parsedAnchor) {
              expect(parsedAnchor.coords.x).toBe(block.coords.x);
              expect(parsedAnchor.coords.y).toBe(block.coords.y);
              expect(parsedAnchor.coords.width).toBe(block.coords.width);
              expect(parsedAnchor.coords.height).toBe(block.coords.height);
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 锚点嵌入在复杂 Markdown 内容中的 round-trip 测试
   */
  it('属性：锚点嵌入在复杂内容中仍能正确解析', () => {
    fc.assert(
      fc.property(
        blockWithCoordsArb,
        fc.string({ minLength: 0, maxLength: 500 }),
        fc.string({ minLength: 0, maxLength: 500 }),
        ({ blockId, coords }, prefix, suffix) => {
          // 过滤掉可能干扰锚点解析的内容
          const safePrefix = prefix.replace(/@block:/g, '').replace(/<!--/g, '');
          const safeSuffix = suffix.replace(/@block:/g, '').replace(/<!--/g, '');
          
          // 生成锚点字符串
          const anchorStr = generateAnchor(blockId, coords);
          
          // 将锚点嵌入到复杂内容中
          const markdown = `${safePrefix}\n${anchorStr}\n${safeSuffix}`;
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 应该解析出恰好一个锚点
          expect(anchors.length).toBe(1);
          
          const parsedAnchor = anchors[0];
          
          // 数据应该一致
          expect(parsedAnchor.blockId).toBe(blockId);
          expect(parsedAnchor.coords.x).toBe(coords.x);
          expect(parsedAnchor.coords.y).toBe(coords.y);
          expect(parsedAnchor.coords.width).toBe(coords.width);
          expect(parsedAnchor.coords.height).toBe(coords.height);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界值测试：坐标为 0 的情况
   */
  it('属性：坐标为 0 时 round-trip 仍然正确', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        (blockId) => {
          const coords = { x: 0, y: 0, width: 1, height: 1 };
          
          const anchorStr = generateAnchor(blockId, coords);
          const anchors = parseAnchors(anchorStr);
          
          expect(anchors.length).toBe(1);
          expect(anchors[0].blockId).toBe(blockId);
          expect(anchors[0].coords.x).toBe(0);
          expect(anchors[0].coords.y).toBe(0);
          expect(anchors[0].coords.width).toBe(1);
          expect(anchors[0].coords.height).toBe(1);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界值测试：大坐标值的情况
   */
  it('属性：大坐标值时 round-trip 仍然正确', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        fc.integer({ min: 10000, max: 100000 }),
        fc.integer({ min: 10000, max: 100000 }),
        fc.integer({ min: 1000, max: 10000 }),
        fc.integer({ min: 1000, max: 10000 }),
        (blockId, x, y, width, height) => {
          const coords = { x, y, width, height };
          
          const anchorStr = generateAnchor(blockId, coords);
          const anchors = parseAnchors(anchorStr);
          
          expect(anchors.length).toBe(1);
          expect(anchors[0].blockId).toBe(blockId);
          expect(anchors[0].coords.x).toBe(x);
          expect(anchors[0].coords.y).toBe(y);
          expect(anchors[0].coords.width).toBe(width);
          expect(anchors[0].coords.height).toBe(height);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 位置信息测试：解析后的 position 应该正确反映锚点在文本中的位置
   */
  it('属性：解析后的 position 正确反映锚点在文本中的位置', () => {
    fc.assert(
      fc.property(
        blockWithCoordsArb,
        fc.string({ minLength: 0, maxLength: 100 }),
        ({ blockId, coords }, prefix) => {
          // 过滤掉可能干扰锚点解析的内容
          const safePrefix = prefix.replace(/@block:/g, '').replace(/<!--/g, '');
          
          const anchorStr = generateAnchor(blockId, coords);
          const markdown = `${safePrefix}${anchorStr}`;
          
          const anchors = parseAnchors(markdown);
          
          expect(anchors.length).toBe(1);
          // position 应该等于前缀的长度
          expect(anchors[0].position).toBe(safePrefix.length);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
