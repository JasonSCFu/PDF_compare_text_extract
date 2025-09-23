#!/usr/bin/env python3

import re
import difflib

def normalize_whitespace(text):
    # Remove backspace characters and normalize all whitespace (spaces, tabs, newlines, etc.)
    text_no_backspace = text.replace('\b', '').replace('\x08', '')
    # Remove text surrounded by slashes before normalization
    text_no_slash = re.sub(r'/[^/]*/', '', text_no_backspace)
    # Replace all whitespace sequences (spaces, tabs, newlines, etc.) with a single space
    # and strip leading/trailing whitespace
    normalized = re.sub(r'\s+', ' ', text_no_slash).strip()
    return normalized

def test_line_break_ignoring():
    print("=== Testing Line Break Ignoring ===")

    # Test 1: Line breaks should be ignored
    text1 = "This is a sentence\nthat is broken\ninto multiple lines"
    text2 = "This is a sentence that is broken into multiple lines"

    norm1 = normalize_whitespace(text1)
    norm2 = normalize_whitespace(text2)

    print(f"Original text1: {repr(text1)}")
    print(f"Original text2: {repr(text2)}")
    print(f"Normalized text1: {repr(norm1)}")
    print(f"Normalized text2: {repr(norm2)}")
    print(f"Are they equal after normalization? {norm1 == norm2}")
    print()

def test_slash_exclusion():
    print("=== Testing Slash Exclusion ===")

    # Test 2: Text in slashes should be ignored
    text1 = "This is /ignore this/ important text"
    text2 = "This is /don't ignore this/ important text"

    norm1 = normalize_whitespace(text1)
    norm2 = normalize_whitespace(text2)

    print(f"Original text1: {repr(text1)}")
    print(f"Original text2: {repr(text2)}")
    print(f"Normalized text1: {repr(norm1)}")
    print(f"Normalized text2: {repr(norm2)}")
    print(f"Are they equal after normalization? {norm1 == norm2}")
    print()

def test_combined_features():
    print("=== Testing Combined Features ===")

    # Test 3: Both line breaks and slash exclusion
    text1 = "This is a\nsentence /ignore this/\nwith breaks"
    text2 = "This is a sentence /something else/ with breaks"

    norm1 = normalize_whitespace(text1)
    norm2 = normalize_whitespace(text2)

    print(f"Original text1: {repr(text1)}")
    print(f"Original text2: {repr(text2)}")
    print(f"Normalized text1: {repr(norm1)}")
    print(f"Normalized text2: {repr(norm2)}")
    print(f"Are they equal after normalization? {norm1 == norm2}")
    print()

def test_whitespace_and_backspace():
    print("=== Testing Whitespace and Backspace Handling ===")

    # Test 4: Backspace and various whitespace characters
    text1 = "This\thas\b\x08\tvarious   whitespace\n\n\ncharacters"
    text2 = "This has various whitespace characters"

    norm1 = normalize_whitespace(text1)
    norm2 = normalize_whitespace(text2)

    print(f"Original text1: {repr(text1)}")
    print(f"Original text2: {repr(text2)}")
    print(f"Normalized text1: {repr(norm1)}")
    print(f"Normalized text2: {repr(norm2)}")
    print(f"Are they equal after normalization? {norm1 == norm2}")
    print()

if __name__ == "__main__":
    test_line_break_ignoring()
    test_slash_exclusion()
    test_combined_features()
    test_whitespace_and_backspace()

    print("=== All Tests Complete ===")