/**
 * 图像缓存 Hook - 优化图像加载性能
 * 任务 20.2: 优化图像加载（懒加载、缓存）
 */
import { useState, useEffect, useCallback, useRef } from 'react';

interface ImageCacheEntry {
  url: string;
  blob: Blob;
  objectUrl: string;
  timestamp: number;
  width: number;
  height: number;
}

interface UseImageCacheOptions {
  /** 缓存最大条目数 */
  maxEntries?: number;
  /** 缓存过期时间（毫秒） */
  maxAge?: number;
}

interface UseImageCacheResult {
  /** 获取缓存的图像 URL（如果已缓存）或原始 URL */
  getCachedUrl: (url: string) => string;
  /** 预加载图像 */
  preloadImage: (url: string) => Promise<void>;
  /** 检查图像是否已缓存 */
  isCached: (url: string) => boolean;
  /** 清除缓存 */
  clearCache: () => void;
  /** 缓存统计 */
  stats: { size: number; hits: number; misses: number };
}

// 全局图像缓存
const imageCache = new Map<string, ImageCacheEntry>();
let cacheHits = 0;
let cacheMisses = 0;

const DEFAULT_MAX_ENTRIES = 20;
const DEFAULT_MAX_AGE = 30 * 60 * 1000; // 30 分钟

/**
 * 图像缓存 Hook
 */
export function useImageCache({
  maxEntries = DEFAULT_MAX_ENTRIES,
  maxAge = DEFAULT_MAX_AGE,
}: UseImageCacheOptions = {}): UseImageCacheResult {
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // 清理过期缓存
  const cleanupExpired = useCallback(() => {
    const now = Date.now();
    const expiredKeys: string[] = [];
    
    imageCache.forEach((entry, key) => {
      if (now - entry.timestamp > maxAge) {
        URL.revokeObjectURL(entry.objectUrl);
        expiredKeys.push(key);
      }
    });
    
    expiredKeys.forEach(key => imageCache.delete(key));
  }, [maxAge]);

  // 限制缓存大小
  const enforceMaxEntries = useCallback(() => {
    if (imageCache.size <= maxEntries) return;
    
    // 按时间戳排序，删除最旧的条目
    const entries = Array.from(imageCache.entries())
      .sort((a, b) => a[1].timestamp - b[1].timestamp);
    
    const toRemove = entries.slice(0, imageCache.size - maxEntries);
    toRemove.forEach(([key, entry]) => {
      URL.revokeObjectURL(entry.objectUrl);
      imageCache.delete(key);
    });
  }, [maxEntries]);

  // 预加载图像
  const preloadImage = useCallback(async (url: string): Promise<void> => {
    if (imageCache.has(url)) {
      cacheHits++;
      return;
    }

    cacheMisses++;

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch image');
      
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      
      // 获取图像尺寸
      const dimensions = await new Promise<{ width: number; height: number }>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
        img.onerror = reject;
        img.src = objectUrl;
      });

      if (!mountedRef.current) {
        URL.revokeObjectURL(objectUrl);
        return;
      }

      imageCache.set(url, {
        url,
        blob,
        objectUrl,
        timestamp: Date.now(),
        width: dimensions.width,
        height: dimensions.height,
      });

      cleanupExpired();
      enforceMaxEntries();
    } catch (error) {
      console.warn('Failed to cache image:', url, error);
    }
  }, [cleanupExpired, enforceMaxEntries]);

  // 获取缓存的 URL
  const getCachedUrl = useCallback((url: string): string => {
    const entry = imageCache.get(url);
    if (entry) {
      cacheHits++;
      return entry.objectUrl;
    }
    cacheMisses++;
    return url;
  }, []);

  // 检查是否已缓存
  const isCached = useCallback((url: string): boolean => {
    return imageCache.has(url);
  }, []);

  // 清除缓存
  const clearCache = useCallback(() => {
    imageCache.forEach(entry => {
      URL.revokeObjectURL(entry.objectUrl);
    });
    imageCache.clear();
    cacheHits = 0;
    cacheMisses = 0;
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      // 不清除全局缓存，只标记组件已卸载
    };
  }, []);

  return {
    getCachedUrl,
    preloadImage,
    isCached,
    clearCache,
    stats: {
      size: imageCache.size,
      hits: cacheHits,
      misses: cacheMisses,
    },
  };
}

export default useImageCache;
