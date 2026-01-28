"""
API routes for document processing
"""
import os
import uuid
import time
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from backend.api import api_bp
from backend.models.document import Document, ProcessingStatus
from backend.services.validation import FileValidator, ValidationError
from backend.services.pdf_processor import PDFProcessor, PDFProcessingError
from backend.services.error_handler import error_handler
from backend.services.status_tracker import status_tracker, ProcessingStage
from backend.services.performance_monitor import performance_monitor
from backend.services.document_processor import (
    get_document_processor, init_document_processor, ProcessingResult
)
from backend.services.job_cache import get_job_cache, init_job_cache

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'pdf-to-editable-web'})


@api_bp.route('/test-confidence-log', methods=['GET'])
def test_confidence_log():
    """测试置信度日志端点 - 验证前后端通讯"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=== TEST CONFIDENCE LOG ENDPOINT CALLED ===")
    # 返回一个完整精度的测试值
    test_value = 0.9881692556724135
    return jsonify({
        'success': True,
        'message': '前后端通讯正常！',
        'timestamp': time.time(),
        'test_confidence': test_value,
        'test_confidence_str': str(test_value)
    })


@api_bp.route('/debug-confidence/<job_id>', methods=['GET'])
def debug_confidence(job_id):
    """调试端点 - 返回完整的confidence_report数据"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    processor = get_document_processor()
    if processor is None:
        return jsonify({'error': 'Processor not initialized'}), 500
    
    result = processor.get_processing_result(job_id)
    if result is None:
        return jsonify({'error': 'Result not found'}), 404
    
    # 直接返回confidence_report，不做任何处理
    cr = result.confidence_report
    logger.info(f"=== DEBUG CONFIDENCE ===")
    logger.info(f"confidence_report type: {type(cr)}")
    if cr and 'confidence_breakdown' in cr:
        overall = cr['confidence_breakdown'].get('overall', {})
        logger.info(f"overall.score: {overall.get('score')}")
        logger.info(f"overall.score type: {type(overall.get('score'))}")
    
    return jsonify({
        'job_id': job_id,
        'confidence_report': cr,
        'confidence_report_json': json.dumps(cr)
    })

@api_bp.route('/convert', methods=['POST'])
def convert_document():
    """Document conversion endpoint with file upload and validation"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== CONVERT REQUEST RECEIVED ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request files: {request.files}")
    logger.info(f"Request form: {request.form}")
    
    operation_id = performance_monitor.start_operation('document_conversion')
    
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            error = ValidationError('No file provided')
            performance_monitor.end_operation(operation_id, success=False, error_message=str(error))
            response_data, status_code = error_handler.handle_error(
                error, 
                context={'operation': 'file_upload', 'endpoint': '/convert'}
            )
            return jsonify(response_data), status_code
        
        file = request.files['file']
        
        # Validate the uploaded file
        is_valid, error_message = FileValidator.validate_file(file)
        if not is_valid:
            error = ValidationError(error_message)
            performance_monitor.end_operation(operation_id, success=False, error_message=str(error))
            response_data, status_code = error_handler.handle_error(
                error,
                context={
                    'operation': 'file_validation',
                    'filename': file.filename,
                    'endpoint': '/convert'
                }
            )
            return jsonify(response_data), status_code
        
        # Get file information
        file_info = FileValidator.get_file_info(file)
        
        # Get document type ID from form data
        document_type_id = request.form.get('document_type_id', None)
        logger.info(f"Document type ID: {document_type_id}")
        
        # Create document record
        document = Document(
            id=str(uuid.uuid4()),
            original_filename=file_info['original_filename'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            processing_status=ProcessingStatus.PENDING,
            document_type_id=document_type_id
        )
        
        # Create job tracking
        status_tracker.create_job(document.id, {'filename': file_info['original_filename']})
        status_tracker.update_status(document.id, ProcessingStage.UPLOADING, 1.0, 'File uploaded successfully')
        
        # Save file to upload directory
        upload_folder = current_app.config['UPLOAD_FOLDER']
        upload_folder.mkdir(exist_ok=True)
        
        # Generate unique filename to prevent conflicts
        file_extension = file_info['file_type']
        saved_filename = f"{document.id}.{file_extension}"
        file_path = upload_folder / saved_filename
        
        # Register temp file for tracking
        performance_monitor.register_temp_file(str(file_path))
        
        # Save file
        file.save(str(file_path))
        
        # Handle PDF-specific processing
        pdf_info = None
        notification = None
        
        if file_info['file_type'] == 'pdf':
            status_tracker.update_status(document.id, ProcessingStage.PDF_PROCESSING, 0.0, 'Processing PDF')
            
            try:
                # Validate PDF structure
                is_valid_pdf, pdf_error = PDFProcessor.validate_pdf_structure(file_path)
                if not is_valid_pdf:
                    # Clean up uploaded file
                    file_path.unlink(missing_ok=True)
                    error = PDFProcessingError(pdf_error)
                    response_data, status_code = error_handler.handle_error(
                        error,
                        context={
                            'operation': 'pdf_validation',
                            'document_id': document.id,
                            'filename': file_info['original_filename']
                        }
                    )
                    return jsonify(response_data), status_code
                
                # Analyze PDF for page count and metadata
                pdf_analysis = PDFProcessor.analyze_pdf(file_path)
                pdf_info = {
                    'page_count': pdf_analysis['page_count'],
                    'is_multi_page': pdf_analysis['is_multi_page']
                }
                
                # Generate notification for multi-page PDFs
                notification = PDFProcessor.get_processing_notification(pdf_analysis['page_count'])
                
                # 复制原始 PDF 到 temp 目录（方便调试，无论单页还是多页）
                temp_folder = current_app.config['TEMP_FOLDER']
                temp_folder.mkdir(exist_ok=True)
                import shutil
                pdf_cache_path = temp_folder / f"{document.id}_original.pdf"
                shutil.copy2(file_path, pdf_cache_path)
                logger.info(f"Cached original PDF to: {pdf_cache_path}")
                
                # 提取第一页为图像（无论单页还是多页都需要）
                image_path = temp_folder / f"{document.id}_page1.png"
                success, extract_error = PDFProcessor.extract_first_page_as_image(file_path, image_path)
                
                if not success:
                    # Clean up uploaded file
                    file_path.unlink(missing_ok=True)
                    error = PDFProcessingError(f"Could not extract first page: {extract_error}")
                    response_data, status_code = error_handler.handle_error(
                        error,
                        context={
                            'operation': 'pdf_page_extraction',
                            'document_id': document.id,
                            'filename': file_info['original_filename']
                        }
                    )
                    return jsonify(response_data), status_code
                
            except PDFProcessingError as e:
                # Clean up uploaded file
                file_path.unlink(missing_ok=True)
                response_data, status_code = error_handler.handle_error(
                    e,
                    context={
                        'operation': 'pdf_processing',
                        'document_id': document.id,
                        'filename': file_info['original_filename']
                    }
                )
                return jsonify(response_data), status_code
        
        # Initialize document processor if needed and start async processing
        processor = get_document_processor()
        if processor is None:
            processor = init_document_processor(
                upload_folder,
                current_app.config['TEMP_FOLDER'],
                use_gpu=current_app.config.get('OCR_USE_GPU', False)
            )
        
        # Start async document processing
        processor.process_document_async(document)
        
        response_data = {
            'job_id': document.id,
            'status': document.processing_status.value,
            'message': 'File uploaded successfully and processing started',
            'file_info': {
                'original_filename': document.original_filename,
                'file_type': document.file_type,
                'file_size': document.file_size
            }
        }
        
        # Add PDF-specific information
        if pdf_info:
            response_data['pdf_info'] = pdf_info
        
        # Add notification for multi-page PDFs
        if notification:
            response_data['notification'] = notification
        
        # Mark operation as successful
        performance_monitor.end_operation(operation_id, success=True)
        
        return jsonify(response_data), 202
        
    except Exception as e:
        # Handle any unexpected errors
        performance_monitor.end_operation(operation_id, success=False, error_message=str(e))
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'file_upload',
                'endpoint': '/convert'
            }
        )
        return jsonify(response_data), status_code

@api_bp.route('/convert/<job_id>/status', methods=['GET'])
def get_conversion_status(job_id):
    """
    Get conversion status endpoint with detailed progress information
    Provides real-time status updates for processing jobs
    """
    try:
        # Get job status from tracker
        job_status = status_tracker.get_job_progress(job_id)
        
        if not job_status:
            return jsonify({
                'job_id': job_id,
                'error': 'Job not found',
                'status': 'unknown',
                'message': 'The requested job does not exist or has been cleaned up'
            }), 404
        
        # Add additional context for the response
        response_data = {
            'job_id': job_status['job_id'],
            'status': job_status['stage'],
            'progress': job_status['progress'] * 100,  # Convert to percentage
            'progress_percent': job_status['progress_percent'],
            'message': job_status['message'],
            'completed': job_status['completed'],
            'failed': job_status['failed'],
            'error': job_status['error'],
            'elapsed_time': job_status['elapsed_time'],
            'updated_at': job_status['updated_at']
        }
        
        # Add estimated time remaining if processing
        if not job_status['completed'] and not job_status['failed']:
            elapsed = job_status['elapsed_time']
            progress = job_status['progress']
            
            if progress > 0.1:  # Only estimate after 10% progress
                estimated_total = elapsed / progress
                estimated_remaining = estimated_total - elapsed
                response_data['estimated_remaining_seconds'] = max(0, int(estimated_remaining))
        
        return jsonify(response_data)
        
    except Exception as e:
        # Handle any unexpected errors
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_conversion_status',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/status'
            }
        )
        return jsonify(response_data), status_code

@api_bp.route('/convert/<job_id>/result', methods=['GET'])
def get_conversion_result(job_id):
    """Get conversion result endpoint with confidence reporting"""
    try:
        # Get document processor
        processor = get_document_processor()
        
        if processor is None:
            return jsonify({
                'job_id': job_id,
                'error': 'Document processor not initialized',
                'status': 'error'
            }), 500
        
        # Get processing result
        result = processor.get_processing_result(job_id)
        
        if result is None:
            # Check if job exists but is still processing
            job_status = status_tracker.get_job_status(job_id)
            
            if job_status is None:
                return jsonify({
                    'job_id': job_id,
                    'error': 'Job not found',
                    'status': 'unknown'
                }), 404
            
            if not job_status.get('completed') and not job_status.get('failed'):
                return jsonify({
                    'job_id': job_id,
                    'error': 'Processing not yet complete',
                    'status': job_status['status'].value if hasattr(job_status['status'], 'value') else str(job_status['status']),
                    'progress': job_status.get('progress', 0)
                }), 202
            
            if job_status.get('failed'):
                return jsonify({
                    'job_id': job_id,
                    'error': job_status.get('error', 'Processing failed'),
                    'status': 'failed'
                }), 500
        
        # Check if processing failed
        if not result.success:
            return jsonify({
                'job_id': job_id,
                'error': result.error,
                'status': 'failed'
            }), 500
        
        # Build response with Editor.js data
        editor_data = result.editor_data
        
        # Convert EditorJSData to dictionary format
        blocks_data = []
        for block in editor_data.blocks:
            block_dict = {
                'id': block.id,
                'type': block.type,
                'data': block.data
            }
            if block.metadata:
                block_dict['metadata'] = block.metadata
            blocks_data.append(block_dict)
        
        response_data = {
            'job_id': job_id,
            'status': ProcessingStatus.COMPLETED.value,
            'result': {
                'time': editor_data.time,
                'blocks': blocks_data,
                'version': editor_data.version
            },
            'processing_time': result.processing_time
        }
        
        # Add confidence report if available
        if result.confidence_report:
            response_data['confidence_report'] = result.confidence_report
            # 调试日志：打印完整的置信度值
            import logging
            logger = logging.getLogger(__name__)
            if 'confidence_breakdown' in result.confidence_report:
                overall = result.confidence_report['confidence_breakdown'].get('overall', {})
                logger.info(f"=== API返回置信度: {overall.get('score')} ===")
        else:
            # Generate basic confidence report
            response_data['confidence_report'] = {
                'confidence_breakdown': {
                    'overall': {'score': 0.85, 'level': 'good', 'description': 'Good - High accuracy with minimal errors'}
                },
                'warnings': [],
                'has_warnings': False,
                'warning_count': 0,
                'overall_assessment': 'Document processed successfully.'
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        # Handle any unexpected errors
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_conversion_result',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/result'
            }
        )
        return jsonify(response_data), status_code

@api_bp.route('/convert/<job_id>/history', methods=['GET'])
def get_conversion_history(job_id):
    """
    Get status update history for a job
    Provides detailed history of all status updates for debugging and monitoring
    """
    try:
        # Get optional limit parameter
        limit = request.args.get('limit', type=int, default=None)
        
        # Get job history from tracker
        history = status_tracker.get_job_history(job_id, limit=limit)
        
        if not history:
            return jsonify({
                'job_id': job_id,
                'error': 'Job not found or no history available',
                'history': []
            }), 404
        
        return jsonify({
            'job_id': job_id,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        # Handle any unexpected errors
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_conversion_history',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/history'
            }
        )
        return jsonify(response_data), status_code


@api_bp.route('/convert/<job_id>/image', methods=['GET'])
def get_document_image(job_id):
    """
    Get the processed document image for display
    Returns the PDF page converted to image or the original image
    """
    from flask import send_file
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get configured folders
        temp_folder = current_app.config['TEMP_FOLDER']
        upload_folder = current_app.config['UPLOAD_FOLDER']
        
        # Also check root-level folders (for when running from project root)
        root_temp = Path('temp')
        root_uploads = Path('uploads')
        
        # List of temp folders to check
        temp_folders = [temp_folder, root_temp]
        upload_folders = [upload_folder, root_uploads]
        
        # Check temp folders first (for PDF first page images)
        for tf in temp_folders:
            image_path = tf / f"{job_id}_page1.png"
            if image_path.exists():
                logger.info(f"Serving image from temp folder: {image_path}")
                return send_file(str(image_path.resolve()), mimetype='image/png')
            
            # Check for preprocessed image
            preprocessed_path = tf / f"{job_id}_page1_preprocessed.png"
            if preprocessed_path.exists():
                logger.info(f"Serving preprocessed image: {preprocessed_path}")
                return send_file(str(preprocessed_path.resolve()), mimetype='image/png')
        
        # Check upload folders for original file
        for uf in upload_folders:
            # Try different extensions
            for ext in ['png', 'jpg', 'jpeg', 'pdf']:
                file_path = uf / f"{job_id}.{ext}"
                if file_path.exists():
                    if ext == 'pdf':
                        # Convert PDF to image on the fly
                        # Use the first available temp folder
                        target_temp = temp_folder if temp_folder.exists() else root_temp
                        target_temp.mkdir(exist_ok=True)
                        temp_image_path = target_temp / f"{job_id}_page1.png"
                        success, error = PDFProcessor.extract_first_page_as_image(file_path, temp_image_path)
                        if success:
                            logger.info(f"Converted PDF to image: {temp_image_path}")
                            return send_file(str(temp_image_path.resolve()), mimetype='image/png')
                        else:
                            return jsonify({'error': f'Failed to convert PDF: {error}'}), 500
                    else:
                        logger.info(f"Serving original image: {file_path}")
                        mimetype = 'image/png' if ext == 'png' else 'image/jpeg'
                        return send_file(str(file_path.resolve()), mimetype=mimetype)
        
        logger.warning(f"Image not found for job_id: {job_id}")
        return jsonify({
            'job_id': job_id,
            'error': 'Image not found',
            'status': 'not_found'
        }), 404
        
    except Exception as e:
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_document_image',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/image'
            }
        )
        return jsonify(response_data), status_code


@api_bp.route('/convert/<job_id>/raw-output', methods=['GET'])
def get_raw_ocr_output(job_id):
    """
    Get the raw PaddleOCR output (JSON and HTML) and PPStructure output
    Returns the original OCR results before processing
    """
    from pathlib import Path
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check for raw output files
        temp_folder = current_app.config['TEMP_FOLDER']
        root_temp = Path('temp')
        
        temp_folders = [temp_folder, root_temp]
        
        raw_json = None
        raw_html = None
        ppstructure_json = None
        
        for tf in temp_folders:
            json_path = tf / f"{job_id}_raw_ocr.json"
            html_path = tf / f"{job_id}_raw_ocr.html"
            ppstructure_path = tf / f"{job_id}_ppstructure.json"
            
            if json_path.exists() and raw_json is None:
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw_json = json.load(f)
                logger.info(f"Found raw JSON at: {json_path}")
            
            if html_path.exists() and raw_html is None:
                with open(html_path, 'r', encoding='utf-8') as f:
                    raw_html = f.read()
                logger.info(f"Found raw HTML at: {html_path}")
            
            if ppstructure_path.exists() and ppstructure_json is None:
                with open(ppstructure_path, 'r', encoding='utf-8') as f:
                    ppstructure_json = json.load(f)
                logger.info(f"Found PPStructure JSON at: {ppstructure_path}")
            
            if raw_json and raw_html and ppstructure_json:
                break
        
        if not raw_json and not raw_html and not ppstructure_json:
            return jsonify({
                'job_id': job_id,
                'error': 'Raw OCR output not found',
                'message': 'Raw output files may not have been saved for this job'
            }), 404
        
        return jsonify({
            'job_id': job_id,
            'raw_json': raw_json,
            'raw_html': raw_html,
            'ppstructure_json': ppstructure_json
        })
        
    except Exception as e:
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_raw_ocr_output',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/raw-output'
            }
        )
        return jsonify(response_data), status_code


@api_bp.route('/convert/<job_id>/editable-html', methods=['GET'])
def get_editable_html(job_id):
    """
    Get editable HTML content for the OCR result
    Returns HTML with data attributes for inline editing
    """
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check for raw HTML file first (it contains the editable structure)
        temp_folder = current_app.config['TEMP_FOLDER']
        root_temp = Path('temp')
        
        temp_folders = [temp_folder, root_temp]
        
        editable_html = None
        
        for tf in temp_folders:
            html_path = tf / f"{job_id}_raw_ocr.html"
            
            if html_path.exists():
                with open(html_path, 'r', encoding='utf-8') as f:
                    editable_html = f.read()
                logger.info(f"Found editable HTML at: {html_path}")
                break
        
        if not editable_html:
            return jsonify({
                'job_id': job_id,
                'error': 'Editable HTML not found',
                'message': 'HTML output file may not have been saved for this job'
            }), 404
        
        return jsonify({
            'job_id': job_id,
            'editable_html': editable_html
        })
        
    except Exception as e:
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_editable_html',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/editable-html'
            }
        )
        return jsonify(response_data), status_code


@api_bp.route('/convert/<job_id>/markdown', methods=['GET'])
def get_markdown_output(job_id):
    """
    Get Markdown output for the OCR result
    
    PaddleOCR 3.x 新功能：支持 Markdown 格式输出
    将 PPStructure 识别结果转换为 Markdown 格式
    """
    from pathlib import Path
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        temp_folder = current_app.config['TEMP_FOLDER']
        root_temp = Path('temp')
        temp_folders = [temp_folder, root_temp]
        
        # 首先检查是否有预生成的 Markdown 文件
        markdown_content = None
        
        for tf in temp_folders:
            md_path = tf / f"{job_id}_raw_ocr.md"
            if md_path.exists():
                with open(md_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                logger.info(f"Found pre-generated Markdown at: {md_path}")
                break
        
        # 如果没有预生成的 Markdown，从 PPStructure JSON 生成
        if not markdown_content:
            ppstructure_json = None
            for tf in temp_folders:
                ppstructure_path = tf / f"{job_id}_ppstructure.json"
                if ppstructure_path.exists():
                    with open(ppstructure_path, 'r', encoding='utf-8') as f:
                        ppstructure_json = json.load(f)
                    logger.info(f"Found PPStructure JSON at: {ppstructure_path}")
                    break
            
            if ppstructure_json:
                markdown_content = _convert_ppstructure_to_markdown(ppstructure_json)
            else:
                # 尝试从 raw_ocr.json 生成简单的 Markdown
                for tf in temp_folders:
                    json_path = tf / f"{job_id}_raw_ocr.json"
                    if json_path.exists():
                        with open(json_path, 'r', encoding='utf-8') as f:
                            raw_json = json.load(f)
                        markdown_content = _convert_raw_ocr_to_markdown(raw_json)
                        logger.info(f"Generated Markdown from raw OCR JSON")
                        break
        
        if not markdown_content:
            return jsonify({
                'job_id': job_id,
                'error': 'Markdown output not available',
                'message': 'No OCR data found to generate Markdown'
            }), 404
        
        return jsonify({
            'job_id': job_id,
            'markdown': markdown_content,
            'format': 'markdown'
        })
        
    except Exception as e:
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_markdown_output',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/markdown'
            }
        )
        return jsonify(response_data), status_code


def _convert_ppstructure_to_markdown(ppstructure_json):
    """
    将 PPStructure JSON 转换为 Markdown 格式
    
    Args:
        ppstructure_json: PPStructure 输出的 JSON 数据
        
    Returns:
        Markdown 格式字符串
    """
    from bs4 import BeautifulSoup
    
    markdown_parts = []
    items = ppstructure_json.get('items', [])
    
    # 按 y 坐标排序
    sorted_items = sorted(items, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1] if x.get('bbox') else 0)
    
    for item in sorted_items:
        item_type = item.get('type', 'unknown')
        res = item.get('res', {})
        
        # 标题类型（包括 title 和 doc_title）
        if item_type in ('title', 'doc_title'):
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(f"# {text}")
                markdown_parts.append("")
                
        elif item_type == 'text':
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(text)
                markdown_parts.append("")
                
        elif item_type in ('header', 'footer'):
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(f"*{text}*")
                markdown_parts.append("")
                
        elif item_type == 'table':
            if isinstance(res, dict) and 'html' in res:
                table_md = _html_table_to_markdown(res['html'])
                if table_md:
                    markdown_parts.append(table_md)
                    markdown_parts.append("")
                    
        elif item_type == 'figure_caption':
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(f"**{text}**")
                markdown_parts.append("")
                
        elif item_type == 'reference':
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(f"*{text}*")
                markdown_parts.append("")
                
        elif item_type == 'equation':
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(f"${text}$")
                markdown_parts.append("")
                
        elif item_type == 'figure':
            # 图片区域，可以添加占位符
            markdown_parts.append("*[图片]*")
            markdown_parts.append("")
            
        else:
            # 其他未知类型，尝试提取文本
            text = _extract_text_from_res(res)
            if text:
                markdown_parts.append(text)
                markdown_parts.append("")
    
    return '\n'.join(markdown_parts)


def _convert_raw_ocr_to_markdown(raw_json):
    """
    将原始 OCR JSON 转换为简单的 Markdown 格式
    
    Args:
        raw_json: 原始 OCR 输出的 JSON 数据
        
    Returns:
        Markdown 格式字符串
    """
    markdown_parts = []
    ocr_results = raw_json.get('ocr_result', [])
    
    # 按 y 坐标排序
    sorted_results = sorted(ocr_results, key=lambda x: x.get('bbox', {}).get('y', 0))
    
    for item in sorted_results:
        text = item.get('text', '').strip()
        if text:
            markdown_parts.append(text)
    
    return '\n\n'.join(markdown_parts)


def _extract_text_from_res(res):
    """从 res 字段提取文本"""
    if isinstance(res, str):
        return res.strip()
    
    if isinstance(res, list):
        texts = []
        for item in res:
            if isinstance(item, dict) and 'text' in item:
                texts.append(item['text'])
        return ' '.join(texts)
    
    if isinstance(res, dict) and 'text' in res:
        return res['text']
    
    return ''


def _html_table_to_markdown(html_content):
    """HTML 表格转 Markdown"""
    from bs4 import BeautifulSoup
    
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    
    if not table:
        return ""
    
    rows = table.find_all('tr')
    markdown_rows = []
    
    for row_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        cell_texts = [cell.get_text(strip=True).replace('|', '\\|') for cell in cells]
        
        if not cell_texts:
            continue
            
        markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
        
        # 第一行后添加分隔符
        if row_idx == 0:
            separator = '| ' + ' | '.join(['---'] * len(cell_texts)) + ' |'
            markdown_rows.append(separator)
    
    return '\n'.join(markdown_rows)


@api_bp.route('/convert/<job_id>/confidence-log', methods=['GET'])
def get_confidence_log(job_id):
    """
    获取置信度计算详细日志（Markdown 格式）
    
    返回详细的置信度计算过程，包括：
    - 每个区域的置信度
    - 文本置信度计算过程
    - 布局置信度计算过程
    - 总体置信度计算过程
    """
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        temp_folder = current_app.config['TEMP_FOLDER']
        root_temp = Path('temp')
        
        temp_folders = [temp_folder, root_temp]
        
        log_content = None
        
        for tf in temp_folders:
            log_path = tf / f"{job_id}_confidence_log.md"
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                logger.info(f"Found confidence log at: {log_path}")
                break
        
        if not log_content:
            return jsonify({
                'job_id': job_id,
                'error': '置信度日志未找到',
                'message': '该任务的置信度日志文件不存在，可能任务尚未完成处理'
            }), 404
        
        return jsonify({
            'job_id': job_id,
            'confidence_log': log_content,
            'format': 'markdown'
        })
        
    except Exception as e:
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_confidence_log',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/confidence-log'
            }
        )
        return jsonify(response_data), status_code


@api_bp.route('/convert/<job_id>/original-file', methods=['GET', 'HEAD'])
def get_original_file(job_id):
    """
    下载或获取原始上传的文件（PDF或图片）
    支持 HEAD 请求用于检测文件类型
    查询参数 download=true 时作为附件下载，否则直接返回内容
    """
    from flask import send_file
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        temp_folder = current_app.config['TEMP_FOLDER']
        upload_folder = current_app.config['UPLOAD_FOLDER']
        root_temp = Path('temp')
        root_uploads = Path('uploads')
        
        # 是否作为附件下载
        as_download = request.args.get('download', 'false').lower() == 'true'
        
        # 首先检查 temp 目录中的原始 PDF 缓存
        for tf in [temp_folder, root_temp]:
            pdf_path = tf / f"{job_id}_original.pdf"
            if pdf_path.exists():
                logger.info(f"Serving original PDF from temp: {pdf_path}")
                return send_file(
                    str(pdf_path.resolve()),
                    mimetype='application/pdf',
                    as_attachment=as_download,
                    download_name=f"{job_id}_original.pdf" if as_download else None
                )
        
        # 检查 uploads 目录
        for uf in [upload_folder, root_uploads]:
            for ext in ['pdf', 'png', 'jpg', 'jpeg']:
                file_path = uf / f"{job_id}.{ext}"
                if file_path.exists():
                    mimetype = {
                        'pdf': 'application/pdf',
                        'png': 'image/png',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg'
                    }.get(ext, 'application/octet-stream')
                    logger.info(f"Serving original file from uploads: {file_path}")
                    return send_file(
                        str(file_path.resolve()),
                        mimetype=mimetype,
                        as_attachment=as_download,
                        download_name=f"{job_id}_original.{ext}" if as_download else None
                    )
        
        return jsonify({
            'job_id': job_id,
            'error': '原始文件未找到',
            'message': '该任务的原始文件不存在'
        }), 404
        
    except Exception as e:
        response_data, status_code = error_handler.handle_error(
            e,
            context={
                'operation': 'get_original_file',
                'job_id': job_id,
                'endpoint': f'/convert/{job_id}/original-file'
            }
        )
        return jsonify(response_data), status_code


# ============================================================
# Job Cache API - 任务缓存相关端点
# ============================================================

@api_bp.route('/jobs/history', methods=['GET'])
def get_job_history():
    """
    获取历史任务列表
    
    用于前端页面加载时显示可恢复的历史任务
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        cache = get_job_cache()
        if cache is None:
            # 尝试初始化
            temp_folder = current_app.config['TEMP_FOLDER']
            cache = init_job_cache(temp_folder)
        
        limit = request.args.get('limit', type=int, default=20)
        jobs = cache.get_all_jobs(limit=limit)
        
        return jsonify({
            'success': True,
            'jobs': [
                {
                    'job_id': job.job_id,
                    'filename': job.filename,
                    'created_at': job.created_at,
                    'created_at_str': _format_timestamp(job.created_at),
                    'processing_time': round(job.processing_time, 2),
                    'status': job.status,
                    'confidence_score': job.confidence_score,
                    'block_count': job.block_count,
                    'has_tables': job.has_tables,
                    'document_type_id': job.document_type_id
                }
                for job in jobs
            ],
            'count': len(jobs)
        })
    except Exception as e:
        logger.error(f"Failed to get job history: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'jobs': []
        }), 500


@api_bp.route('/jobs/latest', methods=['GET'])
def get_latest_job():
    """
    获取最新的任务
    
    用于前端页面加载时自动恢复上次的识别结果
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        cache = get_job_cache()
        if cache is None:
            temp_folder = current_app.config['TEMP_FOLDER']
            cache = init_job_cache(temp_folder)
        
        job = cache.get_latest_job()
        
        if job is None:
            return jsonify({
                'success': True,
                'has_job': False,
                'job': None
            })
        
        return jsonify({
            'success': True,
            'has_job': True,
            'job': {
                'job_id': job.job_id,
                'filename': job.filename,
                'created_at': job.created_at,
                'created_at_str': _format_timestamp(job.created_at),
                'processing_time': round(job.processing_time, 2),
                'status': job.status,
                'confidence_score': job.confidence_score,
                'block_count': job.block_count,
                'has_tables': job.has_tables,
                'document_type_id': job.document_type_id
            }
        })
    except Exception as e:
        logger.error(f"Failed to get latest job: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'has_job': False
        }), 500


@api_bp.route('/jobs/<job_id>/cached-result', methods=['GET'])
def get_cached_result(job_id):
    """
    获取缓存的识别结果
    
    返回与 /api/convert/{job_id}/result 相同格式的数据
    用于前端直接加载历史结果，无需重新处理
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        cache = get_job_cache()
        if cache is None:
            temp_folder = current_app.config['TEMP_FOLDER']
            cache = init_job_cache(temp_folder)
        
        result = cache.load_cached_result(job_id)
        
        if result is None:
            return jsonify({
                'success': False,
                'error': '缓存结果不存在或文件已删除',
                'job_id': job_id
            }), 404
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get cached result for {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'job_id': job_id
        }), 500


@api_bp.route('/jobs/<job_id>', methods=['DELETE'])
def delete_cached_job(job_id):
    """
    删除缓存的任务
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        cache = get_job_cache()
        if cache is None:
            return jsonify({
                'success': False,
                'error': '缓存服务未初始化'
            }), 500
        
        deleted = cache.delete_job(job_id)
        
        return jsonify({
            'success': deleted,
            'job_id': job_id,
            'message': '任务已删除' if deleted else '任务不存在'
        })
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _format_timestamp(ts: float) -> str:
    """格式化时间戳为可读字符串"""
    from datetime import datetime
    dt = datetime.fromtimestamp(ts)
    return dt.strftime('%Y-%m-%d %H:%M:%S')
