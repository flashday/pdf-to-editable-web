/**
 * 性能监控日志工具
 * 任务 20.4: 添加性能监控日志
 */

interface PerformanceMetric {
  name: string;
  duration: number;
  timestamp: number;
  metadata?: Record<string, any>;
}

interface PerformanceLoggerOptions {
  /** 是否启用日志 */
  enabled?: boolean;
  /** 是否输出到控制台 */
  logToConsole?: boolean;
  /** 最大保留的指标数量 */
  maxMetrics?: number;
  /** 慢操作阈值（毫秒） */
  slowThreshold?: number;
}

class PerformanceLogger {
  private metrics: PerformanceMetric[] = [];
  private options: Required<PerformanceLoggerOptions>;
  private activeTimers: Map<string, number> = new Map();

  constructor(options: PerformanceLoggerOptions = {}) {
    this.options = {
      enabled: process.env.NODE_ENV === 'development',
      logToConsole: true,
      maxMetrics: 100,
      slowThreshold: 100,
      ...options,
    };
  }

  /**
   * 开始计时
   */
  start(name: string): void {
    if (!this.options.enabled) return;
    this.activeTimers.set(name, performance.now());
  }

  /**
   * 结束计时并记录
   */
  end(name: string, metadata?: Record<string, any>): number {
    if (!this.options.enabled) return 0;

    const startTime = this.activeTimers.get(name);
    if (startTime === undefined) {
      console.warn(`[PerformanceLogger] No start time found for: ${name}`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.activeTimers.delete(name);
    this.record(name, duration, metadata);
    return duration;
  }

  /**
   * 记录性能指标
   */
  record(name: string, duration: number, metadata?: Record<string, any>): void {
    if (!this.options.enabled) return;

    const metric: PerformanceMetric = {
      name,
      duration,
      timestamp: Date.now(),
      metadata,
    };

    this.metrics.push(metric);

    // 限制保留的指标数量
    if (this.metrics.length > this.options.maxMetrics) {
      this.metrics = this.metrics.slice(-this.options.maxMetrics);
    }

    // 输出到控制台
    if (this.options.logToConsole) {
      const isSlow = duration > this.options.slowThreshold;
      const logFn = isSlow ? console.warn : console.log;
      const prefix = isSlow ? '🐢 [SLOW]' : '⚡';
      logFn(
        `${prefix} [Performance] ${name}: ${duration.toFixed(2)}ms`,
        metadata || ''
      );
    }
  }

  /**
   * 测量函数执行时间
   */
  measure<T>(name: string, fn: () => T, metadata?: Record<string, any>): T {
    if (!this.options.enabled) return fn();

    this.start(name);
    try {
      const result = fn();
      this.end(name, metadata);
      return result;
    } catch (error) {
      this.end(name, { ...metadata, error: true });
      throw error;
    }
  }

  /**
   * 测量异步函数执行时间
   */
  async measureAsync<T>(
    name: string,
    fn: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> {
    if (!this.options.enabled) return fn();

    this.start(name);
    try {
      const result = await fn();
      this.end(name, metadata);
      return result;
    } catch (error) {
      this.end(name, { ...metadata, error: true });
      throw error;
    }
  }

  /**
   * 获取所有记录的指标
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * 获取指定名称的指标
   */
  getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter((m) => m.name === name);
  }

  /**
   * 获取性能统计摘要
   */
  getSummary(): Record<string, { count: number; avg: number; min: number; max: number }> {
    const summary: Record<string, { count: number; total: number; min: number; max: number }> = {};

    for (const metric of this.metrics) {
      if (!summary[metric.name]) {
        summary[metric.name] = { count: 0, total: 0, min: Infinity, max: -Infinity };
      }
      summary[metric.name].count++;
      summary[metric.name].total += metric.duration;
      summary[metric.name].min = Math.min(summary[metric.name].min, metric.duration);
      summary[metric.name].max = Math.max(summary[metric.name].max, metric.duration);
    }

    const result: Record<string, { count: number; avg: number; min: number; max: number }> = {};
    for (const [name, data] of Object.entries(summary)) {
      result[name] = {
        count: data.count,
        avg: data.total / data.count,
        min: data.min,
        max: data.max,
      };
    }

    return result;
  }

  /**
   * 打印性能摘要到控制台
   */
  printSummary(): void {
    if (!this.options.enabled) return;

    const summary = this.getSummary();
    console.group('📊 Performance Summary');
    for (const [name, stats] of Object.entries(summary)) {
      console.log(
        `${name}: avg=${stats.avg.toFixed(2)}ms, min=${stats.min.toFixed(2)}ms, max=${stats.max.toFixed(2)}ms, count=${stats.count}`
      );
    }
    console.groupEnd();
  }

  /**
   * 清除所有记录的指标
   */
  clear(): void {
    this.metrics = [];
    this.activeTimers.clear();
  }

  /**
   * 启用/禁用日志
   */
  setEnabled(enabled: boolean): void {
    this.options.enabled = enabled;
  }
}

// 创建全局单例
export const performanceLogger = new PerformanceLogger();

// 导出类以便创建自定义实例
export { PerformanceLogger };
export type { PerformanceMetric, PerformanceLoggerOptions };
