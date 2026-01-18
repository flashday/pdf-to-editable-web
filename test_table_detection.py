"""
Test script to directly test PPStructure table detection
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path

def test_ppstructure_table_detection():
    """Test PPStructure table detection on the uploaded PDF"""
    
    # Find the most recent uploaded PDF
    temp_folder = Path('temp')
    
    # Look for PNG images in temp folder
    png_files = list(temp_folder.glob('*_page1.png'))
    if not png_files:
        print("No PNG files found in temp folder")
        return
    
    # Use the most recent one
    image_path = str(png_files[-1])
    print(f"Testing with image: {image_path}")
    
    try:
        from paddleocr import PPStructure
        from bs4 import BeautifulSoup
        
        # Initialize PPStructure with table detection
        print("Initializing PPStructure...")
        table_engine = PPStructure(
            use_gpu=False,
            show_log=True,
            lang='ch',
            layout=True,
            table=True,
            ocr=True
        )
        
        # Run detection
        print("Running table detection...")
        result = table_engine(image_path)
        
        print(f"\n=== PPStructure Results ===")
        print(f"Total items detected: {len(result)}")
        
        for idx, item in enumerate(result):
            item_type = item.get('type', 'unknown')
            
            if item_type == 'table' and 'res' in item:
                res = item['res']
                if isinstance(res, dict) and 'html' in res:
                    html = res['html']
                    print(f"\n=== Table {idx} HTML Analysis ===")
                    
                    # Parse HTML
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.find_all('tr')
                    print(f"Total rows in HTML: {len(rows)}")
                    
                    # Analyze rows to find potential table boundaries
                    empty_row_indices = []
                    for row_idx, row in enumerate(rows):
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        non_empty = sum(1 for t in cell_texts if t)
                        
                        if non_empty <= 1:
                            empty_row_indices.append(row_idx)
                        
                        # Print first 15 rows for analysis
                        if row_idx < 15:
                            print(f"  Row {row_idx}: {cell_texts[:5]}... (non-empty: {non_empty})")
                    
                    print(f"\nEmpty/sparse rows at indices: {empty_row_indices[:20]}...")
                    
                    # Try to identify table boundaries
                    print("\n=== Potential Table Boundaries ===")
                    prev_empty = -2
                    boundaries = []
                    for idx in empty_row_indices:
                        if idx - prev_empty > 3:  # Gap of more than 3 rows
                            boundaries.append(idx)
                        prev_empty = idx
                    print(f"Boundaries: {boundaries}")
        
    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_ppstructure_table_detection()
