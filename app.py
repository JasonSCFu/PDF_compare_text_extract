from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import fitz
from werkzeug.utils import secure_filename
import difflib
import tempfile

# Import the compare_pdfs function from pdf_compare.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pdf_compare import compare_pdfs, is_italic_font

app = Flask(__name__)
app.secret_key = 'pdf_comparison_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

@app.route('/', methods=['POST'])
def upload_files():
    # Get pasted texts from the form
    text1 = request.form.get('text1', '').strip()
    text2 = request.form.get('text2', '').strip()

    if not text1 or not text2:
        flash('Both text inputs are required', 'error')
        return redirect(request.url)

    # For AJAX requests, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Import the highlight_text_diff function
        import difflib
        
        def highlight_text_diff(a, b, color):
            matcher = difflib.SequenceMatcher(None, a.split(), b.split())
            result = []
            for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
                if opcode == 'equal':
                    words = a.split()[i1:i2] if color == 'red' else b.split()[j1:j2]
                    result.extend(words)
                elif opcode == 'delete' and color == 'red':
                    for word in a.split()[i1:i2]:
                        result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
                elif opcode == 'insert' and color == 'green':
                    for word in b.split()[j1:j2]:
                        result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
                elif opcode == 'replace':
                    if color == 'red':
                        for word in a.split()[i1:i2]:
                            result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
                    elif color == 'green':
                        for word in b.split()[j1:j2]:
                            result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
            return ' '.join(result)

        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        max_lines = max(len(lines1), len(lines2))
        highlighted1 = []
        highlighted2 = []
        has_diff = False
        
        for i in range(max_lines):
            l1 = lines1[i] if i < len(lines1) else ''
            l2 = lines2[i] if i < len(lines2) else ''
            h1 = highlight_text_diff(l1, l2, 'red')
            h2 = highlight_text_diff(l1, l2, 'green')
            if h1 != l1 or h2 != l2:
                has_diff = True
            highlighted1.append(h1)
            highlighted2.append(h2)

        # Prepare the comparison result HTML
        highlighted1_html = '\n'.join(highlighted1)
        highlighted2_html = '\n'.join(highlighted2)
        
        compare_html = f'''<div class="comparison-result">
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-primary text-white">First Text (with highlights)</div>
                        <div class="card-body" style="white-space: pre-wrap;">{highlighted1_html}</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-success text-white">Second Text (with highlights)</div>
                        <div class="card-body" style="white-space: pre-wrap;">{highlighted2_html}</div>
                    </div>
                </div>
            </div>
            <div class="text-center mt-4">
                <a href="/" class="btn btn-secondary">New Comparison</a>
            </div>
        </div>'''
        
        if not has_diff:
            return {
                'status': 'success',
                'html': '<div class="alert alert-info text-center">No differences found.</div>'
            }, 200, {'Content-Type': 'application/json'}
        
        return {
            'status': 'success',
            'html': compare_html
        }, 200, {'Content-Type': 'application/json'}
    
    # For non-AJAX requests, render the result directly
    return compare(text1, text2)

@app.route('/compare', methods=['POST'])
def compare():
    # Get pasted texts
    text1 = request.form.get('text1', '').strip()
    text2 = request.form.get('text2', '').strip()

    if not text1 or not text2:
        flash('Both text inputs are required', 'error')
        return redirect(url_for('index'))

    # --- Highlight differences in the original texts ---
    import difflib
    def highlight_text_diff(a, b, color):
        matcher = difflib.SequenceMatcher(None, a.split(), b.split())
        result = []
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == 'equal':
                # For 'equal' opcode, show the words from the text being processed
                words = a.split()[i1:i2] if color == 'red' else b.split()[j1:j2]
                result.extend(words)
            elif opcode == 'delete' and color == 'red':
                # Highlight deletions in red (for first text)
                for word in a.split()[i1:i2]:
                    result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
            elif opcode == 'insert' and color == 'green':
                # Highlight insertions in green (for second text)
                for word in b.split()[j1:j2]:
                    result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
            elif opcode == 'replace':
                if color == 'red':
                    # For first text, show replaced/deleted words in red
                    for word in a.split()[i1:i2]:
                        result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
                elif color == 'green':
                    # For second text, show new words in green
                    for word in b.split()[j1:j2]:
                        result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
        return ' '.join(result)

    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    max_lines = max(len(lines1), len(lines2))
    highlighted1 = []
    highlighted2 = []
    has_diff = False
    for i in range(max_lines):
        l1 = lines1[i] if i < len(lines1) else ''
        l2 = lines2[i] if i < len(lines2) else ''
        h1 = highlight_text_diff(l1, l2, 'red')  # First text: highlight what's in text1 but not in text2
        h2 = highlight_text_diff(l1, l2, 'green')  # Second text: highlight what's in text2 but not in text1
        if h1 != l1 or h2 != l2:
            has_diff = True
        highlighted1.append(h1)
        highlighted2.append(h2)

    # Prepare the comparison result HTML
    highlighted1_html = '\n'.join(highlighted1)
    highlighted2_html = '\n'.join(highlighted2)
    
    compare_html = f'''<div class="comparison-result">
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">First Text (with highlights)</div>
                    <div class="card-body" style="white-space: pre-wrap;">{highlighted1_html}</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-success text-white">Second Text (with highlights)</div>
                    <div class="card-body" style="white-space: pre-wrap;">{highlighted2_html}</div>
                </div>
            </div>
        </div>
        <div class="text-center mt-4">
            <a href="/" class="btn btn-secondary">New Comparison</a>
        </div>
    </div>'''
    
    # If AJAX request, return the comparison result as JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if not has_diff:
            return {
                'status': 'success',
                'html': '<div class="alert alert-info text-center">No differences found.</div>'
            }, 200, {'Content-Type': 'application/json'}
        
        return {
            'status': 'success',
            'html': compare_html
        }, 200, {'Content-Type': 'application/json'}

    # For non-AJAX, render the same in result.html
    return render_template('result.html', comparison_result=compare_html)


if __name__ == '__main__':
    app.run(debug=True)
