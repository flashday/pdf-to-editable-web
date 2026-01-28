/**
 * PBT-1: Block ID 映射一致性测试
 * **Validates: Requirements 7.1**
 * 
 * 属性：对于任意 Block ID，PDF 上的 Bounding Box 坐标与 Markdown 中的锚点坐标必须一致
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { parseAnchors, AnchorInfo } from '../../utils/anchorParser';

// 生成有效的 Block ID（使用新格式 block_xxx）
const blockIdArb = fc.stringMatching(/^block_[0-9a-f]{3,8}$/);

// 生成有效的坐标
const coordArb = fc.record({
  x: fc.integer({ min: 0, max: 2000 }),
  y: fc.integer({ min: 0, max: 3000 }),
  width: fc.integer({ min: 10, max: 1000 }),
  height: fc.integer({ min: 10, max: 500 }),
});

// 生成 Layout Block
const layoutBlockArb = fc.record({
  id: blockIdArb,
  type: fc.constantFrom('text', 'table', 'title', 'figure'),
  bbox: coordArb,
  confidence: fc.float({ min: 0, max: 1 }),
  pageNum: fc.integer({ min: 1, max: 10 }),
});

// 生成带锚点的 Markdown 内容（使用 V2 新格式）
function generateMarkdownWithAnchors(blocks: Array<{ id: string; bbox: { x: number; y: number; width: number; height: number } }>): string {
  return blocks.map((block, index) => {
    // 使用新的统一锚点格式 <!-- @block:block_xxx x,y,width,height -->
    const anchor = `<!-- @block:${block.id} ${block.bbox.x},${block.bbox.y},${block.bbox.width},${block.bbox.height} -->`;
    const content = index === 0 ? '# 标题\n' : `段落 ${index} 内容\n`;
    return anchor + '\n' + content;
  }).join('\n');
}

describe('PBT-1: Block ID 映射一致性', () => {
  it('属性：解析后的锚点坐标与原始 Block 坐标一致', () => {
    fc.assert(
      fc.property(
        fc.array(layoutBlockArb, { minLength: 1, maxLength: 20 }),
        (blocks) => {
          // 生成 Markdown
          const markdown = generateMarkdownWithAnchors(blocks);
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          // 验证每个 Block 的坐标一致性
          for (const block of blocks) {
            const anchor = anchors.find(a => a.blockId === block.id);
            
            // 锚点必须存在
            expect(anchor).toBeDefined();
            
            if (anchor) {
              // 坐标必须一致
              expect(anchor.coords.x).toBe(block.bbox.x);
              expect(anchor.coords.y).toBe(block.bbox.y);
              expect(anchor.coords.width).toBe(block.bbox.width);
              expect(anchor.coords.height).toBe(block.bbox.height);
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：Block ID 唯一性保持', () => {
    fc.assert(
      fc.property(
        fc.array(layoutBlockArb, { minLength: 1, maxLength: 20 }),
        (blocks) => {
          // 确保生成的 Block ID 唯一
          const uniqueBlocks = blocks.filter((block, index, self) => 
            self.findIndex(b => b.id === block.id) === index
          );
          
          const markdown = generateMarkdownWithAnchors(uniqueBlocks);
          const anchors = parseAnchors(markdown);
          
          // 解析后的锚点数量应等于唯一 Block 数量
          expect(anchors.length).toBe(uniqueBlocks.length);
          
          // 所有锚点 ID 应唯一
          const anchorIds = anchors.map(a => a.blockId);
          const uniqueAnchorIds = [...new Set(anchorIds)];
          expect(anchorIds.length).toBe(uniqueAnchorIds.length);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：锚点位置单调递增', () => {
    fc.assert(
      fc.property(
        fc.array(layoutBlockArb, { minLength: 2, maxLength: 20 }),
        (blocks) => {
          const uniqueBlocks = blocks.filter((block, index, self) => 
            self.findIndex(b => b.id === block.id) === index
          );
          
          if (uniqueBlocks.length < 2) return true;
          
          const markdown = generateMarkdownWithAnchors(uniqueBlocks);
          const anchors = parseAnchors(markdown);
          
          // 锚点位置应单调递增
          for (let i = 1; i < anchors.length; i++) {
            expect(anchors[i].position).toBeGreaterThan(anchors[i - 1].position);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：空 Markdown 返回空锚点数组', () => {
    const anchors = parseAnchors('');
    expect(anchors).toEqual([]);
  });

  it('属性：无锚点的 Markdown 返回空数组', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 1000 }),
        (content) => {
          // 过滤掉可能意外匹配锚点格式的内容
          const safeContent = content.replace(/@block:/g, '');
          const anchors = parseAnchors(safeContent);
          expect(anchors).toEqual([]);
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });
});
