from flask import Flask, request, send_file
from docx2pdf import convert
import tempfile, os

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_docx():
    file = request.files['file']
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, file.filename)
        pdf_path = docx_path.replace('.docx', '.pdf')
        file.save(docx_path)
        convert(docx_path, pdf_path)
        return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run()
