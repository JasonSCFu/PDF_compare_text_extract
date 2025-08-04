import fitz
import argparse
import sys
from datetime import datetime

def is_italic_font(page, span):
    """Check if the text uses an italic font."""
    # Get the font name from the span
    font_name = span.get("font", "")
    text = span.get("text", "").strip()
    
    # Get all fonts in the page
    fonts = page.get_fonts()
    
    # Check if it's an italic font
    return "LightIt" in font_name or "Italic" in font_name

def compare_pdfs(pdf1_path, pdf2_path, output_path=None, specific_italic_words=None):
    """Compare text content of two PDF files and highlight differences in a new PDF."""
    try:
        # Open the PDFs with PyMuPDF
        doc1 = fitz.open(pdf1_path)
        doc2 = fitz.open(pdf2_path)
        
        print('Creating output document...')
        # Create a new PDF for the comparison result
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'comparison_result_{timestamp}.pdf'
        output_doc = fitz.open()
        print(f'Output will be saved as: {output_path}')
        
        # Process each page
        max_pages = max(len(doc1), len(doc2))
        print(f'Processing {max_pages} pages...')
        
        for page_num in range(max_pages):
            # Create a new page
            page_width = max(doc1[0].rect.width if len(doc1) > 0 else 0,
                           doc2[0].rect.width if len(doc2) > 0 else 0)
            page_height = max(doc1[0].rect.height if len(doc1) > 0 else 0,
                            doc2[0].rect.height if len(doc2) > 0 else 0)
            new_page = output_doc.new_page(width=page_width * 2, height=page_height)
            
            # Process first document
            if page_num < len(doc1):
                text1 = doc1[page_num].get_text()
                # Copy content to left side
                new_page.show_pdf_page(
                    fitz.Rect(0, 0, page_width, page_height),
                    doc1,
                    page_num
                )
            else:
                text1 = ""
            
            # Process second document
            if page_num < len(doc2):
                text2 = doc2[page_num].get_text()
                # Copy content to right side
                new_page.show_pdf_page(
                    fitz.Rect(page_width, 0, page_width * 2, page_height),
                    doc2,
                    page_num
                )
            else:
                text2 = ""
            
            # Compare text and highlight differences
            if text1 and text2:
                # Function to check if a block contains a bullet point
                def is_bullet_point(text):
                    return any(bullet in text for bullet in ['•', '-', '·', '*', '○', '▪', '◦', '▫', '⁃'])
                
                # Process bullet points
                blocks1 = doc1[page_num].get_text("blocks")
                blocks2 = doc2[page_num].get_text("blocks")
                
                # Process regular text (word by word)
                # Get words with their positions and font info
                words1 = []
                words2 = []
                
                # Get words from first document
                dict1 = doc1[page_num].get_text("dict")
                for block in dict1["blocks"]:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                # Split text into individual words
                                words = text.split()
                                word_width = (span["bbox"][2] - span["bbox"][0]) / len(text)
                                
                                # Calculate position for each word
                                for word in words:
                                    word_start = span["bbox"][0] + text.index(word) * word_width
                                    word_bbox = [
                                        word_start,
                                        span["bbox"][1],
                                        word_start + len(word) * word_width,
                                        span["bbox"][3]
                                    ]
                                    is_italic = is_italic_font(doc1[page_num], span)
                                    words1.append((word, word_bbox, block.get("number", 0), is_italic))
                
                # Get words from second document
                dict2 = doc2[page_num].get_text("dict")
                for block in dict2["blocks"]:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                # Split text into individual words
                                words = text.split()
                                word_width = (span["bbox"][2] - span["bbox"][0]) / len(text)
                                
                                # Calculate position for each word
                                for word in words:
                                    word_start = span["bbox"][0] + text.index(word) * word_width
                                    word_bbox = [
                                        word_start,
                                        span["bbox"][1],
                                        word_start + len(word) * word_width,
                                        span["bbox"][3]
                                    ]
                                    is_italic = is_italic_font(doc2[page_num], span)
                                    words2.append((word, word_bbox, block.get("number", 0), is_italic))
                
                # Function to find similar positions
                def find_matching_word(target_word, target_line, words_list, tolerance=5):
                    for word, coords, line_num, _ in words_list:
                        # Check if words are on similar lines (within tolerance)
                        if abs(line_num - target_line) <= tolerance:
                            if word == target_word:
                                return True
                    return False
                
                # Find and highlight differences and italic text in first document
                for word, coords, line_num, is_italic in words1:
                    # Debug print for italic words
                    if is_italic:
                        print(f'Found italic word in doc1: {word}')
                    
                    # Check for differences
                    if not find_matching_word(word, line_num, words2):
                        # Word not found in similar position in doc2
                        highlight = new_page.add_highlight_annot(fitz.Rect(coords))
                        highlight.set_colors(stroke=(1, 0, 0))  # Red
                        highlight.set_opacity(0.3)  # Make it more transparent
                        highlight.update()
                    
                    # Check for italic text
                    if is_italic and specific_italic_words:
                        # Only highlight specific italic words if they are provided
                        if word.lower() in [w.lower() for w in specific_italic_words]:
                            highlight = new_page.add_highlight_annot(fitz.Rect(coords))
                            highlight.set_colors(stroke=(0, 0, 1))  # Blue
                            highlight.set_opacity(0.2)  # Make blue highlight very transparent
                            highlight.update()
                
                # Find and highlight differences and italic text in second document
                for word, coords, line_num, is_italic in words2:
                    # Debug print for italic words
                    if is_italic:
                        print(f'Found italic word in doc2: {word}')
                    
                    # Check for differences
                    if not find_matching_word(word, line_num, words1):
                        # Word not found in similar position in doc1
                        rect = fitz.Rect(
                            coords[0] + page_width,
                            coords[1],
                            coords[2] + page_width,
                            coords[3]
                        )
                        highlight = new_page.add_highlight_annot(rect)
                        highlight.set_colors(stroke=(0, 1, 0))  # Green
                        highlight.set_opacity(0.3)  # Make it more transparent
                        highlight.update()
                    
                    # Check for italic text
                    if is_italic and specific_italic_words:
                        # Only highlight specific italic words if they are provided
                        if word.lower() in [w.lower() for w in specific_italic_words]:
                            rect = fitz.Rect(
                                coords[0] + page_width,
                                coords[1],
                                coords[2] + page_width,
                                coords[3]
                            )
                            highlight = new_page.add_highlight_annot(rect)
                            highlight.set_colors(stroke=(0, 0, 1))  # Blue
                            highlight.set_opacity(0.2)  # Make blue highlight very transparent
                            highlight.update()
        
        # Save and close
        print('Saving comparison result...')
        output_doc.save(output_path)
        output_doc.close()
        doc1.close()
        doc2.close()
        
        print('\nComparison completed successfully!')
        print(f'Result saved as: {output_path}')
        print('\nHighlight colors:')
        print('- Red: Content only in first PDF')
        print('- Green: Content only in second PDF')
        print('- Yellow: Missing words between matching content')
        
    except fitz.FileDataError as e:
        print(f'Error: Could not open PDF file - {str(e)}')
        print('Please make sure both files exist and are valid PDF files.')
    except Exception as e:
        print(f'Error comparing PDFs: {str(e)}')
        import traceback
        print('Detailed error:')
        print(traceback.format_exc())



def main():
    parser = argparse.ArgumentParser(description='Compare text differences between two PDF files')
    parser.add_argument('pdf1', help='Path to first PDF file')
    parser.add_argument('pdf2', help='Path to second PDF file')
    
    args = parser.parse_args()
    compare_pdfs(args.pdf1, args.pdf2)

if __name__ == "__main__":
    main()
