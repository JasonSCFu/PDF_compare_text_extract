#!/usr/bin/env python3

import re

def normalize_whitespace(text):
    # Remove backspace characters and normalize all whitespace (spaces, tabs, newlines, etc.)
    text_no_backspace = text.replace('\b', '').replace('\x08', '')
    # Remove text surrounded by slashes before normalization (global replacement)
    text_no_slash = re.sub(r'/[^/]*/', '', text_no_backspace, flags=re.DOTALL)
    # Replace all whitespace sequences (spaces, tabs, newlines, etc.) with a single space
    # and strip leading/trailing whitespace
    normalized = re.sub(r'\s+', ' ', text_no_slash).strip()
    return normalized

def test_user_example():
    print("=== Testing User's Example ===")

    text1 = "your home or /lifestyle block are/ going to be unoccupied."
    text2 = "your home or /lifestyle is/ going to be unoccupied."

    norm1 = normalize_whitespace(text1)
    norm2 = normalize_whitespace(text2)

    print(f"Original text1: {repr(text1)}")
    print(f"Original text2: {repr(text2)}")
    print(f"Normalized text1: {repr(norm1)}")
    print(f"Normalized text2: {repr(norm2)}")
    print(f"Are they equal after normalization? {norm1 == norm2}")

    if norm1 != norm2:
        print("❌ FAILED - texts should be equal after normalization")
    else:
        print("✅ PASSED - texts are correctly treated as equal")

if __name__ == "__main__":
    test_user_example()