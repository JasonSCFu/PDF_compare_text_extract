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
            # Normalize whitespace in input strings for comparison
            a_normalized = normalize_whitespace(a)
            b_normalized = normalize_whitespace(b)

            # Split into words for comparison
            a_words = a_normalized.split()
            b_words = b_normalized.split()

            # Create a matcher that ignores whitespace
            matcher = difflib.SequenceMatcher(lambda x: x == ' ', a_words, b_words, autojunk=False)

            # For display, preserve original formatting but remove slash content
            import re
            text_to_display = a if color == 'red' else b
            display_text = re.sub(r'/[^/]*/', '', text_to_display.replace('\b', '').replace('\x08', ''), flags=re.DOTALL)

            # If texts are identical after normalization, return original formatting
            if a_normalized == b_normalized:
                return display_text

            # Split display text into words while preserving positions
            display_words = []
            word_positions = []
            current_pos = 0

            # Find word positions in the display text
            for word in re.finditer(r'\S+', display_text):
                display_words.append(word.group())
                word_positions.append((word.start(), word.end()))

            # Create result by reconstructing text with highlights
            result = []
            last_end = 0
            word_index = 0

            # Process each opcode from the matcher
            for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
                if opcode == 'equal':
                    # Add words without highlighting, preserving original spacing
                    target_words = i2 - i1 if color == 'red' else j2 - j1
                    for _ in range(target_words):
                        if word_index < len(word_positions):
                            start, end = word_positions[word_index]
                            # Add any whitespace/formatting before this word
                            result.append(display_text[last_end:start])
                            # Add the word itself
                            result.append(display_words[word_index])
                            last_end = end
                            word_index += 1

                elif (opcode == 'delete' and color == 'red') or (opcode == 'insert' and color == 'green'):
                    # Highlight differences
                    target_words = i2 - i1 if color == 'red' else j2 - j1
                    highlight_color = '#f8d7da' if color == 'red' else '#d4edda'
                    text_color = '#721c24' if color == 'red' else '#155724'

                    for _ in range(target_words):
                        if word_index < len(word_positions):
                            start, end = word_positions[word_index]
                            # Add any whitespace/formatting before this word
                            result.append(display_text[last_end:start])
                            # Add the highlighted word
                            result.append(f'<span style="background:{highlight_color};color:{text_color};">{display_words[word_index]}</span>')
                            last_end = end
                            word_index += 1

                elif opcode == 'replace':
                    if color == 'red':
                        # Highlight deleted words in red
                        for _ in range(i2 - i1):
                            if word_index < len(word_positions):
                                start, end = word_positions[word_index]
                                result.append(display_text[last_end:start])
                                result.append(f'<span style="background:#f8d7da;color:#721c24;">{display_words[word_index]}</span>')
                                last_end = end
                                word_index += 1
                    elif color == 'green':
                        # Highlight inserted words in green
                        for _ in range(j2 - j1):
                            if word_index < len(word_positions):
                                start, end = word_positions[word_index]
                                result.append(display_text[last_end:start])
                                result.append(f'<span style="background:#d4edda;color:#155724;">{display_words[word_index]}</span>')
                                last_end = end
                                word_index += 1

            # Add any remaining text after the last word
            if last_end < len(display_text):
                result.append(display_text[last_end:])

            return ''.join(result)

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

        # Split into words for comparison
        a_words = a_normalized.split()
        b_words = b_normalized.split()

        # Create a matcher that ignores whitespace
        matcher = difflib.SequenceMatcher(lambda x: x == ' ', a_words, b_words, autojunk=False)

        # For display, preserve original formatting but remove slash content
        import re
        text_to_display = a if color == 'red' else b
        display_text = re.sub(r'/[^/]*/', '', text_to_display.replace('\b', '').replace('\x08', ''), flags=re.DOTALL)

        # If texts are identical after normalization, return original formatting
        if a_normalized == b_normalized:
            return display_text

        # Split display text into words while preserving positions
        display_words = []
        word_positions = []

        # Find word positions in the display text
        for word in re.finditer(r'\S+', display_text):
            display_words.append(word.group())
            word_positions.append((word.start(), word.end()))

        # Create result by reconstructing text with highlights
        result = []
        last_end = 0
        word_index = 0

        # Process each opcode from the matcher
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == 'equal':
                # Add words without highlighting, preserving original spacing
                target_words = i2 - i1 if color == 'red' else j2 - j1
                for _ in range(target_words):
                    if word_index < len(word_positions):
                        start, end = word_positions[word_index]
                        # Add any whitespace/formatting before this word
                        result.append(display_text[last_end:start])
                        # Add the word itself
                        result.append(display_words[word_index])
                        last_end = end
                        word_index += 1

            elif (opcode == 'delete' and color == 'red') or (opcode == 'insert' and color == 'green'):
                # Highlight differences
                target_words = i2 - i1 if color == 'red' else j2 - j1
                highlight_color = '#f8d7da' if color == 'red' else '#d4edda'
                text_color = '#721c24' if color == 'red' else '#155724'

                for _ in range(target_words):
                    if word_index < len(word_positions):
                        start, end = word_positions[word_index]
                        # Add any whitespace/formatting before this word
                        result.append(display_text[last_end:start])
                        # Add the highlighted word
                        result.append(f'<span style="background:{highlight_color};color:{text_color};">{display_words[word_index]}</span>')
                        last_end = end
                        word_index += 1

            elif opcode == 'replace':
                if color == 'red':
                    # Highlight deleted words in red
                    for _ in range(i2 - i1):
                        if word_index < len(word_positions):
                            start, end = word_positions[word_index]
                            result.append(display_text[last_end:start])
                            result.append(f'<span style="background:#f8d7da;color:#721c24;">{display_words[word_index]}</span>')
                            last_end = end
                            word_index += 1
                elif color == 'green':
                    # Highlight inserted words in green
                    for _ in range(j2 - j1):
                        if word_index < len(word_positions):
                            start, end = word_positions[word_index]
                            result.append(display_text[last_end:start])
                            result.append(f'<span style="background:#d4edda;color:#155724;">{display_words[word_index]}</span>')
                            last_end = end
                            word_index += 1

        # Add any remaining text after the last word
        if last_end < len(display_text):
            result.append(display_text[last_end:])

        return ''.join(result)

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
