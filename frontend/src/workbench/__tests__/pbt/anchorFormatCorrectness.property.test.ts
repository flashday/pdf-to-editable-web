/**
 * Feature: workbench-v2-optimization, Property 6: 锚点生成格式正确性
 * **Validates: Requirements 4.1**
 * 
 * 属性：对于任意 Block ID（非空字符串）和坐标（非负整数），
 * generateAnchor 生成的字符串应该匹配正则表达式 /^<!-- @block:\S+ \d+,\d+,\d+,\d+ -->$/
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { generateAnchor } from '../../utils/anchorParser';

// 锚点格式正则表达式（根据设计文档定义）
const ANCHOR_FORMAT_REGEX = /^<!-- @block:\S+ \d+,\d+,\d+,\d+ -->$/;

// 生成非空字符串作为 Block ID（不包含空白字符）
const nonEmptyBlockIdArb = fc.stringMatching(/^\S+$/).filter(s => s.length > 0);

// 生成标准格式的 Block ID（block_xxx 格式）
const standardBlockIdArb = fc.stringMatching(/^block_[0-9a-f]{3,8}$/);

// 生成非负整数坐标
const nonNegativeCoordArb = fc.integer({ min: 0, max: 100000 });

// 生成有效的坐标对象
const coordsArb = fc.record({
  x: nonNegativeCoordArb,
  y: nonNegativeCoordArb,
  width: nonNegativeCoordArb,
  height: nonNegativeCoordArb,
});

describe('Property 6: 锚点生成格式正确性', () => {
  /**
   * 核心属性测试：使用标准 Block ID 格式时，生成的锚点应该匹配正则表达式
   */
  it('属性：标准 Block ID 和非负整数坐标生成的锚点格式正确', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          // 生成锚点字符串
          const anchorStr = generateAnchor(blockId, coords);
          
          // 验证格式匹配正则表达式
          expect(anchorStr).toMatch(ANCHOR_FORMAT_REGEX);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：任意非空非空白字符串作为 Block ID 时，格式仍然正确
   */
  it('属性：任意非空非空白 Block ID 和非负整数坐标生成的锚点格式正确', () => {
    fc.assert(
      fc.property(
        nonEmptyBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          // 生成锚点字符串
          const anchorStr = generateAnchor(blockId, coords);
          
          // 验证格式匹配正则表达式
          expect(anchorStr).toMatch(ANCHOR_FORMAT_REGEX);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：锚点字符串以 "<!-- @block:" 开头
   */
  it('属性：生成的锚点以 "<!-- @block:" 开头', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchorStr = generateAnchor(blockId, coords);
          
          expect(anchorStr.startsWith('<!-- @block:')).toBe(true);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：锚点字符串以 " -->" 结尾
   */
  it('属性：生成的锚点以 " -->" 结尾', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchorStr = generateAnchor(blockId, coords);
          
          expect(anchorStr.endsWith(' -->')).toBe(true);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：锚点包含正确的坐标格式（逗号分隔的四个数字）
   */
  it('属性：锚点包含正确的坐标格式（x,y,width,height）', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchorStr = generateAnchor(blockId, coords);
          
          // 提取坐标部分
          const coordsMatch = anchorStr.match(/(\d+),(\d+),(\d+),(\d+)/);
          
          expect(coordsMatch).not.toBeNull();
          
          if (coordsMatch) {
            expect(parseInt(coordsMatch[1], 10)).toBe(coords.x);
            expect(parseInt(coordsMatch[2], 10)).toBe(coords.y);
            expect(parseInt(coordsMatch[3], 10)).toBe(coords.width);
            expect(parseInt(coordsMatch[4], 10)).toBe(coords.height);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：锚点包含正确的 Block ID
   */
  it('属性：锚点包含正确的 Block ID', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchorStr = generateAnchor(blockId, coords);
          
          // 提取 Block ID 部分
          const blockIdMatch = anchorStr.match(/<!-- @block:(\S+) /);
          
          expect(blockIdMatch).not.toBeNull();
          
          if (blockIdMatch) {
            expect(blockIdMatch[1]).toBe(blockId);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界值测试：坐标为 0 时格式仍然正确
   */
  it('属性：坐标为 0 时格式仍然正确', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        (blockId) => {
          const coords = { x: 0, y: 0, width: 0, height: 0 };
          const anchorStr = generateAnchor(blockId, coords);
          
          expect(anchorStr).toMatch(ANCHOR_FORMAT_REGEX);
          expect(anchorStr).toContain('0,0,0,0');
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界值测试：大坐标值时格式仍然正确
   */
  it('属性：大坐标值时格式仍然正确', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        fc.integer({ min: 10000, max: 1000000 }),
        fc.integer({ min: 10000, max: 1000000 }),
        fc.integer({ min: 10000, max: 1000000 }),
        fc.integer({ min: 10000, max: 1000000 }),
        (blockId, x, y, width, height) => {
          const coords = { x, y, width, height };
          const anchorStr = generateAnchor(blockId, coords);
          
          expect(anchorStr).toMatch(ANCHOR_FORMAT_REGEX);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：生成的锚点是单行的（不包含换行符）
   */
  it('属性：生成的锚点是单行的', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchorStr = generateAnchor(blockId, coords);
          
          expect(anchorStr).not.toContain('\n');
          expect(anchorStr).not.toContain('\r');
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：Block ID 和坐标之间有且仅有一个空格
   */
  it('属性：Block ID 和坐标之间有且仅有一个空格', () => {
    fc.assert(
      fc.property(
        standardBlockIdArb,
        coordsArb,
        (blockId, coords) => {
          const anchorStr = generateAnchor(blockId, coords);
          
          // 验证格式：@block:ID 坐标（ID 和坐标之间只有一个空格）
          const pattern = new RegExp(`@block:${blockId} ${coords.x},${coords.y},${coords.width},${coords.height}`);
          expect(anchorStr).toMatch(pattern);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
