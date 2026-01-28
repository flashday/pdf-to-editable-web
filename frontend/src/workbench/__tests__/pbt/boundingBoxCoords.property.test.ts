/**
 * Feature: workbench-v2-optimization, Property 1: Bounding Box 坐标直接缩放
 * **Validates: Requirements 1.4, 1.5**
 * 
 * 属性：对于任意 LayoutBlock 和任意 zoomLevel（10-500），渲染后的 Bounding Box 位置
 * 应该等于 block.bbox * (zoomLevel / 100)，无需任何额外的坐标转换因子。
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// 纯函数：计算缩放后的 Bounding Box 坐标
// 这是 BoundingBoxOverlay 组件中使用的核心计算逻辑
export function calculateScaledBoundingBox(
  bbox: { x: number; y: number; width: number; height: number },
  zoomLevel: number
): { left: number; top: number; width: number; height: number } {
  const scale = zoomLevel / 100;
  return {
    left: bbox.x * scale,
    top: bbox.y * scale,
    width: bbox.width * scale,
    height: bbox.height * scale,
  };
}

// 生成有效的 bbox 坐标（非负整数）
const bboxArb = fc.record({
  x: fc.integer({ min: 0, max: 10000 }),
  y: fc.integer({ min: 0, max: 10000 }),
  width: fc.integer({ min: 1, max: 5000 }),
  height: fc.integer({ min: 1, max: 5000 }),
});

// 生成有效的 zoomLevel（10-500）
const zoomLevelArb = fc.integer({ min: 10, max: 500 });

// 生成 LayoutBlock 类型
const blockTypeArb = fc.constantFrom('title', 'text', 'table', 'figure', 'list', 'reference');

// 生成完整的 LayoutBlock
const layoutBlockArb = fc.record({
  id: fc.stringMatching(/^block_[0-9a-f]{3,8}$/),
  type: blockTypeArb,
  bbox: bboxArb,
  confidence: fc.float({ min: 0, max: 1 }),
  pageNum: fc.integer({ min: 1, max: 100 }),
});

describe('Property 1: Bounding Box 坐标直接缩放', () => {
  /**
   * 核心属性测试：缩放后的坐标等于原始坐标乘以缩放因子
   */
  it('属性：缩放后的坐标等于 bbox * (zoomLevel / 100)', () => {
    fc.assert(
      fc.property(
        bboxArb,
        zoomLevelArb,
        (bbox, zoomLevel) => {
          const result = calculateScaledBoundingBox(bbox, zoomLevel);
          const scale = zoomLevel / 100;
          
          // 验证每个坐标值
          expect(result.left).toBeCloseTo(bbox.x * scale, 10);
          expect(result.top).toBeCloseTo(bbox.y * scale, 10);
          expect(result.width).toBeCloseTo(bbox.width * scale, 10);
          expect(result.height).toBeCloseTo(bbox.height * scale, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：100% 缩放时坐标不变
   */
  it('属性：100% 缩放时坐标不变', () => {
    fc.assert(
      fc.property(
        bboxArb,
        (bbox) => {
          const result = calculateScaledBoundingBox(bbox, 100);
          
          expect(result.left).toBe(bbox.x);
          expect(result.top).toBe(bbox.y);
          expect(result.width).toBe(bbox.width);
          expect(result.height).toBe(bbox.height);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：50% 缩放时坐标减半
   */
  it('属性：50% 缩放时坐标减半', () => {
    fc.assert(
      fc.property(
        bboxArb,
        (bbox) => {
          const result = calculateScaledBoundingBox(bbox, 50);
          
          expect(result.left).toBeCloseTo(bbox.x / 2, 10);
          expect(result.top).toBeCloseTo(bbox.y / 2, 10);
          expect(result.width).toBeCloseTo(bbox.width / 2, 10);
          expect(result.height).toBeCloseTo(bbox.height / 2, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：200% 缩放时坐标加倍
   */
  it('属性：200% 缩放时坐标加倍', () => {
    fc.assert(
      fc.property(
        bboxArb,
        (bbox) => {
          const result = calculateScaledBoundingBox(bbox, 200);
          
          expect(result.left).toBeCloseTo(bbox.x * 2, 10);
          expect(result.top).toBeCloseTo(bbox.y * 2, 10);
          expect(result.width).toBeCloseTo(bbox.width * 2, 10);
          expect(result.height).toBeCloseTo(bbox.height * 2, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：缩放是线性的（两次缩放等于一次组合缩放）
   */
  it('属性：缩放是线性的', () => {
    fc.assert(
      fc.property(
        bboxArb,
        zoomLevelArb,
        zoomLevelArb,
        (bbox, zoom1, zoom2) => {
          // 先缩放 zoom1，再缩放 zoom2
          const intermediate = calculateScaledBoundingBox(bbox, zoom1);
          const intermediateBbox = {
            x: intermediate.left,
            y: intermediate.top,
            width: intermediate.width,
            height: intermediate.height,
          };
          const result1 = calculateScaledBoundingBox(intermediateBbox, zoom2);
          
          // 直接缩放组合值
          const combinedZoom = (zoom1 / 100) * (zoom2 / 100) * 100;
          const result2 = calculateScaledBoundingBox(bbox, combinedZoom);
          
          // 两种方式应该得到相同结果
          expect(result1.left).toBeCloseTo(result2.left, 5);
          expect(result1.top).toBeCloseTo(result2.top, 5);
          expect(result1.width).toBeCloseTo(result2.width, 5);
          expect(result1.height).toBeCloseTo(result2.height, 5);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：缩放保持宽高比
   */
  it('属性：缩放保持宽高比', () => {
    fc.assert(
      fc.property(
        bboxArb,
        zoomLevelArb,
        (bbox, zoomLevel) => {
          const result = calculateScaledBoundingBox(bbox, zoomLevel);
          
          // 原始宽高比
          const originalRatio = bbox.width / bbox.height;
          // 缩放后宽高比
          const scaledRatio = result.width / result.height;
          
          // 宽高比应该保持不变
          expect(scaledRatio).toBeCloseTo(originalRatio, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 属性测试：缩放后的坐标始终为非负数
   */
  it('属性：缩放后的坐标始终为非负数', () => {
    fc.assert(
      fc.property(
        bboxArb,
        zoomLevelArb,
        (bbox, zoomLevel) => {
          const result = calculateScaledBoundingBox(bbox, zoomLevel);
          
          expect(result.left).toBeGreaterThanOrEqual(0);
          expect(result.top).toBeGreaterThanOrEqual(0);
          expect(result.width).toBeGreaterThan(0);
          expect(result.height).toBeGreaterThan(0);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界测试：最小缩放级别（10%）
   */
  it('属性：最小缩放级别（10%）正确计算', () => {
    fc.assert(
      fc.property(
        bboxArb,
        (bbox) => {
          const result = calculateScaledBoundingBox(bbox, 10);
          
          expect(result.left).toBeCloseTo(bbox.x * 0.1, 10);
          expect(result.top).toBeCloseTo(bbox.y * 0.1, 10);
          expect(result.width).toBeCloseTo(bbox.width * 0.1, 10);
          expect(result.height).toBeCloseTo(bbox.height * 0.1, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 边界测试：最大缩放级别（500%）
   */
  it('属性：最大缩放级别（500%）正确计算', () => {
    fc.assert(
      fc.property(
        bboxArb,
        (bbox) => {
          const result = calculateScaledBoundingBox(bbox, 500);
          
          expect(result.left).toBeCloseTo(bbox.x * 5, 10);
          expect(result.top).toBeCloseTo(bbox.y * 5, 10);
          expect(result.width).toBeCloseTo(bbox.width * 5, 10);
          expect(result.height).toBeCloseTo(bbox.height * 5, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * 使用完整 LayoutBlock 的属性测试
   */
  it('属性：完整 LayoutBlock 的 bbox 正确缩放', () => {
    fc.assert(
      fc.property(
        layoutBlockArb,
        zoomLevelArb,
        (block, zoomLevel) => {
          const result = calculateScaledBoundingBox(block.bbox, zoomLevel);
          const scale = zoomLevel / 100;
          
          expect(result.left).toBeCloseTo(block.bbox.x * scale, 10);
          expect(result.top).toBeCloseTo(block.bbox.y * scale, 10);
          expect(result.width).toBeCloseTo(block.bbox.width * scale, 10);
          expect(result.height).toBeCloseTo(block.bbox.height * scale, 10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
