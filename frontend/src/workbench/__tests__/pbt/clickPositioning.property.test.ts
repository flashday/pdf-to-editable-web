/**
 * PBT-2: 点击定位准确性测试
 * **Validates: Requirements 7.2**
 * 
 * 属性：点击 PDF 上的 Block 后，编辑器必须滚动到包含对应锚点的段落
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { parseAnchors, getBlockIdAtPosition } from '../../utils/anchorParser';

// 生成有效的 Block ID（使用新格式 block_xxx）
const blockIdArb = fc.stringMatching(/^block_[0-9]{3,6}$/);

// 生成有效的坐标
const coordArb = fc.record({
  x: fc.integer({ min: 0, max: 2000 }),
  y: fc.integer({ min: 0, max: 3000 }),
  width: fc.integer({ min: 10, max: 1000 }),
  height: fc.integer({ min: 10, max: 500 }),
});

// 生成带锚点的 Markdown 段落（使用 V2 新格式）
function generateMarkdownParagraph(blockId: string, coords: { x: number; y: number; width: number; height: number }, content: string): string {
  // 使用新的统一锚点格式 <!-- @block:block_xxx x,y,width,height -->
  return `<!-- @block:${blockId} ${coords.x},${coords.y},${coords.width},${coords.height} -->\n${content}\n\n`;
}

describe('PBT-2: 点击定位准确性', () => {
  it('属性：getBlockIdAtPosition 返回位置之前最近的锚点 ID', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: blockIdArb,
            coords: coordArb,
            content: fc.string({ minLength: 10, maxLength: 100 }),
          }),
          { minLength: 2, maxLength: 10 }
        ),
        (paragraphs) => {
          // 确保 ID 唯一
          const uniqueParagraphs = paragraphs.filter((p, i, self) => 
            self.findIndex(x => x.id === p.id) === i
          );
          
          if (uniqueParagraphs.length < 2) return true;
          
          // 生成 Markdown
          const markdown = uniqueParagraphs
            .map(p => generateMarkdownParagraph(p.id, p.coords, p.content))
            .join('');
          
          // 解析锚点
          const anchors = parseAnchors(markdown);
          
          if (anchors.length < 2) return true;
          
          // 对于每个锚点之后的位置，应返回该锚点的 ID
          for (let i = 0; i < anchors.length; i++) {
            const anchor = anchors[i];
            const nextAnchor = anchors[i + 1];
            
            // 在当前锚点位置之后、下一个锚点之前的位置
            const testPosition = nextAnchor 
              ? Math.floor((anchor.position + nextAnchor.position) / 2)
              : anchor.position + 50;
            
            const foundId = getBlockIdAtPosition(anchors, testPosition);
            expect(foundId).toBe(anchor.blockId);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：位置在第一个锚点之前返回 null', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: blockIdArb,
          coords: coordArb,
        }),
        (block) => {
          const markdown = `一些前置内容\n\n${generateMarkdownParagraph(block.id, block.coords, '段落内容')}`;
          const anchors = parseAnchors(markdown);
          
          if (anchors.length === 0) return true;
          
          // 在第一个锚点之前的位置应返回 null
          const positionBeforeFirst = anchors[0].position - 1;
          if (positionBeforeFirst >= 0) {
            const foundId = getBlockIdAtPosition(anchors, positionBeforeFirst);
            expect(foundId).toBeNull();
          }
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('属性：精确位置匹配', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: blockIdArb,
            coords: coordArb,
          }),
          { minLength: 1, maxLength: 5 }
        ),
        (blocks) => {
          const uniqueBlocks = blocks.filter((b, i, self) => 
            self.findIndex(x => x.id === b.id) === i
          );
          
          const markdown = uniqueBlocks
            .map((b, i) => generateMarkdownParagraph(b.id, b.coords, `段落 ${i}`))
            .join('');
          
          const anchors = parseAnchors(markdown);
          
          // 在锚点精确位置应返回该锚点 ID
          for (const anchor of anchors) {
            const foundId = getBlockIdAtPosition(anchors, anchor.position);
            expect(foundId).toBe(anchor.blockId);
          }
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('属性：空锚点数组对任意位置返回 null', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 10000 }),
        (position) => {
          const foundId = getBlockIdAtPosition([], position);
          expect(foundId).toBeNull();
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });

  it('属性：负位置返回 null', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: blockIdArb,
            coords: coordArb,
          }),
          { minLength: 1, maxLength: 5 }
        ),
        fc.integer({ min: -1000, max: -1 }),
        (blocks, negativePosition) => {
          const uniqueBlocks = blocks.filter((b, i, self) => 
            self.findIndex(x => x.id === b.id) === i
          );
          
          const markdown = uniqueBlocks
            .map((b, i) => generateMarkdownParagraph(b.id, b.coords, `段落 ${i}`))
            .join('');
          
          const anchors = parseAnchors(markdown);
          const foundId = getBlockIdAtPosition(anchors, negativePosition);
          expect(foundId).toBeNull();
          
          return true;
        }
      ),
      { numRuns: 50 }
    );
  });
});
