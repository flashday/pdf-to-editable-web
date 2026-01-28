/**
 * Feature: workbench-v2-optimization, Property 2: 最近锚点查找算法
 * **Validates: Requirements 2.1**
 * 
 * 属性：对于任意已排序的锚点列表和任意光标位置，findNearestAnchor 函数应该返回
 * 位置小于等于光标位置的最后一个锚点；如果光标位置在所有锚点之前，应该返回 null。
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { findNearestAnchor } from '../../hooks/useSyncScroll';
import { AnchorInfo } from '../../stores/types';

// 生成有效的 Block ID
const blockIdArb = fc.stringMatching(/^block_[0-9a-f]{3,8}$/);

// 生成有效的坐标
const coordsArb = fc.record({
  x: fc.integer({ min: 0, max: 10000 }),
  y: fc.integer({ min: 0, max: 10000 }),
  width: fc.integer({ min: 1, max: 5000 }),
  height: fc.integer({ min: 1, max: 5000 }),
});

// 生成单个锚点（带有指定位置）
const anchorWithPositionArb = (position: number): fc.Arbitrary<AnchorInfo> =>
  fc.record({
    blockId: blockIdArb,
    coords: coordsArb,
    position: fc.constant(position),
  });

// 生成已排序的锚点列表
const sortedAnchorsArb = fc.array(
  fc.integer({ min: 0, max: 10000 }),
  { minLength: 0, maxLength: 20 }
).chain((positions) => {
  // 确保位置唯一并排序
  const uniquePositions = [...new Set(positions)].sort((a, b) => a - b);
  
  return fc.tuple(
    ...uniquePositions.map(pos => anchorWithPositionArb(pos))
  );
}).map(anchors => anchors as AnchorInfo[]);

// 生成非空的已排序锚点列表
const nonEmptySortedAnchorsArb = fc.array(
  fc.integer({ min: 0, max: 10000 }),
  { minLength: 1, maxLength: 20 }
).chain((positions) => {
  const uniquePositions = [...new Set(positions)].sort((a, b) => a - b);
  
  return fc.tuple(
    ...uniquePositions.map(pos => anchorWithPositionArb(pos))
  );
}).map(anchors => anchors as AnchorInfo[]);

describe('Property 2: 最近锚点查找算法', () => {
  /**
   * 核心属性测试：返回位置小于等于光标位置的最后一个锚点
   */
  it('属性：返回位置小于等于光标位置的最后一个锚点', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        fc.integer({ min: 0, max: 15000 }),
        (anchors, cursorPosition) => {
          const result = findNearestAnchor(anchors, cursorPosition);
          
          // 找出所有位置 <= cursorPosition 的锚点
          const validAnchors = anchors.filter(a => a.position <= cursorPosition);
          
          if (validAnchors.length === 0) {
            // 如果没有有效锚点，应该返回 null
            expect(result).toBeNull();
          } else {
            // 应该返回最后一个有效锚点（位置最大的）
            const expectedAnchor = validAnchors[validAnchors.length - 1];
            expect(result).not.toBeNull();
            expect(result!.blockId).toBe(expectedAnchor.blockId);
            expect(result!.position).toBe(expectedAnchor.position);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：光标位置在所有锚点之前时返回 null
   */
  it('属性：光标位置在所有锚点之前时返回 null', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        (anchors) => {
          // 获取第一个锚点的位置
          const firstPosition = anchors[0].position;
          
          // 如果第一个锚点位置 > 0，测试光标在其之前的情况
          if (firstPosition > 0) {
            const cursorPosition = firstPosition - 1;
            const result = findNearestAnchor(anchors, cursorPosition);
            expect(result).toBeNull();
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：光标位置恰好在某个锚点上时返回该锚点
   */
  it('属性：光标位置恰好在某个锚点上时返回该锚点', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        (anchors) => {
          // 随机选择一个锚点
          const randomIndex = Math.floor(Math.random() * anchors.length);
          const targetAnchor = anchors[randomIndex];
          
          const result = findNearestAnchor(anchors, targetAnchor.position);
          
          expect(result).not.toBeNull();
          expect(result!.blockId).toBe(targetAnchor.blockId);
          expect(result!.position).toBe(targetAnchor.position);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：空锚点列表返回 null
   */
  it('属性：空锚点列表返回 null', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 10000 }),
        (cursorPosition) => {
          const result = findNearestAnchor([], cursorPosition);
          expect(result).toBeNull();
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：返回的锚点位置总是 <= 光标位置
   */
  it('属性：返回的锚点位置总是 <= 光标位置', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        fc.integer({ min: 0, max: 15000 }),
        (anchors, cursorPosition) => {
          const result = findNearestAnchor(anchors, cursorPosition);
          
          if (result !== null) {
            expect(result.position).toBeLessThanOrEqual(cursorPosition);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：不存在比返回锚点更接近光标位置的有效锚点
   */
  it('属性：不存在比返回锚点更接近光标位置的有效锚点', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        fc.integer({ min: 0, max: 15000 }),
        (anchors, cursorPosition) => {
          const result = findNearestAnchor(anchors, cursorPosition);
          
          if (result !== null) {
            // 检查没有其他锚点比 result 更接近光标位置
            for (const anchor of anchors) {
              if (anchor.position <= cursorPosition && anchor.position > result.position) {
                // 不应该存在这样的锚点
                expect(anchor.blockId).toBe(result.blockId);
              }
            }
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：光标位置在最后一个锚点之后时返回最后一个锚点
   */
  it('属性：光标位置在最后一个锚点之后时返回最后一个锚点', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        fc.integer({ min: 1, max: 5000 }),
        (anchors, offset) => {
          const lastAnchor = anchors[anchors.length - 1];
          const cursorPosition = lastAnchor.position + offset;
          
          const result = findNearestAnchor(anchors, cursorPosition);
          
          expect(result).not.toBeNull();
          expect(result!.blockId).toBe(lastAnchor.blockId);
          expect(result!.position).toBe(lastAnchor.position);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：单个锚点的情况
   */
  it('属性：单个锚点时的正确行为', () => {
    fc.assert(
      fc.property(
        anchorWithPositionArb(100),
        fc.integer({ min: 0, max: 500 }),
        (anchor, cursorPosition) => {
          const anchors = [anchor];
          const result = findNearestAnchor(anchors, cursorPosition);
          
          if (cursorPosition < anchor.position) {
            expect(result).toBeNull();
          } else {
            expect(result).not.toBeNull();
            expect(result!.blockId).toBe(anchor.blockId);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：光标位置为 0 时的行为
   */
  it('属性：光标位置为 0 时的正确行为', () => {
    fc.assert(
      fc.property(
        sortedAnchorsArb,
        (anchors) => {
          const result = findNearestAnchor(anchors, 0);
          
          // 只有当存在位置为 0 的锚点时才返回非 null
          const anchorAtZero = anchors.find(a => a.position === 0);
          
          if (anchorAtZero) {
            expect(result).not.toBeNull();
            expect(result!.position).toBe(0);
          } else if (anchors.length === 0 || anchors[0].position > 0) {
            expect(result).toBeNull();
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：null 或 undefined 输入的处理
   */
  it('属性：null 或 undefined 锚点列表返回 null', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 10000 }),
        (cursorPosition) => {
          // @ts-expect-error - 测试 null 输入
          const resultNull = findNearestAnchor(null, cursorPosition);
          expect(resultNull).toBeNull();
          
          // @ts-expect-error - 测试 undefined 输入
          const resultUndefined = findNearestAnchor(undefined, cursorPosition);
          expect(resultUndefined).toBeNull();
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：结果的稳定性（相同输入产生相同输出）
   */
  it('属性：相同输入产生相同输出（确定性）', () => {
    fc.assert(
      fc.property(
        nonEmptySortedAnchorsArb,
        fc.integer({ min: 0, max: 15000 }),
        (anchors, cursorPosition) => {
          const result1 = findNearestAnchor(anchors, cursorPosition);
          const result2 = findNearestAnchor(anchors, cursorPosition);
          
          if (result1 === null) {
            expect(result2).toBeNull();
          } else {
            expect(result2).not.toBeNull();
            expect(result1.blockId).toBe(result2!.blockId);
            expect(result1.position).toBe(result2!.position);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
