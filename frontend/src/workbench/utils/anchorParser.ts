/**
 * 锚点解析工具
 * 用于解析 Markdown 中的 Block ID 锚点，实现 PDF 与编辑器的双向定位
 */

import { AnchorInfo } from '../stores/types';

/**
 * 锚点正则表达式
 * 匹配格式: <div id="block_xxx" data-coords="x,y,w,h" style="display:none;"></div>
 */
const ANCHOR_REGEX = /<div\s+id="block_([^"]+)"\s+data-coords="(\d+),(\d+),(\d+),(\d+)"[^>]*><\/div>/g;

/**
 * HTML 注释格式锚点正则（备用格式）
 * 匹配格式: <!-- block:xxx coords:x,y,w,h -->
 */
const COMMENT_ANCHOR_REGEX = /<!--\s*block:([^\s]+)\s+coords:(\d+),(\d+),(\d+),(\d+)\s*-->/g;

/**
 * 解析 Markdown 中的所有锚点
 * @param markdown Markdown 内容
 * @returns 锚点信息数组，按位置排序
 */
export function parseAnchors(markdown: string): AnchorInfo[] {
  const anchors: AnchorInfo[] = [];
  
  // 尝试解析 div 格式锚点
  let match;
  const divRegex = new RegExp(ANCHOR_REGEX.source, 'g');
  while ((match = divRegex.exec(markdown)) !== null) {
    anchors.push({
      blockId: match[1],
      coords: {
        x: parseInt(match[2], 10),
        y: parseInt(match[3], 10),
        width: parseInt(match[4], 10),
        height: parseInt(match[5], 10)
      },
      position: match.index
    });
  }

  // 如果没有找到 div 格式，尝试解析注释格式
  if (anchors.length === 0) {
    const commentRegex = new RegExp(COMMENT_ANCHOR_REGEX.source, 'g');
    while ((match = commentRegex.exec(markdown)) !== null) {
      anchors.push({
        blockId: match[1],
        coords: {
          x: parseInt(match[2], 10),
          y: parseInt(match[3], 10),
          width: parseInt(match[4], 10),
          height: parseInt(match[5], 10)
        },
        position: match.index
      });
    }
  }

  // 按位置排序
  anchors.sort((a, b) => a.position - b.position);

  return anchors;
}

/**
 * 根据光标位置获取当前所在的 Block ID
 * @param anchors 锚点数组（需要按位置排序）
 * @param position 光标在文档中的位置
 * @returns Block ID 或 null
 */
export function getBlockIdAtPosition(anchors: AnchorInfo[], position: number): string | null {
  if (!anchors || anchors.length === 0) {
    return null;
  }

  // 找到位置之前最近的锚点
  let nearestAnchor: AnchorInfo | null = null;
  
  for (const anchor of anchors) {
    if (anchor.position <= position) {
      nearestAnchor = anchor;
    } else {
      // 锚点已经超过当前位置，停止搜索
      break;
    }
  }

  return nearestAnchor?.blockId ?? null;
}

/**
 * 根据 Block ID 获取锚点信息
 * @param anchors 锚点数组
 * @param blockId Block ID
 * @returns 锚点信息或 null
 */
export function getAnchorByBlockId(anchors: AnchorInfo[], blockId: string): AnchorInfo | null {
  return anchors.find(anchor => anchor.blockId === blockId) ?? null;
}

/**
 * 获取指定 Block ID 在 Markdown 中的位置
 * @param anchors 锚点数组
 * @param blockId Block ID
 * @returns 位置或 -1
 */
export function getPositionByBlockId(anchors: AnchorInfo[], blockId: string): number {
  const anchor = getAnchorByBlockId(anchors, blockId);
  return anchor?.position ?? -1;
}

/**
 * 生成锚点 HTML
 * @param blockId Block ID
 * @param coords 坐标信息
 * @returns 锚点 HTML 字符串
 */
export function generateAnchorHtml(
  blockId: string, 
  coords: { x: number; y: number; width: number; height: number }
): string {
  return `<div id="block_${blockId}" data-coords="${coords.x},${coords.y},${coords.width},${coords.height}" style="display:none;"></div>`;
}

/**
 * 生成锚点注释（备用格式）
 * @param blockId Block ID
 * @param coords 坐标信息
 * @returns 锚点注释字符串
 */
export function generateAnchorComment(
  blockId: string,
  coords: { x: number; y: number; width: number; height: number }
): string {
  return `<!-- block:${blockId} coords:${coords.x},${coords.y},${coords.width},${coords.height} -->`;
}

/**
 * 从 Markdown 中移除所有锚点
 * @param markdown Markdown 内容
 * @returns 移除锚点后的 Markdown
 */
export function removeAnchors(markdown: string): string {
  let result = markdown;
  
  // 移除 div 格式锚点
  result = result.replace(new RegExp(ANCHOR_REGEX.source, 'g'), '');
  
  // 移除注释格式锚点
  result = result.replace(new RegExp(COMMENT_ANCHOR_REGEX.source, 'g'), '');
  
  // 清理多余的空行
  result = result.replace(/\n{3,}/g, '\n\n');
  
  return result.trim();
}

/**
 * 验证锚点格式是否正确
 * @param anchorHtml 锚点 HTML 字符串
 * @returns 是否有效
 */
export function isValidAnchor(anchorHtml: string): boolean {
  const divMatch = anchorHtml.match(ANCHOR_REGEX);
  const commentMatch = anchorHtml.match(COMMENT_ANCHOR_REGEX);
  return !!(divMatch || commentMatch);
}
