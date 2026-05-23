from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile, os, subprocess, glob, shutil, io
import fitz  # PyMuPDF
from pdf2docx import Converter

app = Flask(__name__)
CORS(app)

MAX_FILE_SIZE = 20 * 1024 * 1024
SIMPLE_PAGE_THRESHOLD = 5
SIMPLE_IMAGE_THRESHOLD = 2

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'PDF Converter API is running'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/convert', methods=['POST'])
def convert_docx():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, file.filename)
        file.save(docx_path)
        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to', 'pdf',
            '--outdir', tmp, docx_path
        ], check=True)
        pdf_path = os.path.join(tmp, os.path.splitext(file.filename)[0] + '.pdf')
        return send_file(pdf_path, as_attachment=True,
                         download_name=file.filename.replace('.docx', '.pdf'))

def analyze_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    page_count = doc.page_count
    image_count = 0
    table_count = 0
    has_text = False
    multi_column = False

    for page in doc:
        text = page.get_text().strip()
        if text:
            has_text = True

        image_count += len(page.get_images(full=True))

        blocks = [b for b in page.get_text('blocks') if b[4] == 0 and b[6].strip()]
        if len(blocks) > 1:
            left_positions = set(int(b[0] // (page.rect.width / 3)) for b in blocks)
            if len(left_positions) >= 2:
                multi_column = True

        drawings = page.get_drawings()
        horizontal_lines = 0
        vertical_lines = 0
        rect_count = 0
        for item in drawings:
            if item['type'] == 'line':
                x0, y0 = item['from']
                x1, y1 = item['to']
                if abs(y1 - y0) < 1:
                    horizontal_lines += 1
                elif abs(x1 - x0) < 1:
                    vertical_lines += 1
            elif item['type'] == 'rect':
                rect_count += 1

        if horizontal_lines >= 3 and vertical_lines >= 3:
            table_count += 1
        elif rect_count >= 3:
            table_count += 1

    doc.close()
    return {
        'page_count': page_count,
        'image_count': image_count,
        'has_text': has_text,
        'table_count': table_count,
        'multi_column': multi_column
    }


def open_pdf_metadata(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        if doc.needs_pass:
            doc.close()
            return 'password'
        doc.close()
        return 'ok'
    except RuntimeError as exc:
        message = str(exc).lower()
        if 'password' in message or 'encrypted' in message or 'need a password' in message:
            return 'password'
        return 'corrupted'
    except Exception:
        return 'corrupted'

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 20MB'}), 413

    metadata_status = open_pdf_metadata(file_bytes)
    if metadata_status == 'password':
        return jsonify({'error': 'This PDF is password protected'}), 400
    if metadata_status == 'corrupted':
        return jsonify({'error': 'File appears to be corrupted'}), 400

    analysis = analyze_pdf(file_bytes)
    if not analysis['has_text']:
        return jsonify({'error': 'This document appears to be a scanned PDF without extractable text'}), 400

    is_complex = (
        analysis['page_count'] > SIMPLE_PAGE_THRESHOLD or
        analysis['image_count'] > SIMPLE_IMAGE_THRESHOLD or
        analysis['table_count'] > 0 or
        analysis['multi_column']
    )

    if is_complex:
        return jsonify({
            'warning': True,
            'complexity': 'high',
            'message': 'This document has complex formatting (images, tables, multiple columns). Conversion may lose some formatting. Do you want to proceed?',
            'image_count': analysis['image_count'],
            'page_count': analysis['page_count']
        }), 200

    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, 'input.pdf')
        output_path = os.path.join(tmp, file.filename.replace('.pdf', '.docx'))
        with open(input_path, 'wb') as f:
            f.write(file_bytes)

        converter = Converter(input_path)
        converter.convert(output_path, start=0, end=None)
        converter.close()

        with open(output_path, 'rb') as f:
            file_data = io.BytesIO(f.read())

    file_data.seek(0)
    return send_file(
        file_data,
        as_attachment=True,
        download_name=file.filename.replace('.pdf', '.docx'),
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/pdf-to-word/force', methods=['POST'])
def pdf_to_word_force():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    confirmed = request.args.get('confirmed', 'false').lower() == 'true'
    if not confirmed:
        return jsonify({'error': 'Conversion not confirmed. Set confirmed=true to proceed.'}), 400

    file = request.files['file']
    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 20MB'}), 413

    metadata_status = open_pdf_metadata(file_bytes)
    if metadata_status == 'password':
        return jsonify({'error': 'This PDF is password protected'}), 400
    if metadata_status == 'corrupted':
        return jsonify({'error': 'File appears to be corrupted'}), 400

    analysis = analyze_pdf(file_bytes)
    if not analysis['has_text']:
        return jsonify({'error': 'This document appears to be a scanned PDF without extractable text'}), 400

    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, 'input.pdf')
        output_path = os.path.join(tmp, file.filename.replace('.pdf', '.docx'))
        with open(input_path, 'wb') as f:
            f.write(file_bytes)

        converter = Converter(input_path)
        converter.convert(output_path, start=0, end=None)
        converter.close()

        with open(output_path, 'rb') as f:
            file_data = io.BytesIO(f.read())

    file_data.seek(0)
    return send_file(
        file_data,
        as_attachment=True,
        download_name=file.filename.replace('.pdf', '.docx'),
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

if __name__ == '__main__':
    app.run()
