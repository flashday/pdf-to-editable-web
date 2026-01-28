// 布局块类型
export interface LayoutBlock {
  id: string;
  type: 'text' | 'table' | 'title' | 'figure' | 'list' | 'reference';
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;
  pageNum: number;
  text?: string;
}

// 锚点信息
export interface AnchorInfo {
  blockId: string;
  coords: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  position: number;
}

// API 响应类型
export interface LayoutResponse {
  success: boolean;
  data: {
    blocks: LayoutBlock[];
    imageWidth: number;
    imageHeight: number;
  };
}

export interface MarkdownResponse {
  success: boolean;
  data: {
    markdown: string;
    anchors: AnchorInfo[];
  };
}

export interface SaveResponse {
  success: boolean;
  data: {
    savedAt: string;
    vectorUpdated: boolean;
  };
}
