"""
表格处理模块

负责表格相关功能：
- 表格检测
- 表格结构解析
- 单元格提取
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import cv2

from backend.models.document import Region, TableStructure, BoundingBox, RegionType

logger = logging.getLogger(__name__)


class TableProcessor:
    """表格处理器"""
    
    def __init__(self):
        pass
    
    def parse_table_result(self, table_item: Dict[str, Any]) -> Optional[TableStructure]:
        """
        解析 PP-Structure 的表格结果
        
        Args:
            table_item: PP-Structure 结果中的表格项
            
        Returns:
            TableStructure 对象或 None
        """
        try:
            logger.info(f"解析表格项，键: {list(table_item.keys())}")
            
            bbox = BoundingBox(0, 0, 0, 0)
            if 'bbox' in table_item:
                box = table_item['bbox']
                if len(box) >= 4:
                    bbox = BoundingBox(
                        x=float(box[0]),
                        y=float(box[1]),
                        width=float(box[2] - box[0]),
                        height=float(box[3] - box[1])
                    )
            
            if 'res' not in table_item:
                logger.warning("表格项中没有 'res' 键")
                return None
            
            table_data = table_item['res']
            table_structure = None
            
            if isinstance(table_data, dict):
                if 'html' in table_data:
                    table_structure = self._parse_html_table(table_data['html'])
                elif 'cell_bbox' in table_data:
                    table_structure = self._parse_cell_bbox_table(table_data)
            elif isinstance(table_data, list):
                table_structure = self._parse_list_table(table_data)
            elif isinstance(table_data, str):
                table_structure = self._parse_html_table(table_data)
            
            if table_structure and bbox.width > 0:
                table_structure.coordinates = bbox
            
            return table_structure
            
        except Exception as e:
            logger.warning(f"解析表格结果失败: {e}")
            return None
    
    def _parse_html_table(self, html_content: str) -> Optional[TableStructure]:
        """
        解析 HTML 表格内容以提取结构
        
        Args:
            html_content: HTML 表格内容
            
        Returns:
            TableStructure 对象或 None
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return None
            
            rows = table.find_all('tr')
            if not rows:
                return None
            
            table_grid = []
            max_cols = 0
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                table_grid.append(row_data)
                max_cols = max(max_cols, len(row_data))
            
            for row in table_grid:
                while len(row) < max_cols:
                    row.append('')
            
            has_headers = bool(rows[0].find_all('th')) if rows else False
            
            return TableStructure(
                rows=len(table_grid),
                columns=max_cols,
                cells=table_grid,
                coordinates=BoundingBox(0, 0, 0, 0),
                has_headers=has_headers
            )
            
        except ImportError:
            logger.warning("BeautifulSoup 不可用于 HTML 表格解析")
            return None
        except Exception as e:
            logger.warning(f"HTML 表格解析失败: {e}")
            return None
    
    def _parse_cell_bbox_table(self, table_data: Dict) -> Optional[TableStructure]:
        """
        从单元格边界框数据解析表格
        
        Args:
            table_data: 包含 cell_bbox 和其他表格信息的字典
            
        Returns:
            TableStructure 对象或 None
        """
        try:
            cell_bboxes = table_data.get('cell_bbox', [])
            if not cell_bboxes:
                return None
            
            rows_dict = {}
            for cell_info in cell_bboxes:
                if len(cell_info) >= 5:
                    y_center = (cell_info[1] + cell_info[3]) / 2
                    row_key = int(y_center / 20)
                    
                    if row_key not in rows_dict:
                        rows_dict[row_key] = []
                    
                    text = str(cell_info[4]) if len(cell_info) > 4 else ''
                    rows_dict[row_key].append((cell_info[0], text))
            
            sorted_rows = sorted(rows_dict.keys())
            table_grid = []
            max_cols = 0
            
            for row_key in sorted_rows:
                cells = sorted(rows_dict[row_key], key=lambda x: x[0])
                row_data = [cell[1] for cell in cells]
                table_grid.append(row_data)
                max_cols = max(max_cols, len(row_data))
            
            for row in table_grid:
                while len(row) < max_cols:
                    row.append('')
            
            if not table_grid:
                return None
            
            return TableStructure(
                rows=len(table_grid),
                columns=max_cols,
                cells=table_grid,
                coordinates=BoundingBox(0, 0, 0, 0),
                has_headers=True
            )
            
        except Exception as e:
            logger.warning(f"单元格边界框表格解析失败: {e}")
            return None
    
    def _parse_list_table(self, table_data: List) -> Optional[TableStructure]:
        """
        解析列表格式的表格数据
        
        Args:
            table_data: 列表格式的表格数据
            
        Returns:
            TableStructure 对象或 None
        """
        try:
            if not table_data:
                return None
            
            table_grid = []
            max_cols = 0
            
            for row_data in table_data:
                if isinstance(row_data, list):
                    row = [str(cell) for cell in row_data]
                    table_grid.append(row)
                    max_cols = max(max_cols, len(row))
                elif isinstance(row_data, str):
                    row = [cell.strip() for cell in row_data.split('\t') if cell.strip()]
                    if not row:
                        row = [cell.strip() for cell in row_data.split() if cell.strip()]
                    table_grid.append(row)
                    max_cols = max(max_cols, len(row))
            
            for row in table_grid:
                while len(row) < max_cols:
                    row.append('')
            
            if not table_grid:
                return None
            
            return TableStructure(
                rows=len(table_grid),
                columns=max_cols,
                cells=table_grid,
                coordinates=BoundingBox(0, 0, 0, 0),
                has_headers=self._detect_table_headers(table_grid)
            )
            
        except Exception as e:
            logger.warning(f"列表表格解析失败: {e}")
            return None
    
    def _detect_table_headers(self, table_grid: List[List[str]]) -> bool:
        """
        基于内容分析检测表格是否有标题行
        
        Args:
            table_grid: 2D 表格网格
            
        Returns:
            如果表格可能有标题则返回 True
        """
        if not table_grid or len(table_grid) < 2:
            return False
        
        try:
            first_row = table_grid[0]
            second_row = table_grid[1] if len(table_grid) > 1 else []
            
            header_indicators = 0
            
            for i, cell in enumerate(first_row):
                if not cell:
                    continue
                
                if len(cell) < 50 and any(char.isalpha() for char in cell):
                    header_indicators += 1
                
                if i < len(second_row) and second_row[i]:
                    if (cell.replace(' ', '').isalpha() and 
                        any(char.isdigit() for char in second_row[i])):
                        header_indicators += 1
            
            return header_indicators > len(first_row) / 2
            
        except Exception as e:
            logger.warning(f"标题检测失败: {e}")
            return False
    
    def split_large_table(self, table: TableStructure) -> List[TableStructure]:
        """
        基于空行将大表格拆分为小表格
        
        Args:
            table: 待拆分的大表格结构
            
        Returns:
            小表格结构列表
        """
        if not table.cells or len(table.cells) <= 5:
            return [table]
        
        tables = []
        current_rows = []
        empty_row_count = 0
        
        for row_idx, row in enumerate(table.cells):
            non_empty_cells = sum(1 for cell in row if cell and cell.strip())
            is_empty_row = non_empty_cells <= 1
            
            if is_empty_row:
                empty_row_count += 1
                if empty_row_count >= 2 and current_rows:
                    if len(current_rows) >= 2:
                        new_table = TableStructure(
                            rows=len(current_rows),
                            columns=table.columns,
                            cells=current_rows,
                            coordinates=table.coordinates,
                            has_headers=True
                        )
                        tables.append(new_table)
                    current_rows = []
                    empty_row_count = 0
            else:
                empty_row_count = 0
                current_rows.append(row)
        
        if current_rows and len(current_rows) >= 2:
            new_table = TableStructure(
                rows=len(current_rows),
                columns=table.columns,
                cells=current_rows,
                coordinates=table.coordinates,
                has_headers=True
            )
            tables.append(new_table)
        
        if not tables:
            return [table]
        
        logger.info(f"将 {table.rows} 行的表格拆分为 {len(tables)} 个表格")
        return tables
    
    def extract_table_from_region(self, image: np.ndarray, region: Region, 
                                   ocr_engine) -> Optional[TableStructure]:
        """
        从特定区域提取表格结构
        
        Args:
            image: OpenCV 图像数组
            region: 包含表格的区域
            ocr_engine: OCR 引擎实例
            
        Returns:
            TableStructure 对象或 None
        """
        try:
            x = int(region.coordinates.x)
            y = int(region.coordinates.y)
            w = int(region.coordinates.width)
            h = int(region.coordinates.height)
            
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(image.shape[1] - x, w + 2 * padding)
            h = min(image.shape[0] - y, h + 2 * padding)
            
            cropped_table = image[y:y+h, x:x+w]
            
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                temp_path = tmp.name
                cv2.imwrite(temp_path, cropped_table)
            
            table_structure = self._analyze_table_structure(temp_path, region.coordinates, ocr_engine)
            
            try:
                os.remove(temp_path)
            except OSError:
                pass
            
            return table_structure
            
        except Exception as e:
            logger.warning(f"从区域提取表格失败: {e}")
            return None
    
    def _analyze_table_structure(self, table_image_path: str, original_coords: BoundingBox,
                                  ocr_engine) -> Optional[TableStructure]:
        """
        使用 OCR 和布局分析来分析表格结构
        
        Args:
            table_image_path: 裁剪的表格图像路径
            original_coords: 表格的原始坐标
            ocr_engine: OCR 引擎实例
            
        Returns:
            TableStructure 对象或 None
        """
        try:
            ocr_result = ocr_engine.ocr(table_image_path, cls=True)
            
            if not ocr_result or not ocr_result[0]:
                return None
            
            cells_data = self._parse_table_cells(ocr_result[0])
            
            if not cells_data:
                return None
            
            table_grid = self._organize_cells_into_grid(cells_data)
            
            if not table_grid:
                return None
            
            has_headers = self._detect_table_headers(table_grid)
            
            return TableStructure(
                rows=len(table_grid),
                columns=len(table_grid[0]) if table_grid else 0,
                cells=table_grid,
                coordinates=original_coords,
                has_headers=has_headers
            )
            
        except Exception as e:
            logger.warning(f"表格结构分析失败: {e}")
            return None
    
    def _parse_table_cells(self, ocr_result: List) -> List[Dict[str, Any]]:
        """
        解析 OCR 结果以提取表格单元格信息
        
        Args:
            ocr_result: 表格图像的 OCR 结果
            
        Returns:
            单元格数据字典列表
        """
        cells = []
        
        for line in ocr_result:
            if len(line) < 2:
                continue
            
            try:
                bbox_coords = line[0]
                x_coords = [point[0] for point in bbox_coords]
                y_coords = [point[1] for point in bbox_coords]
                
                cell_bbox = BoundingBox(
                    x=min(x_coords),
                    y=min(y_coords),
                    width=max(x_coords) - min(x_coords),
                    height=max(y_coords) - min(y_coords)
                )
                
                text_content = line[1][0]
                confidence = line[1][1]
                
                cells.append({
                    'bbox': cell_bbox,
                    'content': text_content.strip(),
                    'confidence': confidence,
                    'center_x': cell_bbox.x + cell_bbox.width / 2,
                    'center_y': cell_bbox.y + cell_bbox.height / 2
                })
                
            except Exception as e:
                logger.warning(f"解析表格单元格失败: {e}")
                continue
        
        return cells
    
    def _organize_cells_into_grid(self, cells_data: List[Dict[str, Any]]) -> List[List[str]]:
        """
        将单元格数据组织成 2D 网格结构
        
        Args:
            cells_data: 单元格数据字典列表
            
        Returns:
            表示表格网格的 2D 列表
        """
        if not cells_data:
            return []
        
        try:
            cells_data.sort(key=lambda cell: (cell['center_y'], cell['center_x']))
            
            rows = []
            current_row = []
            current_y = cells_data[0]['center_y']
            y_tolerance = 20
            
            for cell in cells_data:
                if abs(cell['center_y'] - current_y) <= y_tolerance:
                    current_row.append(cell)
                else:
                    if current_row:
                        current_row.sort(key=lambda c: c['center_x'])
                        rows.append(current_row)
                    current_row = [cell]
                    current_y = cell['center_y']
            
            if current_row:
                current_row.sort(key=lambda c: c['center_x'])
                rows.append(current_row)
            
            max_cols = max(len(row) for row in rows) if rows else 0
            table_grid = []
            
            for row in rows:
                row_data = []
                for i in range(max_cols):
                    if i < len(row):
                        row_data.append(row[i]['content'])
                    else:
                        row_data.append('')
                table_grid.append(row_data)
            
            return table_grid
            
        except Exception as e:
            logger.warning(f"组织单元格到网格失败: {e}")
            return []
