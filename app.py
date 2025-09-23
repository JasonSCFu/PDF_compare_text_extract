from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import difflib


app = Flask(__name__)
app.secret_key = 'pdf_comparison_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


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
        
        def normalize_whitespace(text):
            # Remove backspace characters and normalize all whitespace (spaces, tabs, newlines, etc.)
            import re
            text_no_backspace = text.replace('\b', '').replace('\x08', '')
            # Remove text surrounded by slashes before normalization (global replacement)
            text_no_slash = re.sub(r'/[^/]*/', '', text_no_backspace, flags=re.DOTALL)
            # Replace all whitespace sequences (spaces, tabs, newlines, etc.) with a single space
            # and strip leading/trailing whitespace
            normalized = re.sub(r'\s+', ' ', text_no_slash).strip()
            return normalized
        

        def highlight_text_diff(a, b, color):
            # Normalize whitespace in input strings
            a_normalized = normalize_whitespace(a)
            b_normalized = normalize_whitespace(b)

            # Split into words for comparison
            a_words = a_normalized.split()
            b_words = b_normalized.split()

            # Create a matcher that ignores whitespace
            matcher = difflib.SequenceMatcher(lambda x: x == ' ', a_words, b_words, autojunk=False)

            # For the original text (to preserve formatting in display), also remove slash content
            import re
            a_clean = re.sub(r'/[^/]*/', '', a.replace('\b', '').replace('\x08', ''), flags=re.DOTALL)
            b_clean = re.sub(r'/[^/]*/', '', b.replace('\b', '').replace('\x08', ''), flags=re.DOTALL)
            a_original = a_clean.split()
            b_original = b_clean.split()
            
            result = []
            
            # Process each opcode from the matcher
            for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
                if opcode == 'equal':
                    # For equal parts, use the original text (not normalized)
                    words = a_original[i1:i2] if color == 'red' else b_original[j1:j2]
                    result.extend(words)
                elif opcode == 'delete' and color == 'red':
                    # Highlight deletions in red
                    for word in a_original[i1:i2]:
                        result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
                elif opcode == 'insert' and color == 'green':
                    # Highlight insertions in green
                    for word in b_original[j1:j2]:
                        result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
                elif opcode == 'replace':
                    if color == 'red':
                        for word in a_original[i1:i2]:
                            result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
                    elif color == 'green':
                        for word in b_original[j1:j2]:
                            result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
            
            # Join with a single space to ensure consistent spacing in the output
            return ' '.join(result)

        # Instead of line-by-line comparison, compare entire texts as single blocks
        # This allows multi-line sentences to be compared properly
        h1 = highlight_text_diff(text1, text2, 'red')
        h2 = highlight_text_diff(text1, text2, 'green')
        has_diff = (h1 != text1 or h2 != text2)

        # Prepare the comparison result HTML
        highlighted1_html = h1
        highlighted2_html = h2
        
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
                <button type="button" class="btn btn-primary" id="next-comparison-btn">New Comparison</button>
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
    
    def normalize_text_for_comparison(text):
        # Remove backspace characters and normalize all whitespace for comparison
        import re
        text_no_backspace = text.replace('\b', '').replace('\x08', '')
        # Remove text surrounded by slashes before normalization (global replacement)
        text_no_slash = re.sub(r'/[^/]*/', '', text_no_backspace, flags=re.DOTALL)
        # Replace all whitespace sequences (spaces, tabs, newlines, etc.) with a single space
        # and strip leading/trailing whitespace
        normalized = re.sub(r'\s+', ' ', text_no_slash).strip()
        return normalized
    
    
    def highlight_text_diff(a, b, color):
        # Normalize text for comparison
        a_normalized = normalize_text_for_comparison(a)
        b_normalized = normalize_text_for_comparison(b)
        matcher = difflib.SequenceMatcher(None, a_normalized.split(), b_normalized.split())

        # For the original text (to preserve formatting in display), also remove slash content
        import re
        a_clean = re.sub(r'/[^/]*/', '', a.replace('\b', '').replace('\x08', ''), flags=re.DOTALL)
        b_clean = re.sub(r'/[^/]*/', '', b.replace('\b', '').replace('\x08', ''), flags=re.DOTALL)

        result = []
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == 'equal':
                # For 'equal' opcode, show the words from the cleaned text being processed
                words = a_clean.split()[i1:i2] if color == 'red' else b_clean.split()[j1:j2]
                result.extend(words)
            elif opcode == 'delete' and color == 'red':
                # Highlight deletions in red (for first text)
                for word in a_clean.split()[i1:i2]:
                    result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
            elif opcode == 'insert' and color == 'green':
                # Highlight insertions in green (for second text)
                for word in b_clean.split()[j1:j2]:
                    result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
            elif opcode == 'replace':
                if color == 'red':
                    # For first text, show replaced/deleted words in red
                    for word in a_clean.split()[i1:i2]:
                        result.append(f'<span style="background:#f8d7da;color:#721c24;">{word}</span>')
                elif color == 'green':
                    # For second text, show new words in green
                    for word in b_clean.split()[j1:j2]:
                        result.append(f'<span style="background:#d4edda;color:#155724;">{word}</span>')
        return ' '.join(result)

    # Instead of line-by-line comparison, compare entire texts as single blocks
    # This allows multi-line sentences to be compared properly
    h1 = highlight_text_diff(text1, text2, 'red')  # First text: highlight what's in text1 but not in text2
    h2 = highlight_text_diff(text1, text2, 'green')  # Second text: highlight what's in text2 but not in text1
    has_diff = (h1 != text1 or h2 != text2)

    # Prepare the comparison result HTML
    highlighted1_html = h1
    highlighted2_html = h2
    
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
