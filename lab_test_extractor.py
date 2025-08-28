#!/usr/bin/env python3
"""
Lab Test Document Extractor
Extracts field names (computer-typed) and handwritten answers from lab test PDFs
"""

import os
import json
import base64
from enhanced_extractor import EnhancedPDFExtractor
from config import GEMINI_API_KEY

def extract_lab_test_fields(pdf_path):
    """Extract field names and values from lab test document."""
    print(f"🔬 Analyzing lab test document: {os.path.basename(pdf_path)}")
    
    extractor = EnhancedPDFExtractor()
    
    # Extract fields using multiple methods
    fields = []
    
    # Method 1: PyMuPDF extraction (best for complex PDFs)
    try:
        fitz_fields = extractor._extract_with_fitz(pdf_path)
        if fitz_fields:
            fields.extend(fitz_fields)
            print(f"   ✅ PyMuPDF extraction: {len(fitz_fields)}")
        else:
            print(f"   ⚠️  PyMuPDF: No fields found")
    except Exception as e:
        print(f"   ❌ PyMuPDF extraction failed: {e}")
    
    # Method 2: PyPDF2 extraction (fallback)
    try:
        pypdf2_fields = extractor._extract_with_pypdf2(pdf_path)
        if pypdf2_fields:
            fields.extend(pypdf2_fields)
            print(f"   ✅ PyPDF2 extraction: {len(pypdf2_fields)}")
        else:
            print(f"   ⚠️  PyPDF2: No fields found")
    except Exception as e:
        print(f"   ❌ PyPDF2 extraction failed: {e}")
    
    # Method 3: AI Vision for handwritten text (if API key available)
    if GEMINI_API_KEY != 'your_gemini_api_key_here':
        try:
            vision_fields = extractor._extract_with_ai_vision(pdf_path)
            if vision_fields:
                fields.extend(vision_fields)
                print(f"   ✅ AI Vision: {len(vision_fields)}")
            else:
                print(f"   ⚠️  AI Vision: No fields found")
        except Exception as e:
            print(f"   ❌ AI Vision failed: {e}")
    else:
        print("   ⚠️  AI Vision skipped (no API key)")
    
    # Clean and organize fields
    cleaned_fields = []
    for field in fields:
        if field.get('key') and field.get('value'):
            # Clean up the field data
            cleaned_field = {
                'field_name': field.get('key', '').strip(),
                'value': field.get('value', '').strip(),
                'type': field.get('type', 'unknown'),
                'page': field.get('page', 1),
                'extraction_method': field.get('method', 'unknown')
            }
            cleaned_fields.append(cleaned_field)
    
    print(f"   📊 Total fields extracted: {len(cleaned_fields)}")
    return cleaned_fields

def main():
    """Main function for lab test extraction."""
    print("🔬 LAB TEST DOCUMENT EXTRACTOR")
    print("=" * 50)
    print("Extracts field names and handwritten answers from lab test PDFs")
    print()
    
    # Get PDF file path
    pdf_path = input("📄 Enter path to lab test PDF: ").strip().strip('"')
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print(f"\n✅ File found: {os.path.basename(pdf_path)}")
    
    # Check API key
    if GEMINI_API_KEY == 'your_gemini_api_key_here':
        print("\n⚠️  No Gemini API key set - handwritten text extraction will be limited")
        print("   To enable AI vision analysis for handwritten text:")
        print("   1. Get a key from: https://makersuite.google.com/app/apikey")
        print("   2. Update config.py with your API key")
        print("   3. Restart the program")
    
    # Extract fields
    print(f"\n🔍 EXTRACTING FIELDS...")
    fields = extract_lab_test_fields(pdf_path)
    
    if not fields:
        print("\n❌ No fields could be extracted from the document")
        print("\n💡 This might happen if:")
        print("   • The PDF is heavily image-based/scanned")
        print("   • Text is not clearly readable")
        print("   • The document structure is complex")
        print("\n🔧 Try using a Gemini API key for better AI vision analysis")
        return
    
    # Display results
    print(f"\n🎉 EXTRACTION COMPLETED!")
    print("=" * 60)
    
    # Group fields by type
    form_fields = [f for f in fields if f['type'] in [2, 7]]  # Checkbox and text fields
    text_fields = [f for f in fields if f['type'] == 'text']
    other_fields = [f for f in fields if f['type'] not in [2, 7, 'text']]
    
    print(f"📊 EXTRACTION SUMMARY:")
    print(f"   Form Fields: {len(form_fields)}")
    print(f"   Text Fields: {len(text_fields)}")
    print(f"   Other Fields: {len(other_fields)}")
    print(f"   Total Fields: {len(fields)}")
    
    # Show form fields (most likely to contain field names and values)
    if form_fields:
        print(f"\n📝 FORM FIELDS (Field Names + Values):")
        print("-" * 80)
        print(f"{'Field Name':<30} {'Value':<40} {'Method':<10}")
        print("-" * 80)
        
        for field in form_fields[:30]:  # Show first 30
            field_name = field['field_name'][:29] if len(field['field_name']) > 29 else field['field_name']
            value = str(field['value'])[:39] if len(str(field['value'])) > 39 else str(field['value'])
            method = field['extraction_method'][:9] if len(field['extraction_method']) > 9 else field['extraction_method']
            print(f"{field_name:<30} {value:<40} {method:<10}")
        
        if len(form_fields) > 30:
            print(f"... and {len(form_fields) - 30} more form fields")
    
    # Show text fields (might contain additional context)
    if text_fields:
        print(f"\n📄 TEXT CONTENT (Additional Context):")
        print("-" * 80)
        for field in text_fields[:10]:  # Show first 10
            print(f"• {field['field_name']}: {field['value']}")
        
        if len(text_fields) > 10:
            print(f"... and {len(text_fields) - 10} more text fields")
    
    # Show other fields
    if other_fields:
        print(f"\n🔍 OTHER FIELDS:")
        print("-" * 80)
        for field in other_fields[:10]:  # Show first 10
            print(f"• {field['field_name']}: {field['value']} (Type: {field['type']})")
        
        if len(other_fields) > 10:
            print(f"... and {len(other_fields) - 10} more other fields")
    
    # Save results
    results_file = "lab_test_extraction_results.json"
    results = {
        'pdf_path': pdf_path,
        'file_size_bytes': os.path.getsize(pdf_path),
        'file_size_mb': round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
        'extraction_summary': {
            'total_fields': len(fields),
            'form_fields': len(form_fields),
            'text_fields': len(text_fields),
            'other_fields': len(other_fields)
        },
        'extracted_fields': fields,
        'status': 'success'
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Instructions for better results
    print(f"\n💡 TIPS FOR BETTER RESULTS:")
    print(f"   • Ensure the PDF is clear and readable")
    print(f"   • Field names should be clearly visible (computer-typed)")
    print(f"   • Handwritten answers should be legible")
    print(f"   • Use a Gemini API key for better handwritten text recognition")
    
    return results

if __name__ == "__main__":
    main() 