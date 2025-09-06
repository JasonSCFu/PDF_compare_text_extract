from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import os
import sys
import fitz
from werkzeug.utils import secure_filename
import difflib
import tempfile
from datetime import datetime
import sys

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
        
        def normalize_whitespace(text):
            # Remove backspace characters and normalize all whitespace (spaces, tabs, newlines, etc.)
            import re
            text_no_backspace = text.replace('\b', '').replace('\x08', '')
            # Replace all whitespace sequences (spaces, tabs, newlines, etc.) with a single space
            # and strip leading/trailing whitespace
            normalized = re.sub(r'\s+', ' ', text_no_backspace).strip()
            return normalized
        
        def filter_empty_lines(lines):
            # Remove empty lines and lines with only whitespace
            import re
            filtered_lines = []
            for line in lines:
                # Remove backspace characters first, then check if line has content
                cleaned_line = line.replace('\b', '').replace('\x08', '')
                if re.sub(r'\s+', '', cleaned_line):  # If line has non-whitespace content
                    filtered_lines.append(line)
            return filtered_lines

        def highlight_text_diff(a, b, color):
            # Normalize whitespace in input strings
            a_normalized = normalize_whitespace(a)
            b_normalized = normalize_whitespace(b)
            
            # Split into words for comparison
            a_words = a_normalized.split()
            b_words = b_normalized.split()
            
            # Create a matcher that ignores whitespace
            matcher = difflib.SequenceMatcher(lambda x: x == ' ', a_words, b_words, autojunk=False)
            
            # For the original text (to preserve formatting in display)
            a_original = a.split()
            b_original = b.split()
            
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

        lines1 = filter_empty_lines(text1.splitlines())
        lines2 = filter_empty_lines(text2.splitlines())
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
                <button type="button" class="btn btn-success me-2" id="save-comparison-btn">Save This Comparison</button>
                <button type="button" class="btn btn-primary me-2" id="next-comparison-btn">Next Comparison</button>
                <button type="button" class="btn btn-info me-2" id="view-saved-btn">View Saved (<span id="saved-count">0</span>)</button>
                <button type="button" class="btn btn-warning" id="generate-pdf-btn" style="display: none;">Generate PDF</button>
            </div>
            <div id="saved-comparisons-info" class="mt-3" style="display: none;">
                <div class="alert alert-info">
                    <strong>Saved Comparisons: <span id="total-saved">0</span></strong>
                    <button type="button" class="btn btn-sm btn-danger ms-2" id="clear-all-btn">Clear All</button>
                </div>
            </div>
        </div>'''
        
        if not has_diff:
            return {
                'status': 'success',
                'html': '<div class="alert alert-info text-center">No differences found.</div>',
                'has_differences': False,
                'comparison_data': None
            }, 200, {'Content-Type': 'application/json'}
        
        # Store comparison data for potential saving
        comparison_data = {
            'text1': text1,
            'text2': text2,
            'highlighted1': highlighted1_html,
            'highlighted2': highlighted2_html,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return {
            'status': 'success',
            'html': compare_html,
            'has_differences': True,
            'comparison_data': comparison_data
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
        # Replace all whitespace sequences (spaces, tabs, newlines, etc.) with a single space
        # and strip leading/trailing whitespace
        normalized = re.sub(r'\s+', ' ', text_no_backspace).strip()
        return normalized
    
    def filter_empty_lines(lines):
        # Remove empty lines and lines with only whitespace
        import re
        filtered_lines = []
        for line in lines:
            # Remove backspace characters first, then check if line has content
            cleaned_line = line.replace('\b', '').replace('\x08', '')
            if re.sub(r'\s+', '', cleaned_line):  # If line has non-whitespace content
                filtered_lines.append(line)
        return filtered_lines
    
    def highlight_text_diff(a, b, color):
        # Normalize text for comparison
        a_normalized = normalize_text_for_comparison(a)
        b_normalized = normalize_text_for_comparison(b)
        matcher = difflib.SequenceMatcher(None, a_normalized.split(), b_normalized.split())
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

    lines1 = filter_empty_lines(text1.splitlines())
    lines2 = filter_empty_lines(text2.splitlines())
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

@app.route('/save_comparison', methods=['POST'])
def save_comparison():
    """Save a comparison result to the session for later PDF generation."""
    try:
        data = request.get_json()
        comparison_data = data.get('comparison_data')
        
        if not comparison_data:
            return jsonify({'status': 'error', 'message': 'No comparison data provided'}), 400
        
        # Initialize session comparisons if not exists
        if 'comparisons' not in session:
            session['comparisons'] = []
        
        # Add comparison to session
        session['comparisons'].append(comparison_data)
        session.modified = True
        
        return jsonify({
            'status': 'success',
            'message': f'Comparison saved! Total saved: {len(session["comparisons"])}',
            'total_comparisons': len(session['comparisons'])
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_saved_comparisons')
def get_saved_comparisons():
    """Get the count and list of saved comparisons."""
    comparisons = session.get('comparisons', [])
    return jsonify({
        'total_comparisons': len(comparisons),
        'comparisons': [{'timestamp': comp['timestamp'], 'index': i} for i, comp in enumerate(comparisons)]
    })

@app.route('/clear_comparisons', methods=['POST'])
def clear_comparisons():
    """Clear all saved comparisons from the session."""
    session.pop('comparisons', None)
    session.modified = True
    return jsonify({'status': 'success', 'message': 'All comparisons cleared'})

def parse_html_with_highlights(html_text):
    """Parse HTML to extract text with highlight information for PDF rendering."""
    import re
    
    if not html_text or not isinstance(html_text, str):
        return [], ""
    
    try:
        # Find all highlighted spans and their positions
        highlight_info = []
        
        # Find removed (red) highlights
        for match in re.finditer(r'<span[^>]*background[^>]*#f8d7da[^>]*>(.*?)</span>', html_text, flags=re.DOTALL):
            highlight_info.append({
                'text': match.group(1),
                'start': match.start(),
                'end': match.end(),
                'type': 'removed',
                'color': (1, 0.85, 0.85)  # Light red background
            })
        
        # Find added (green) highlights
        for match in re.finditer(r'<span[^>]*background[^>]*#d4edda[^>]*>(.*?)</span>', html_text, flags=re.DOTALL):
            highlight_info.append({
                'text': match.group(1),
                'start': match.start(),
                'end': match.end(),
                'type': 'added',
                'color': (0.83, 0.93, 0.85)  # Light green background
            })
        
        # Sort highlights by position
        highlight_info.sort(key=lambda x: x['start'])
        
        # Extract clean plain text
        plain_text = re.sub(r'<span[^>]*background[^>]*#f8d7da[^>]*>(.*?)</span>', r'\1', html_text, flags=re.DOTALL)
        plain_text = re.sub(r'<span[^>]*background[^>]*#d4edda[^>]*>(.*?)</span>', r'\1', plain_text, flags=re.DOTALL)
        plain_text = re.sub(r'<[^>]+>', '', plain_text)
        
        # Clean up whitespace
        plain_text = re.sub(r'[ \t]+', ' ', plain_text)
        plain_text = re.sub(r'\n\s*\n', '\n', plain_text)
        
        # Remove problematic characters
        plain_text = ''.join(c for c in plain_text if ord(c) < 65536 and (c.isprintable() or c in '\n\r\t'))
        
        # Recalculate highlight positions in the cleaned text
        cleaned_highlights = []
        for highlight in highlight_info:
            # Find the highlight text in the cleaned plain text
            highlight_text = highlight['text'].strip()
            if highlight_text:
                pos = plain_text.find(highlight_text)
                if pos != -1:
                    cleaned_highlights.append({
                        'text': highlight_text,
                        'start_pos': pos,
                        'end_pos': pos + len(highlight_text),
                        'type': highlight['type'],
                        'color': highlight['color']
                    })
        
        return cleaned_highlights, plain_text.strip()
        
    except Exception as e:
        print(f"[DEBUG] Error parsing HTML highlights: {e}")
        # Fallback to plain text
        clean_text = re.sub(r'<[^>]+>', '', html_text) if html_text else ""
        return [], clean_text

def html_to_plain_text_with_highlights(html_text):
    """Legacy function - now just returns plain text for backward compatibility."""
    highlights, plain_text = parse_html_with_highlights(html_text)
    return plain_text

def add_highlighted_text_to_pdf(page, text, highlights, x, y, fontsize=10, line_height=12):
    """Add text with highlights to PDF page, returning the final y position."""
    if not text:
        return y
    
    try:
        # Split text into lines
        lines = text.split('\n')
        current_y = y
        
        for line_idx, line in enumerate(lines):
            if not line.strip():
                current_y += line_height
                continue
                
            # Find highlights that apply to this line
            line_start_pos = sum(len(lines[i]) + 1 for i in range(line_idx))  # +1 for newline
            line_end_pos = line_start_pos + len(line)
            
            # Get highlights for this line
            line_highlights = []
            for highlight in highlights:
                # Check if highlight overlaps with this line
                if (highlight['start_pos'] < line_end_pos and 
                    highlight['end_pos'] > line_start_pos):
                    # Calculate relative positions within the line
                    rel_start = max(0, highlight['start_pos'] - line_start_pos)
                    rel_end = min(len(line), highlight['end_pos'] - line_start_pos)
                    line_highlights.append({
                        'start': rel_start,
                        'end': rel_end,
                        'color': highlight['color'],
                        'type': highlight['type']
                    })
            
            # Sort highlights by start position
            line_highlights.sort(key=lambda h: h['start'])
            
            # Add the line with highlights
            if line_highlights:
                # Add text with highlights
                pos = 0
                for highlight in line_highlights:
                    # Add text before highlight (if any)
                    if highlight['start'] > pos:
                        before_text = line[pos:highlight['start']]
                        page.insert_text((x, current_y), before_text, fontsize=fontsize, color=(0, 0, 0))
                        # Calculate text width to position next part (approximate)
                        text_width = len(before_text) * fontsize * 0.6  # Rough character width estimation
                        x += text_width
                    
                    # Add highlighted text with background
                    highlight_text = line[highlight['start']:highlight['end']]
                    if highlight_text:
                        # Calculate highlight rectangle (approximate)
                        text_width = len(highlight_text) * fontsize * 0.6  # Rough character width estimation
                        highlight_rect = fitz.Rect(x, current_y - fontsize + 2, x + text_width, current_y + 3)
                        
                        # Add highlight background
                        page.draw_rect(highlight_rect, color=highlight['color'], fill=highlight['color'])
                        
                        # Add text on top of highlight
                        page.insert_text((x, current_y), highlight_text, fontsize=fontsize, color=(0, 0, 0))
                        x += text_width
                    
                    pos = highlight['end']
                
                # Add any remaining text after last highlight
                if pos < len(line):
                    remaining_text = line[pos:]
                    page.insert_text((x, current_y), remaining_text, fontsize=fontsize, color=(0, 0, 0))
            else:
                # No highlights, add plain text
                page.insert_text((x, current_y), line, fontsize=fontsize, color=(0, 0, 0))
            
            current_y += line_height
            x = 50  # Reset x position for next line
        
        return current_y
        
    except Exception as e:
        print(f"[DEBUG] Error adding highlighted text: {e}")
        # Fallback to plain text
        page.insert_text((x, y), text, fontsize=fontsize, color=(0, 0, 0))
        return y + len(text.split('\n')) * line_height

def generate_comparison_pdf():
    """Generate a PDF containing all saved comparisons."""
    try:
        print(f"[DEBUG] Starting PDF generation...", flush=True)
        print(f"[DEBUG] Session keys: {list(session.keys())}", flush=True)
        
        comparisons = session.get('comparisons', [])
        print(f"[DEBUG] Found {len(comparisons)} comparisons in session")
        
        if not comparisons:
            print("[DEBUG] No comparisons found in session")
            return None, "No comparisons to generate PDF"
        
        # Validate comparison data
        for i, comp in enumerate(comparisons):
            print(f"[DEBUG] Comparison {i+1}: keys = {list(comp.keys()) if comp else 'None'}")
            if not isinstance(comp, dict):
                return None, f"Invalid comparison data format at index {i}"
            required_keys = ['text1', 'text2', 'highlighted1', 'highlighted2', 'timestamp']
            for key in required_keys:
                if key not in comp:
                    return None, f"Missing required key '{key}' in comparison {i+1}"
        
        # Ensure upload directory exists
        upload_dir = app.config['UPLOAD_FOLDER']
        print(f"[DEBUG] Upload directory: {upload_dir}")
        
        if not os.path.exists(upload_dir):
            print(f"[DEBUG] Creating upload directory: {upload_dir}")
            os.makedirs(upload_dir, exist_ok=True)
        
        if not os.access(upload_dir, os.W_OK):
            return None, f"Upload directory is not writable: {upload_dir}"
        
        # Create output PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(upload_dir, f'combined_comparisons_{timestamp}.pdf')
        print(f"[DEBUG] Output PDF path: {output_path}")
        
        print("[DEBUG] Creating PyMuPDF document...")
        output_doc = fitz.open()
        
        for i, comp in enumerate(comparisons, 1):
            print(f"[DEBUG] Processing comparison {i}...")
            
            # Create a new page for each comparison
            page_width = 595  # A4 width in points
            page_height = 842  # A4 height in points
            print(f"[DEBUG] Creating new page {page_width}x{page_height}")
            new_page = output_doc.new_page(width=page_width, height=page_height)
            
            # Add title with standard font
            title_text = f"Comparison {i} - {comp['timestamp']}"
            print(f"[DEBUG] Adding title: {title_text}")
            new_page.insert_text((50, 50), title_text, fontsize=16, color=(0, 0, 0))
            
            # Parse HTML to extract text and highlight information
            print(f"[DEBUG] Parsing HTML with highlights...")
            try:
                highlights1, text1_plain = parse_html_with_highlights(comp.get('highlighted1', ''))
                highlights2, text2_plain = parse_html_with_highlights(comp.get('highlighted2', ''))
                print(f"[DEBUG] Text1: {len(text1_plain)} chars, {len(highlights1)} highlights")
                print(f"[DEBUG] Text2: {len(text2_plain)} chars, {len(highlights2)} highlights")
            except Exception as e:
                print(f"[DEBUG] Error in HTML parsing: {e}")
                # Fallback to original text without highlights
                highlights1, highlights2 = [], []
                text1_plain = comp.get('text1', '')
                text2_plain = comp.get('text2', '')
            
            # Vertical layout: First text on top, second text below
            y_pos = 100
            line_height = 12
            max_y = page_height - 50
            section_spacing = 30  # Space between sections
            
            # Add first text section
            new_page.insert_text((50, y_pos), "First Text:", fontsize=12, color=(0, 0, 1))
            y_pos += 20
            
            print(f"[DEBUG] Adding first text with highlights...")
            try:
                # Add highlighted text and get new y position
                y_pos = add_highlighted_text_to_pdf(new_page, text1_plain, highlights1, 50, y_pos, fontsize=10, line_height=line_height)
            except Exception as e:
                print(f"[DEBUG] Error adding highlighted first text: {e}")
                # Fallback to plain text
                lines1 = text1_plain.split('\n') if text1_plain else ['']
                for line in lines1:
                    if y_pos > max_y:
                        new_page = output_doc.new_page(width=page_width, height=page_height)
                        y_pos = 50
                    if line:
                        new_page.insert_text((50, y_pos), line, fontsize=10, color=(0, 0, 0))
                    y_pos += line_height
            
            # Add spacing between sections
            y_pos += section_spacing
            
            # Check if we need a new page for second text
            if y_pos > max_y - 100:  # Reserve space for second text header + some lines
                new_page = output_doc.new_page(width=page_width, height=page_height)
                y_pos = 50
            
            # Add second text section
            new_page.insert_text((50, y_pos), "Second Text:", fontsize=12, color=(0, 0.5, 0))
            y_pos += 20
            
            print(f"[DEBUG] Adding second text with highlights...")
            try:
                # Add highlighted text and get new y position
                y_pos = add_highlighted_text_to_pdf(new_page, text2_plain, highlights2, 50, y_pos, fontsize=10, line_height=line_height)
            except Exception as e:
                print(f"[DEBUG] Error adding highlighted second text: {e}")
                # Fallback to plain text
                lines2 = text2_plain.split('\n') if text2_plain else ['']
                for line in lines2:
                    if y_pos > max_y:
                        new_page = output_doc.new_page(width=page_width, height=page_height)
                        y_pos = 50
                    if line:
                        new_page.insert_text((50, y_pos), line, fontsize=10, color=(0, 0, 0))
                    y_pos += line_height
            
            # Add separator between comparisons
            if i < len(comparisons):
                try:
                    y_pos += 40  # More space between comparisons
                    if y_pos < max_y - 50:  # Only draw line if enough space available
                        new_page.draw_line((50, y_pos), (page_width - 50, y_pos), color=(0.5, 0.5, 0.5), width=2)
                        y_pos += 20
                    else:
                        # Start next comparison on a new page
                        print(f"[DEBUG] Starting new page for next comparison")
                except Exception as e:
                    print(f"[DEBUG] Error drawing separator: {e}")
        
        # Save the PDF
        print("[DEBUG] Saving PDF...")
        try:
            output_doc.save(output_path)
            print(f"[DEBUG] PDF saved successfully to: {output_path}")
            
            # Verify file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[DEBUG] PDF file size: {file_size} bytes")
                
                if file_size == 0:
                    return None, "Generated PDF file is empty"
            else:
                return None, "PDF file was not created"
                
        except Exception as save_error:
            print(f"[DEBUG] Error saving PDF: {save_error}")
            return None, f"Error saving PDF: {str(save_error)}"
        finally:
            try:
                output_doc.close()
                print("[DEBUG] PDF document closed")
            except Exception as close_error:
                print(f"[DEBUG] Error closing document: {close_error}")
        
        return output_path, None
        
    except Exception as e:
        error_msg = f"PDF generation failed: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        return None, error_msg

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Generate and initiate download of combined comparisons PDF."""
    try:
        pdf_path, error = generate_comparison_pdf()
        
        if error:
            return jsonify({'status': 'error', 'message': error}), 400
        
        if not pdf_path:
            return jsonify({'status': 'error', 'message': 'Failed to generate PDF'}), 500
        
        # Return the filename for download
        filename = os.path.basename(pdf_path)
        return jsonify({
            'status': 'success',
            'message': 'PDF generated successfully',
            'download_url': f'/download_pdf/{filename}',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    """Download the generated PDF file."""
    try:
        # Secure the filename to prevent directory traversal
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Send file for download
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
