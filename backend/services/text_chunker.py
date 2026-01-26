"""
Text Chunker - 文本分块器
将长文本切分为适合向量检索的小块
"""
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """文本块"""
    content: str
    index: int
    start_char: int
    end_char: int
    page: Optional[int] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "index": self.index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "page": self.page,
            "metadata": self.metadata or {}
        }


class TextChunker:
    """
    文本分块器
    
    支持多种分块策略：
    - 固定大小分块（带重叠）
    - 按段落分块
    - 按句子分块
    - 混合策略
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_size: int = 50
    ):
        """
        初始化分块器
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 重叠大小（字符数）
            min_chunk_size: 最小分块大小
        """
        if chunk_size is None or chunk_overlap is None:
            from backend.config import ChatOCRConfig
            chunk_size = chunk_size or ChatOCRConfig.CHUNK_SIZE
            chunk_overlap = chunk_overlap or ChatOCRConfig.CHUNK_OVERLAP
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # 中文句子结束符
        self.sentence_endings = ['。', '！', '？', '；', '\n', '.', '!', '?', ';']
        # 段落分隔符
        self.paragraph_separators = ['\n\n', '\r\n\r\n', '\n\r\n']
    
    def chunk_text(
        self,
        text: str,
        strategy: str = "mixed",
        page: Optional[int] = None
    ) -> List[TextChunk]:
        """
        对文本进行分块
        
        Args:
            text: 输入文本
            strategy: 分块策略 ("fixed", "paragraph", "sentence", "mixed")
            page: 页码（可选）
            
        Returns:
            List[TextChunk]: 分块列表
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        if strategy == "fixed":
            return self._chunk_fixed(text, page)
        elif strategy == "paragraph":
            return self._chunk_by_paragraph(text, page)
        elif strategy == "sentence":
            return self._chunk_by_sentence(text, page)
        else:  # mixed
            return self._chunk_mixed(text, page)
    
    def _chunk_fixed(self, text: str, page: Optional[int] = None) -> List[TextChunk]:
        """
        固定大小分块（带重叠）
        
        Args:
            text: 输入文本
            page: 页码
            
        Returns:
            List[TextChunk]: 分块列表
        """
        chunks = []
        start = 0
        index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句子边界处切分
            if end < len(text):
                # 向后查找最近的句子结束符
                best_end = end
                for i in range(end, max(start + self.min_chunk_size, end - 100), -1):
                    if text[i-1] in self.sentence_endings:
                        best_end = i
                        break
                end = best_end
            else:
                end = len(text)
            
            chunk_text = text[start:end].strip()
            
            if chunk_text and len(chunk_text) >= self.min_chunk_size:
                chunks.append(TextChunk(
                    content=chunk_text,
                    index=index,
                    start_char=start,
                    end_char=end,
                    page=page
                ))
                index += 1
            
            # 下一块的起始位置（考虑重叠）
            start = end - self.chunk_overlap
            if start <= chunks[-1].start_char if chunks else 0:
                start = end
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str, page: Optional[int] = None) -> List[TextChunk]:
        """
        按段落分块
        
        Args:
            text: 输入文本
            page: 页码
            
        Returns:
            List[TextChunk]: 分块列表
        """
        # 分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        char_pos = 0
        index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                char_pos += 2  # 空段落
                continue
            
            # 如果当前块加上新段落超过限制
            if current_chunk and len(current_chunk) + len(para) + 1 > self.chunk_size:
                # 保存当前块
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        index=index,
                        start_char=current_start,
                        end_char=char_pos,
                        page=page
                    ))
                    index += 1
                current_chunk = para
                current_start = char_pos
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_start = char_pos
            
            char_pos += len(para) + 2
        
        # 保存最后一块
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(TextChunk(
                content=current_chunk,
                index=index,
                start_char=current_start,
                end_char=len(text),
                page=page
            ))
        
        return chunks
    
    def _chunk_by_sentence(self, text: str, page: Optional[int] = None) -> List[TextChunk]:
        """
        按句子分块
        
        Args:
            text: 输入文本
            page: 页码
            
        Returns:
            List[TextChunk]: 分块列表
        """
        # 使用正则分割句子
        sentence_pattern = r'([^。！？；.!?;]+[。！？；.!?;]?)'
        sentences = re.findall(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        char_pos = 0
        index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_chunk and len(current_chunk) + len(sentence) > self.chunk_size:
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        index=index,
                        start_char=current_start,
                        end_char=char_pos,
                        page=page
                    ))
                    index += 1
                current_chunk = sentence
                current_start = char_pos
            else:
                current_chunk += sentence
            
            char_pos += len(sentence)
        
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(TextChunk(
                content=current_chunk,
                index=index,
                start_char=current_start,
                end_char=len(text),
                page=page
            ))
        
        return chunks
    
    def _chunk_mixed(self, text: str, page: Optional[int] = None) -> List[TextChunk]:
        """
        混合策略分块：优先按段落，段落过长则按句子，句子过长则固定切分
        
        Args:
            text: 输入文本
            page: 页码
            
        Returns:
            List[TextChunk]: 分块列表
        """
        # 先按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        char_pos = 0
        index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                char_pos += 2
                continue
            
            # 如果段落本身就超过限制，需要进一步切分
            if len(para) > self.chunk_size:
                # 先保存当前累积的块
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(TextChunk(
                        content=current_chunk,
                        index=index,
                        start_char=current_start,
                        end_char=char_pos,
                        page=page
                    ))
                    index += 1
                    current_chunk = ""
                
                # 对长段落按句子切分
                sub_chunks = self._chunk_by_sentence(para, page)
                for sub in sub_chunks:
                    sub.index = index
                    sub.start_char += char_pos
                    sub.end_char += char_pos
                    chunks.append(sub)
                    index += 1
                
                current_start = char_pos + len(para) + 2
            else:
                # 正常段落处理
                if current_chunk and len(current_chunk) + len(para) + 2 > self.chunk_size:
                    if len(current_chunk) >= self.min_chunk_size:
                        chunks.append(TextChunk(
                            content=current_chunk,
                            index=index,
                            start_char=current_start,
                            end_char=char_pos,
                            page=page
                        ))
                        index += 1
                    current_chunk = para
                    current_start = char_pos
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
                        current_start = char_pos
            
            char_pos += len(para) + 2
        
        # 保存最后一块
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(TextChunk(
                content=current_chunk,
                index=index,
                start_char=current_start,
                end_char=len(text),
                page=page
            ))
        
        return chunks
    
    def chunk_pages(
        self,
        pages: List[Dict],
        text_key: str = "text",
        page_key: str = "page"
    ) -> List[TextChunk]:
        """
        对多页文档进行分块
        
        Args:
            pages: 页面列表，每个元素包含文本和页码
            text_key: 文本字段名
            page_key: 页码字段名
            
        Returns:
            List[TextChunk]: 所有分块
        """
        all_chunks = []
        global_index = 0
        
        for page_data in pages:
            text = page_data.get(text_key, "")
            page_num = page_data.get(page_key)
            
            if not text:
                continue
            
            page_chunks = self.chunk_text(text, page=page_num)
            
            # 更新全局索引
            for chunk in page_chunks:
                chunk.index = global_index
                chunk.metadata = {"page": page_num}
                all_chunks.append(chunk)
                global_index += 1
        
        return all_chunks
    
    def get_chunk_texts(self, chunks: List[TextChunk]) -> List[str]:
        """
        从分块列表中提取文本
        
        Args:
            chunks: 分块列表
            
        Returns:
            List[str]: 文本列表
        """
        return [chunk.content for chunk in chunks]
    
    def get_chunk_metadatas(self, chunks: List[TextChunk]) -> List[Dict]:
        """
        从分块列表中提取元数据
        
        Args:
            chunks: 分块列表
            
        Returns:
            List[Dict]: 元数据列表
        """
        metadatas = []
        for chunk in chunks:
            meta = {
                "index": chunk.index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char
            }
            if chunk.page is not None:
                meta["page"] = chunk.page
            if chunk.metadata:
                meta.update(chunk.metadata)
            metadatas.append(meta)
        return metadatas


# 便捷函数
def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
    strategy: str = "mixed"
) -> List[TextChunk]:
    """
    便捷的文本分块函数
    
    Args:
        text: 输入文本
        chunk_size: 分块大小
        chunk_overlap: 重叠大小
        strategy: 分块策略
        
    Returns:
        List[TextChunk]: 分块列表
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_text(text, strategy=strategy)
