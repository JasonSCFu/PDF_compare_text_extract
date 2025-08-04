# PDF Text Comparison Tool

A Python application for comparing text differences between PDF files with word-level highlighting and a web interface.

## Features

- **Word-level Difference Highlighting**: Highlights individual word differences between documents
- **Italic Text Detection**: Identifies and highlights italic text with customizable filtering
- **Web Interface**: User-friendly web application for uploading and comparing PDFs
- **Page Range Selection**: Compare specific pages or page ranges from each document
- **Visual Highlighting**: Color-coded differences (red for removed text, green for added text, blue for italic text)

## Requirements

- Python 3.x
- PyMuPDF (for PDF manipulation and text extraction)
- PyPDF2 (for PDF processing)
- Flask (for web interface)

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Run the script directly from the command line:

```
python pdf_compare.py path_to_first.pdf path_to_second.pdf
```

### Web Application

Start the web application:

```
python app.py
```

Then open your browser and navigate to http://127.0.0.1:5000

## Web Application Features

1. **Upload PDFs**: Upload two PDF documents for comparison
2. **Select Pages**: Choose single pages or page ranges from each document
3. **Specify Italic Words**: Optionally filter which italic words to highlight
4. **View Results**: See highlighted differences in an interactive viewer
5. **Download Results**: Save the comparison result as a PDF file

The tool will:
1. Extract text from both PDF files
2. Compare the text content
3. Display the differences:
   - Red lines: Content present only in the first PDF
   - Green lines: Content present only in the second PDF
