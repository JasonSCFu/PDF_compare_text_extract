from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import os
import fitz
from datetime import datetime
from werkzeug.utils import secure_filename
import shutil
import sys
import tempfile

# Import the compare_pdfs function from pdf_compare.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pdf_compare import compare_pdfs, is_italic_font

app = Flask(__name__)
app.secret_key = 'pdf_comparison_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['RESULT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def get_pdf_page_count(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        print(f"Error getting page count: {e}")
        return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    # Get pasted texts from the form
    text1 = request.form.get('text1', '').strip()
    text2 = request.form.get('text2', '').strip()

    if not text1 or not text2:
        flash('Both text inputs are required', 'error')
        return redirect(request.url)

    # Store texts in session (or pass directly)
    session_data = {
        'text1': text1,
        'text2': text2,
        'page_count1': 1,
        'page_count2': 1
    }

    return render_template('compare.html', 
                          file1='Pasted Text 1',
                          file2='Pasted Text 2',
                          page_count1=1,
                          page_count2=1,
                          session_data=session_data)

@app.route('/compare', methods=['POST'])
def compare():
    # Get pasted texts
    text1 = request.form.get('text1', '').strip()
    text2 = request.form.get('text2', '').strip()

    # Get italic words to highlight (if specified)
    italic_words_input = request.form.get('italic_words', '').strip()
    specific_italic_words = None
    if italic_words_input:
        specific_italic_words = [word.strip() for word in italic_words_input.split(',') if word.strip()]

    if not text1 or not text2:
        flash('Both text inputs are required', 'error')
        return redirect(url_for('index'))

    # --- Simple text comparison logic ---
    # For demonstration, show differences using difflib
    import difflib
    diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
    diff_html = ''
    for line in diff:
        if line.startswith('- '):
            diff_html += f'<div style="background:#f8d7da;color:#721c24;">{line[2:]}</div>'  # Red: only in text1
        elif line.startswith('+ '):
            diff_html += f'<div style="background:#d4edda;color:#155724;">{line[2:]}</div>'  # Green: only in text2
        elif line.startswith('? '):
            continue  # skip markers
        else:
            diff_html += f'<div>{line[2:]}</div>'

    # Optionally highlight specific italic words (blue)
    if specific_italic_words:
        import re
        for word in specific_italic_words:
            diff_html = re.sub(rf'\b({re.escape(word)})\b', r'<span style="color:#0d6efd;font-style:italic;">\1</span>', diff_html, flags=re.IGNORECASE)

    return render_template('result.html', 
                           comparison_result=diff_html, 
                           specific_words=', '.join(specific_italic_words) if specific_italic_words else None)

@app.route('/results/<filename>')
def view_result(filename):
    result_path = os.path.join(app.config['RESULT_FOLDER'], filename)
    if not os.path.exists(result_path):
        flash('Result file not found', 'error')
        return redirect(url_for('index'))
    
    return send_file(result_path, as_attachment=False)

@app.route('/download/<filename>')
def download_result(filename):
    result_path = os.path.join(app.config['RESULT_FOLDER'], filename)
    if not os.path.exists(result_path):
        flash('Result file not found', 'error')
        return redirect(url_for('index'))
    
    return send_file(result_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
