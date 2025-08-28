#!/usr/bin/env python3
"""
Robust Lab Test Document Extractor
Better handling of AI responses and fallback extraction methods
"""

import os
import json
import base64
import re
from enhanced_extractor import EnhancedPDFExtractor
from config import GEMINI_API_KEY

def extract_with_simple_ai_prompt(pdf_path):
    """Extract fields using a simple AI prompt that's more likely to work."""
    try:
        import fitz
        extractor = EnhancedPDFExtractor()
        
        if not extractor.gemini_ready:
            return []
        
        doc = fitz.open(pdf_path)
        all_fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode()
            
            # Simple, clear prompt
            prompt = f"""
            Look at this document image (page {page_num + 1}) and identify:
            
            1. Field names/labels (like "Name:", "Date:", "Address:")
            2. Values written in those fields
            
            Return your response in this exact JSON format:
            [
                {{"key": "field_name", "value": "field_value"}},
                {{"key": "another_field", "value": "another_value"}}
            ]
            
            Only return valid JSON, nothing else.
            """
            
            response = extractor.model.generate_content([
                prompt, 
                {"mime_type": "image/png", "data": img_base64}
            ])
            
            # Try to extract JSON from response
            text = response.text.strip()
            
            # Look for JSON array in the response
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    fields = json.loads(json_str)
                    if isinstance(fields, list):
                        for field in fields:
                            if isinstance(field, dict) and 'key' in field and 'value' in field:
                                field['page'] = page_num + 1
                                field['method'] = 'AI Vision'
                                field['type'] = 'ai_extracted'
                                all_fields.append(field)
                except json.JSONDecodeError:
                    print(f"   ⚠️  JSON parsing failed on page {page_num + 1}")
            
            # If no JSON found, try to extract key-value pairs from text
            else:
                # Simple pattern matching for "key: value" format
                lines = text.split('\n')
                for line in lines:
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key and value:
                                all_fields.append({
                                    'key': key,
                                    'value': value,
                                    'page': page_num + 1,
                                    'method': 'AI Vision (text)',
                                    'type': 'ai_extracted'
                                })
        
        doc.close()
        return all_fields
        
    except Exception as e:
        print(f"   ❌ AI Vision extraction failed: {e}")
        return []

def extract_lab_test_fields_robust(pdf_path):
    """Extract fields using multiple robust methods."""
    print(f"🔬 Analyzing lab test document: {os.path.basename(pdf_path)}")
    
    extractor = EnhancedPDFExtractor()
    all_fields = []
    
    # Method 1: PyMuPDF extraction
    try:
        fitz_fields = extractor._extract_with_fitz(pdf_path)
        if fitz_fields:
            all_fields.extend(fitz_fields)
            print(f"   ✅ PyMuPDF: {len(fitz_fields)} fields")
        else:
            print(f"   ⚠️  PyMuPDF: No fields found")
    except Exception as e:
        print(f"   ❌ PyMuPDF failed: {e}")
    
    # Method 2: PyPDF2 extraction
    try:
        pypdf2_fields = extractor._extract_with_pypdf2(pdf_path)
        if pypdf2_fields:
            all_fields.extend(pypdf2_fields)
            print(f"   ✅ PyPDF2: {len(pypdf2_fields)} fields")
        else:
            print(f"   ⚠️  PyPDF2: No fields found")
    except Exception as e:
        print(f"   ❌ PyPDF2 failed: {e}")
    
    # Method 3: Robust AI Vision
    if GEMINI_API_KEY != 'your_gemini_api_key_here':
        print(f"   🔍 Trying AI Vision with robust parsing...")
        ai_fields = extract_with_simple_ai_prompt(pdf_path)
        if ai_fields:
            all_fields.extend(ai_fields)
            print(f"   ✅ AI Vision: {len(ai_fields)} fields")
        else:
            print(f"   ⚠️  AI Vision: No fields found")
    else:
        print("   ⚠️  AI Vision skipped (no API key)")
    
    # Clean and deduplicate fields
    cleaned_fields = []
    seen_keys = set()
    
    for field in all_fields:
        key = field.get('key', '').strip()
        value = field.get('value', '').strip()
        
        if key and value and key not in seen_keys:
            cleaned_field = {
                'field_name': key,
                'value': value,
                'type': field.get('type', 'unknown'),
                'page': field.get('page', 1),
                'extraction_method': field.get('method', 'unknown')
            }
            cleaned_fields.append(cleaned_field)
            seen_keys.add(key)
    
    print(f"   📊 Total unique fields: {len(cleaned_fields)}")
    return cleaned_fields

def main():
    """Main function for robust lab test extraction."""
    print("🔬 ROBUST LAB TEST DOCUMENT EXTRACTOR")
    print("=" * 50)
    print("Extracts field names and handwritten answers from lab test PDFs")
    print("Uses multiple methods with robust AI Vision handling")
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
    fields = extract_lab_test_fields_robust(pdf_path)
    
    if not fields:
        print("\n❌ No fields could be extracted from the document")
        print("\n💡 This might happen if:")
        print("   • The PDF is heavily image-based/scanned")
        print("   • Text is not clearly readable")
        print("   • The document structure is complex")
        print("\n🔧 Try running the simple AI test: python simple_ai_test.py")
        return
    
    # Display results
    print(f"\n🎉 EXTRACTION COMPLETED!")
    print("=" * 60)
    
    print(f"📊 EXTRACTION SUMMARY:")
    print(f"   Total Fields: {len(fields)}")
    
    # Show all extracted fields
    print(f"\n📝 EXTRACTED FIELDS:")
    print("-" * 80)
    print(f"{'Field Name':<30} {'Value':<40} {'Method':<10}")
    print("-" * 80)
    
    for field in fields:
        field_name = field['field_name'][:29] if len(field['field_name']) > 29 else field['field_name']
        value = str(field['value'])[:39] if len(str(field['value'])) > 39 else str(field['value'])
        method = field['extraction_method'][:9] if len(field['extraction_method']) > 9 else field['extraction_method']
        print(f"{field_name:<30} {value:<40} {method:<10}")
    
    # Save results
    results_file = "robust_lab_extraction_results.json"
    results = {
        'pdf_path': pdf_path,
        'file_size_bytes': os.path.getsize(pdf_path),
        'file_size_mb': round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
        'extraction_summary': {
            'total_fields': len(fields)
        },
        'extracted_fields': fields,
        'status': 'success'
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    main() 