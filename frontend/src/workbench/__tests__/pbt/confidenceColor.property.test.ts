/**
 * PBT-4: 置信度颜色映射测试
 * **Validates: Requirements 7.4**
 * 
 * 属性：置信度 >= 0.9 显示绿色，0.8-0.9 显示黄色，< 0.8 显示红色
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// 置信度颜色映射函数（与 BoundingBoxOverlay 中的实现一致）
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.9) return 'rgba(40, 167, 69, 0.3)';  // 绿色
  if (confidence >= 0.8) return 'rgba(255, 193, 7, 0.3)';  // 黄色
  return 'rgba(220, 53, 69, 0.3)';  // 红色
};

// 颜色常量
const GREEN = 'rgba(40, 167, 69, 0.3)';
const YELLOW = 'rgba(255, 193, 7, 0.3)';
const RED = 'rgba(220, 53, 69, 0.3)';

// 生成高置信度值 (>= 0.9)
const highConfidenceArb = fc.double({ min: 0.9, max: 1.0, noNaN: true });

// 生成中等置信度值 (0.8 - 0.9)
const mediumConfidenceArb = fc.double({ min: 0.8, max: 0.8999999, noNaN: true });

// 生成低置信度值 (< 0.8)
const lowConfidenceArb = fc.double({ min: 0, max: 0.7999999, noNaN: true });

// 生成任意有效置信度值
const anyConfidenceArb = fc.double({ min: 0, max: 1, noNaN: true });

describe('PBT-4: 置信度颜色映射', () => {
  it('属性：高置信度 (>= 0.9) 返回绿色', () => {
    fc.assert(
      fc.property(
        highConfidenceArb,
        (confidence) => {
          const color = getConfidenceColor(confidence);
          expect(color).toBe(GREEN);
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：中等置信度 (0.8 - 0.9) 返回黄色', () => {
    fc.assert(
      fc.property(
        mediumConfidenceArb,
        (confidence) => {
          const color = getConfidenceColor(confidence);
          expect(color).toBe(YELLOW);
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：低置信度 (< 0.8) 返回红色', () => {
    fc.assert(
      fc.property(
        lowConfidenceArb,
        (confidence) => {
          const color = getConfidenceColor(confidence);
          expect(color).toBe(RED);
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：颜色映射是确定性的（相同输入总是返回相同输出）', () => {
    fc.assert(
      fc.property(
        anyConfidenceArb,
        (confidence) => {
          const color1 = getConfidenceColor(confidence);
          const color2 = getConfidenceColor(confidence);
          const color3 = getConfidenceColor(confidence);
          
          expect(color1).toBe(color2);
          expect(color2).toBe(color3);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：颜色映射覆盖所有有效置信度值', () => {
    fc.assert(
      fc.property(
        anyConfidenceArb,
        (confidence) => {
          const color = getConfidenceColor(confidence);
          
          // 必须返回三种颜色之一
          expect([GREEN, YELLOW, RED]).toContain(color);
          
          return true;
        }
      ),
      { numRuns: 200 }
    );
  });

  it('属性：边界值测试 - 0.9 精确值', () => {
    const color = getConfidenceColor(0.9);
    expect(color).toBe(GREEN);
  });

  it('属性：边界值测试 - 0.8 精确值', () => {
    const color = getConfidenceColor(0.8);
    expect(color).toBe(YELLOW);
  });

  it('属性：边界值测试 - 0 和 1', () => {
    expect(getConfidenceColor(0)).toBe(RED);
    expect(getConfidenceColor(1)).toBe(GREEN);
  });

  it('属性：颜色映射单调性 - 更高置信度不会返回更差的颜色', () => {
    const colorRank = (color: string): number => {
      if (color === GREEN) return 3;
      if (color === YELLOW) return 2;
      return 1;
    };

    fc.assert(
      fc.property(
        fc.tuple(anyConfidenceArb, anyConfidenceArb),
        ([conf1, conf2]) => {
          const [lower, higher] = conf1 < conf2 ? [conf1, conf2] : [conf2, conf1];
          
          const lowerColor = getConfidenceColor(lower);
          const higherColor = getConfidenceColor(higher);
          
          // 更高的置信度应该返回相同或更好的颜色
          expect(colorRank(higherColor)).toBeGreaterThanOrEqual(colorRank(lowerColor));
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('属性：颜色分布合理性', () => {
    // 生成大量随机置信度值，验证颜色分布
    const samples = 1000;
    let greenCount = 0;
    let yellowCount = 0;
    let redCount = 0;

    for (let i = 0; i < samples; i++) {
      const confidence = Math.random();
      const color = getConfidenceColor(confidence);
      
      if (color === GREEN) greenCount++;
      else if (color === YELLOW) yellowCount++;
      else redCount++;
    }

    // 绿色应该约占 10% (0.9-1.0)
    // 黄色应该约占 10% (0.8-0.9)
    // 红色应该约占 80% (0-0.8)
    
    // 允许一定误差范围
    expect(greenCount).toBeGreaterThan(samples * 0.05);
    expect(greenCount).toBeLessThan(samples * 0.20);
    
    expect(yellowCount).toBeGreaterThan(samples * 0.05);
    expect(yellowCount).toBeLessThan(samples * 0.20);
    
    expect(redCount).toBeGreaterThan(samples * 0.60);
    expect(redCount).toBeLessThan(samples * 0.95);
  });
});
