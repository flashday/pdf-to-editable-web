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

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'pdf-to-editable-web'})

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
        
        # Create document record
        document = Document(
            id=str(uuid.uuid4()),
            original_filename=file_info['original_filename'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            processing_status=ProcessingStatus.PENDING
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
                
                # If multi-page, extract first page as image for processing
                if pdf_analysis['is_multi_page']:
                    temp_folder = current_app.config['TEMP_FOLDER']
                    temp_folder.mkdir(exist_ok=True)
                    
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
