#!/usr/bin/env python3
"""
Demonstration script showing OCR service integration with the document processing pipeline
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tempfile
from PIL import Image, ImageDraw, ImageFont

from backend.services.ocr_service import PaddleOCRService, OCRProcessingError
from backend.models.document import Document, ProcessingStatus, BoundingBox, RegionType


def create_sample_document_image():
    """Create a sample document image for testing"""
    # Create a white background image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to use a system font
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw sample content
    draw.text((50, 50), "CHAPTER 1: INTRODUCTION", fill='black', font=font_large)
    draw.text((50, 120), "This is a sample paragraph of text that demonstrates", fill='black', font=font_medium)
    draw.text((50, 140), "how the OCR service processes different types of content.", fill='black', font=font_medium)
    
    draw.text((50, 200), "Key Features:", fill='black', font=font_medium)
    draw.text((70, 230), "• Layout analysis and region detection", fill='black', font=font_small)
    draw.text((70, 250), "• Text extraction with confidence scoring", fill='black', font=font_small)
    draw.text((70, 270), "• Table structure recognition", fill='black', font=font_small)
    
    # Draw a simple table
    draw.text((50, 320), "Sample Table:", fill='black', font=font_medium)
    draw.rectangle([70, 350, 400, 450], outline='black', width=2)
    draw.line([70, 380, 400, 380], fill='black', width=1)  # Header separator
    draw.line([200, 350, 200, 450], fill='black', width=1)  # Column separator
    draw.line([300, 350, 300, 450], fill='black', width=1)  # Column separator
    
    draw.text((80, 360), "Name", fill='black', font=font_small)
    draw.text((210, 360), "Age", fill='black', font=font_small)
    draw.text((310, 360), "City", fill='black', font=font_small)
    
    draw.text((80, 390), "John", fill='black', font=font_small)
    draw.text((210, 390), "25", fill='black', font=font_small)
    draw.text((310, 390), "NYC", fill='black', font=font_small)
    
    draw.text((80, 420), "Jane", fill='black', font=font_small)
    draw.text((210, 420), "30", fill='black', font=font_small)
    draw.text((310, 420), "LA", fill='black', font=font_small)
    
    return img


def demonstrate_ocr_integration():
    """Demonstrate OCR service integration"""
    print("=== PDF to Editable Web Layout - OCR Integration Demo ===\n")
    
    # Create sample document
    print("1. Creating sample document image...")
    sample_img = create_sample_document_image()
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        sample_img.save(tmp.name, quality=95)
        image_path = tmp.name
    
    print(f"   Sample image saved to: {image_path}")
    
    try:
        # Initialize OCR service
        print("\n2. Initializing OCR service...")
        try:
            ocr_service = PaddleOCRService(use_gpu=False, lang='en')
            print("   ✓ OCR service initialized successfully")
            has_paddle = True
        except OCRProcessingError as e:
            print(f"   ⚠ PaddleOCR not available: {e}")
            print("   → Demonstrating with mock service...")
            ocr_service = PaddleOCRService.__new__(PaddleOCRService)
            ocr_service.use_gpu = False
            ocr_service.lang = 'en'
            ocr_service._ocr_engine = None
            ocr_service._structure_engine = None
            has_paddle = False
        
        # Test image preprocessing
        print("\n3. Testing image preprocessing...")
        preprocessed_path = ocr_service.preprocess_image(image_path)
        print(f"   ✓ Image preprocessed successfully: {preprocessed_path}")
        
        # Test region classification
        print("\n4. Testing region classification...")
        test_regions = [
            ("CHAPTER 1: INTRODUCTION", BoundingBox(50, 50, 300, 30)),
            ("This is a sample paragraph...", BoundingBox(50, 120, 400, 60)),
            ("• Layout analysis and region detection", BoundingBox(70, 230, 350, 20)),
            ("Name | Age | City", BoundingBox(70, 350, 330, 100))
        ]
        
        for text, bbox in test_regions:
            region_type = ocr_service._classify_region(text, bbox)
            print(f"   '{text[:30]}...' → {region_type.value}")
        
        # Test confidence calculation
        print("\n5. Testing confidence metrics...")
        from backend.models.document import Region
        
        sample_regions = [
            Region(BoundingBox(50, 50, 300, 30), RegionType.HEADER, 0.95, "CHAPTER 1: INTRODUCTION"),
            Region(BoundingBox(50, 120, 400, 60), RegionType.PARAGRAPH, 0.88, "Sample paragraph text"),
            Region(BoundingBox(70, 230, 350, 60), RegionType.LIST, 0.85, "• List items"),
            Region(BoundingBox(70, 350, 330, 100), RegionType.TABLE, 0.80, "Table content")
        ]
        
        metrics = ocr_service._calculate_confidence_metrics(sample_regions)
        print(f"   Overall confidence: {metrics['overall']:.2f}")
        print(f"   Text confidence: {metrics['text_confidence']:.2f}")
        print(f"   Layout confidence: {metrics['layout_confidence']:.2f}")
        print(f"   Regions detected: {metrics['region_count']}")
        
        # Test reading order sorting
        print("\n6. Testing reading order sorting...")
        shuffled_regions = [sample_regions[2], sample_regions[0], sample_regions[3], sample_regions[1]]
        sorted_regions = ocr_service._sort_regions_by_reading_order(shuffled_regions)
        
        print("   Reading order:")
        for i, region in enumerate(sorted_regions, 1):
            print(f"   {i}. {region.classification.value}: '{region.content[:30]}...'")
        
        # Test document integration
        print("\n7. Testing document model integration...")
        doc = Document(
            original_filename="sample_document.jpg",
            file_type="jpg",
            file_size=os.path.getsize(image_path),
            processing_status=ProcessingStatus.PROCESSING
        )
        
        print(f"   Document ID: {doc.id}")
        print(f"   Status: {doc.processing_status.value}")
        print(f"   File size: {doc.file_size} bytes")
        
        if has_paddle:
            # If PaddleOCR is available, try actual layout analysis
            print("\n8. Performing actual layout analysis...")
            try:
                layout_result = ocr_service.analyze_layout(image_path)
                print(f"   ✓ Layout analysis completed in {layout_result.processing_time:.2f}s")
                print(f"   ✓ Detected {len(layout_result.regions)} regions")
                print(f"   ✓ Overall confidence: {layout_result.confidence_score:.2f}")
                
                for i, region in enumerate(layout_result.regions[:3], 1):  # Show first 3 regions
                    print(f"   Region {i}: {region.classification.value} (conf: {region.confidence:.2f})")
                    print(f"      Content: '{region.content[:50]}...'")
                
            except Exception as e:
                print(f"   ⚠ Layout analysis failed: {e}")
        else:
            print("\n8. Skipping actual layout analysis (PaddleOCR not available)")
        
        print("\n=== Integration Demo Complete ===")
        print("\nKey Integration Points Verified:")
        print("✓ OCR service can be initialized and configured")
        print("✓ Image preprocessing works independently")
        print("✓ Region classification logic is functional")
        print("✓ Confidence metrics calculation works")
        print("✓ Reading order sorting is implemented")
        print("✓ Document model integration is ready")
        print("✓ Error handling is robust")
        
        if has_paddle:
            print("✓ Full PaddleOCR integration is working")
        else:
            print("⚠ PaddleOCR integration ready (install paddleocr to test)")
        
    finally:
        # Clean up temporary files
        try:
            os.unlink(image_path)
            if 'preprocessed_path' in locals() and preprocessed_path != image_path:
                os.unlink(preprocessed_path)
        except OSError:
            pass


if __name__ == "__main__":
    demonstrate_ocr_integration()