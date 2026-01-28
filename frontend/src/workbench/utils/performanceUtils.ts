/**
 * 性能优化工具函数
 * 任务 20.3: 优化编辑器渲染性能
 */

/**
 * 防抖函数
 * @param fn 要防抖的函数
 * @param delay 延迟时间（毫秒）
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn.apply(this, args);
      timeoutId = null;
    }, delay);
  };
}

/**
 * 节流函数
 * @param fn 要节流的函数
 * @param limit 最小间隔时间（毫秒）
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    const now = Date.now();
    const remaining = limit - (now - lastCall);

    if (remaining <= 0) {
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      lastCall = now;
      fn.apply(this, args);
    } else if (!timeoutId) {
      timeoutId = setTimeout(() => {
        lastCall = Date.now();
        timeoutId = null;
        fn.apply(this, args);
      }, remaining);
    }
  };
}

/**
 * requestAnimationFrame 节流
 * 使用 RAF 来限制回调频率，适合动画和滚动处理
 */
export function rafThrottle<T extends (...args: any[]) => any>(
  fn: T
): (...args: Parameters<T>) => void {
  let rafId: number | null = null;
  let lastArgs: Parameters<T> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    lastArgs = args;

    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        if (lastArgs) {
          fn.apply(this, lastArgs);
        }
        rafId = null;
      });
    }
  };
}

/**
 * 批量更新工具
 * 收集多个更新并在下一帧一次性执行
 */
export function createBatchUpdater<T>() {
  let pending: T[] = [];
  let rafId: number | null = null;
  let callback: ((items: T[]) => void) | null = null;

  return {
    add(item: T) {
      pending.push(item);
      
      if (rafId === null && callback) {
        rafId = requestAnimationFrame(() => {
          const items = pending;
          pending = [];
          rafId = null;
          callback?.(items);
        });
      }
    },
    
    setCallback(cb: (items: T[]) => void) {
      callback = cb;
    },
    
    flush() {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      const items = pending;
      pending = [];
      return items;
    },
    
    clear() {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      pending = [];
    }
  };
}

/**
 * 性能测量工具
 */
export function measurePerformance(label: string) {
  const start = performance.now();
  
  return {
    end() {
      const duration = performance.now() - start;
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Performance] ${label}: ${duration.toFixed(2)}ms`);
      }
      return duration;
    }
  };
}

/**
 * 内存使用监控（仅开发模式）
 */
export function logMemoryUsage(label: string) {
  if (process.env.NODE_ENV !== 'development') return;
  
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    console.log(`[Memory] ${label}:`, {
      usedJSHeapSize: `${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
      totalJSHeapSize: `${(memory.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
    });
  }
}
