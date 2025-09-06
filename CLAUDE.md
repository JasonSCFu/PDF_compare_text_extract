# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based PDF text comparison tool that provides both command-line and web interfaces. The application has evolved from PDF comparison to direct text comparison, with the current focus on web-based text comparison with real-time highlighting of differences.

## Architecture

### Core Components

- **pdf_compare.py**: Core comparison logic for PDF files with word-level highlighting and italic text detection. Contains the `compare_pdfs()` function and `is_italic_font()` helper.
- **app.py**: Flask web application providing a modern web interface for text comparison. Uses AJAX for real-time comparison without page reloads.
- **templates/**: HTML templates using Bootstrap 5 for responsive UI
  - `index.html`: Main interface with dual text input areas and AJAX comparison
  - `result.html`: Results display template (legacy, superseded by AJAX)
  - `compare.html`: Additional comparison template

### Key Features

- **Text Comparison**: Word-level difference highlighting with whitespace normalization
- **Web Interface**: Bootstrap-based responsive UI with AJAX functionality
- **PDF Processing**: Legacy PDF comparison using PyMuPDF with page-by-page analysis
- **Highlighting System**: 
  - Red: Content in first text but not second
  - Green: Content in second text but not first
  - Blue: Italic text (when specified)

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or with pip3
pip3 install -r requirements.txt
```

### Running the Application
```bash
# Start web server (development mode)
python3 app.py

# Access at http://127.0.0.1:5000

# Command line PDF comparison (legacy)
python3 pdf_compare.py path_to_first.pdf path_to_second.pdf
```

### Dependencies
- Python 3.x (tested with 3.12.3)
- PyMuPDF 1.23.8 (PDF processing)
- PyPDF2 3.0.1 (PDF manipulation)
- Flask 2.0.1 (web framework)
- Bootstrap 5.3.0 (frontend styling via CDN)

## Code Architecture Notes

### Text Comparison Logic
The application uses a sophisticated word-level comparison system:

1. **Normalization**: `normalize_whitespace()` in app.py:53-55 handles whitespace differences
2. **Word-level Matching**: Uses `difflib.SequenceMatcher` for precise difference detection
3. **Dual Processing**: Processes both texts simultaneously to highlight additions and deletions

### AJAX Implementation
The web interface (app.py:48-150) handles both AJAX and traditional form submissions:
- AJAX requests return JSON with HTML content
- Traditional requests render templates directly
- Real-time comparison without page reloads

### File Upload Structure
- `uploads/` directory stores temporary PDF files with timestamp prefixes
- File naming convention: `YYYYMMDD_HHMMSS_N_originalname.pdf`
- 16MB file size limit configured

## Current State
The project is on the `enhance-remove-back-space` branch and has transitioned from PDF upload functionality to direct text comparison. The web interface now focuses on text input rather than file uploads, with the PDF comparison functionality remaining available via command line.