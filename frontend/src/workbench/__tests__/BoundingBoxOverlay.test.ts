import { describe, it, expect } from 'vitest';
import { getConfidenceColor, getConfidenceBorderColor } from '../components/PdfPanel/BoundingBoxOverlay';

describe('BoundingBoxOverlay', () => {
  describe('getConfidenceColor', () => {
    it('should return green for confidence >= 0.9', () => {
      expect(getConfidenceColor(0.9)).toBe('rgba(40, 167, 69, 0.25)');
      expect(getConfidenceColor(0.95)).toBe('rgba(40, 167, 69, 0.25)');
      expect(getConfidenceColor(1.0)).toBe('rgba(40, 167, 69, 0.25)');
    });

    it('should return yellow for confidence >= 0.8 and < 0.9', () => {
      expect(getConfidenceColor(0.8)).toBe('rgba(255, 193, 7, 0.25)');
      expect(getConfidenceColor(0.85)).toBe('rgba(255, 193, 7, 0.25)');
      expect(getConfidenceColor(0.89)).toBe('rgba(255, 193, 7, 0.25)');
    });

    it('should return red for confidence < 0.8', () => {
      expect(getConfidenceColor(0.79)).toBe('rgba(220, 53, 69, 0.25)');
      expect(getConfidenceColor(0.5)).toBe('rgba(220, 53, 69, 0.25)');
      expect(getConfidenceColor(0.0)).toBe('rgba(220, 53, 69, 0.25)');
    });
  });

  describe('getConfidenceBorderColor', () => {
    it('should return green border for confidence >= 0.9', () => {
      expect(getConfidenceBorderColor(0.9)).toBe('#28a745');
      expect(getConfidenceBorderColor(0.95)).toBe('#28a745');
      expect(getConfidenceBorderColor(1.0)).toBe('#28a745');
    });

    it('should return yellow border for confidence >= 0.8 and < 0.9', () => {
      expect(getConfidenceBorderColor(0.8)).toBe('#ffc107');
      expect(getConfidenceBorderColor(0.85)).toBe('#ffc107');
      expect(getConfidenceBorderColor(0.89)).toBe('#ffc107');
    });

    it('should return red border for confidence < 0.8', () => {
      expect(getConfidenceBorderColor(0.79)).toBe('#dc3545');
      expect(getConfidenceBorderColor(0.5)).toBe('#dc3545');
      expect(getConfidenceBorderColor(0.0)).toBe('#dc3545');
    });
  });

  describe('confidence thresholds', () => {
    it('should correctly classify boundary values', () => {
      // 边界值测试
      expect(getConfidenceColor(0.9)).toBe('rgba(40, 167, 69, 0.25)'); // 正好 0.9 是绿色
      expect(getConfidenceColor(0.8)).toBe('rgba(255, 193, 7, 0.25)'); // 正好 0.8 是黄色
      
      // 略低于边界
      expect(getConfidenceColor(0.899)).toBe('rgba(255, 193, 7, 0.25)');
      expect(getConfidenceColor(0.799)).toBe('rgba(220, 53, 69, 0.25)');
    });
  });
});
