/**
 * Property-Based Tests for Anchor Save Integrity
 * 
 * Feature: workbench-v2-optimization
 * Property 7: 锚点保存完整性 Round-Trip
 * 
 * Validates: Requirements 4.6
 * 
 * 对于任意包含锚点的 Markdown 内容，保存到后端再重新加载后，
 * 所有锚点应该保持不变（数量相同、内容相同）。
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { parseAnchors, generateAnchor } from '../../utils/anchorParser';

// Arbitrary generators for anchor components
const blockIdArb = fc.stringMatching(/^block_[0-9a-f]{3,8}$/);

const coordsArb = fc.record({
  x: fc.integer({ min: 0, max: 10000 }),
  y: fc.integer({ min: 0, max: 10000 }),
  width: fc.integer({ min: 1, max: 5000 }),
  height: fc.integer({ min: 1, max: 5000 })
});

const anchorDataArb = fc.record({
  blockId: blockIdArb,
  coords: coordsArb
});

// Generate markdown content
const markdownContentArb = fc.string({ minLength: 0, maxLength: 200 });

describe('Property 7: 锚点保存完整性 Round-Trip', () => {
  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('单个锚点应该在 round-trip 后保持不变', () => {
    fc.assert(
      fc.property(anchorDataArb, markdownContentArb, (anchorData, content) => {
        // Generate anchor string
        const anchor = generateAnchor(anchorData.blockId, anchorData.coords);
        
        // Create markdown with anchor
        const markdown = `${anchor}\n${content}`;
        
        // Parse anchors (simulating load from backend)
        const parsedAnchors = parseAnchors(markdown);
        
        // Verify anchor is preserved
        expect(parsedAnchors).toHaveLength(1);
        expect(parsedAnchors[0].blockId).toBe(anchorData.blockId);
        expect(parsedAnchors[0].coords).toEqual(anchorData.coords);
      }),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('多个锚点应该在 round-trip 后全部保持不变', () => {
    fc.assert(
      fc.property(
        fc.array(anchorDataArb, { minLength: 1, maxLength: 10 }),
        (anchorDataList) => {
          // Ensure unique block IDs
          const uniqueAnchors = anchorDataList.reduce((acc, data, index) => {
            const uniqueId = `${data.blockId}_${index}`;
            acc.push({ ...data, blockId: uniqueId });
            return acc;
          }, [] as typeof anchorDataList);
          
          // Generate markdown with multiple anchors
          const markdown = uniqueAnchors
            .map((data, i) => `${generateAnchor(data.blockId, data.coords)}\nContent block ${i}\n`)
            .join('\n');
          
          // Parse anchors
          const parsedAnchors = parseAnchors(markdown);
          
          // Verify all anchors are preserved
          expect(parsedAnchors).toHaveLength(uniqueAnchors.length);
          
          // Verify each anchor's content
          for (const originalData of uniqueAnchors) {
            const found = parsedAnchors.find(a => a.blockId === originalData.blockId);
            expect(found).toBeDefined();
            expect(found?.coords).toEqual(originalData.coords);
          }
        }
      ),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('锚点顺序应该按位置保持一致', () => {
    fc.assert(
      fc.property(
        fc.array(anchorDataArb, { minLength: 2, maxLength: 5 }),
        (anchorDataList) => {
          // Create unique IDs
          const uniqueAnchors = anchorDataList.map((data, index) => ({
            ...data,
            blockId: `block_${index.toString().padStart(3, '0')}`
          }));
          
          // Generate markdown with anchors in order
          const markdown = uniqueAnchors
            .map((data, i) => `${generateAnchor(data.blockId, data.coords)}\nParagraph ${i}\n`)
            .join('\n');
          
          // Parse anchors
          const parsedAnchors = parseAnchors(markdown);
          
          // Verify order is preserved (by position in document)
          expect(parsedAnchors).toHaveLength(uniqueAnchors.length);
          
          // Anchors should be sorted by position
          for (let i = 1; i < parsedAnchors.length; i++) {
            expect(parsedAnchors[i].position).toBeGreaterThan(parsedAnchors[i - 1].position);
          }
        }
      ),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('锚点坐标值应该精确保持', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 10000 }),
        fc.integer({ min: 0, max: 10000 }),
        fc.integer({ min: 1, max: 5000 }),
        fc.integer({ min: 1, max: 5000 }),
        (x, y, width, height) => {
          const coords = { x, y, width, height };
          const blockId = 'test_block';
          
          // Generate and parse
          const anchor = generateAnchor(blockId, coords);
          const markdown = `${anchor}\nSome content`;
          const parsedAnchors = parseAnchors(markdown);
          
          // Verify exact coordinate preservation
          expect(parsedAnchors).toHaveLength(1);
          expect(parsedAnchors[0].coords.x).toBe(x);
          expect(parsedAnchors[0].coords.y).toBe(y);
          expect(parsedAnchors[0].coords.width).toBe(width);
          expect(parsedAnchors[0].coords.height).toBe(height);
        }
      ),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('锚点应该在复杂 Markdown 内容中保持完整', () => {
    fc.assert(
      fc.property(anchorDataArb, (anchorData) => {
        // Complex markdown content with various elements
        const complexContent = `
# Heading 1

## Heading 2

This is a paragraph with **bold** and *italic* text.

- List item 1
- List item 2
  - Nested item

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |

\`\`\`javascript
const code = "example";
\`\`\`

> Blockquote text

[Link](https://example.com)
`;
        
        const anchor = generateAnchor(anchorData.blockId, anchorData.coords);
        const markdown = `${anchor}\n${complexContent}`;
        
        const parsedAnchors = parseAnchors(markdown);
        
        expect(parsedAnchors).toHaveLength(1);
        expect(parsedAnchors[0].blockId).toBe(anchorData.blockId);
        expect(parsedAnchors[0].coords).toEqual(anchorData.coords);
      }),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('锚点应该在包含特殊字符的内容中保持完整', () => {
    fc.assert(
      fc.property(anchorDataArb, (anchorData) => {
        // Content with special characters that might interfere
        const specialContent = `
Content with special chars: < > & " ' \` ~ ! @ # $ % ^ * ( ) [ ] { }
Unicode: 中文 日本語 한국어 العربية
Emoji: 🎉 🚀 ✨
HTML-like: <not-a-tag> </fake>
Comment-like: <!-- not an anchor -->
`;
        
        const anchor = generateAnchor(anchorData.blockId, anchorData.coords);
        const markdown = `${anchor}\n${specialContent}`;
        
        const parsedAnchors = parseAnchors(markdown);
        
        expect(parsedAnchors).toHaveLength(1);
        expect(parsedAnchors[0].blockId).toBe(anchorData.blockId);
        expect(parsedAnchors[0].coords).toEqual(anchorData.coords);
      }),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('空内容不应该产生锚点', () => {
    fc.assert(
      fc.property(fc.constant(''), (emptyContent) => {
        const parsedAnchors = parseAnchors(emptyContent);
        expect(parsedAnchors).toHaveLength(0);
      }),
      { numRuns: 10, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('仅包含普通内容（无锚点）不应该产生锚点', () => {
    fc.assert(
      fc.property(markdownContentArb, (content) => {
        // Ensure content doesn't accidentally contain anchor pattern
        const safeContent = content.replace(/@block:/g, 'block:');
        const parsedAnchors = parseAnchors(safeContent);
        expect(parsedAnchors).toHaveLength(0);
      }),
      { numRuns: 100, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('锚点 blockId 应该精确保持', () => {
    fc.assert(
      fc.property(
        blockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchor = generateAnchor(blockId, coords);
          const markdown = `${anchor}\nContent`;
          const parsedAnchors = parseAnchors(markdown);
          
          expect(parsedAnchors).toHaveLength(1);
          expect(parsedAnchors[0].blockId).toBe(blockId);
        }
      ),
      { numRuns: 50, verbose: true }
    );
  });

  // Feature: workbench-v2-optimization, Property 7: 锚点保存完整性 Round-Trip
  it('边界坐标值应该正确保持', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          { x: 0, y: 0, width: 1, height: 1 },
          { x: 10000, y: 10000, width: 5000, height: 5000 },
          { x: 0, y: 10000, width: 5000, height: 1 },
          { x: 10000, y: 0, width: 1, height: 5000 }
        ),
        (coords) => {
          const blockId = 'boundary_test';
          const anchor = generateAnchor(blockId, coords);
          const markdown = `${anchor}\nContent`;
          const parsedAnchors = parseAnchors(markdown);
          
          expect(parsedAnchors).toHaveLength(1);
          expect(parsedAnchors[0].coords).toEqual(coords);
        }
      ),
      { numRuns: 20, verbose: true }
    );
  });
});
