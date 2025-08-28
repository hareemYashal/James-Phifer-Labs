#!/usr/bin/env python3
"""
Test script to verify PDF extraction works
"""

from enhanced_extractor import EnhancedPDFExtractor

def test_extraction():
    """Test the extraction methods."""
    print("🧪 TESTING PDF EXTRACTION METHODS")
    print("=" * 40)
    
    extractor = EnhancedPDFExtractor()
    
    # Test with your lab test PDF
    pdf_path = "Sample Documents/2097_001.pdf"
    
    print(f"📄 Testing with: {pdf_path}")
    
    # Test PyMuPDF extraction
    print("\n🔍 Testing PyMuPDF extraction...")
    try:
        fitz_fields = extractor._extract_with_fitz(pdf_path)
        print(f"   ✅ PyMuPDF: {len(fitz_fields) if fitz_fields else 0} fields")
        if fitz_fields:
            print(f"   📝 Sample fields:")
            for field in fitz_fields[:3]:
                print(f"      • {field.get('key', 'Unknown')}: {field.get('value', 'No value')}")
    except Exception as e:
        print(f"   ❌ PyMuPDF failed: {e}")
    
    # Test PyPDF2 extraction
    print("\n🔍 Testing PyPDF2 extraction...")
    try:
        pypdf2_fields = extractor._extract_with_pypdf2(pdf_path)
        print(f"   ✅ PyPDF2: {len(pypdf2_fields) if pypdf2_fields else 0} fields")
        if pypdf2_fields:
            print(f"   📝 Sample fields:")
            for field in pypdf2_fields[:3]:
                print(f"      • {field.get('key', 'Unknown')}: {field.get('value', 'No value')}")
    except Exception as e:
        print(f"   ❌ PyPDF2 failed: {e}")
    
    # Test AI Vision (if available)
    print("\n🔍 Testing AI Vision extraction...")
    try:
        vision_fields = extractor._extract_with_ai_vision(pdf_path)
        print(f"   ✅ AI Vision: {len(vision_fields) if vision_fields else 0} fields")
        if vision_fields:
            print(f"   📝 Sample fields:")
            for field in vision_fields[:3]:
                print(f"      • {field.get('key', 'Unknown')}: {field.get('value', 'No value')}")
    except Exception as e:
        print(f"   ❌ AI Vision failed: {e}")
    
    print("\n✅ Testing completed!")

if __name__ == "__main__":
    test_extraction() 