#!/usr/bin/env python3
"""
Simple AI Vision test to debug JSON parsing issues
"""

import base64
import json
from enhanced_extractor import EnhancedPDFExtractor

def test_ai_vision():
    """Test AI Vision with a simple prompt."""
    print("🧪 TESTING AI VISION EXTRACTION")
    print("=" * 40)
    
    extractor = EnhancedPDFExtractor()
    
    if not extractor.gemini_ready:
        print("❌ Gemini API not ready")
        return
    
    # Test with your lab test PDF
    pdf_path = "Sample Documents/OCR 37.pdf"
    
    print(f"📄 Testing with: {pdf_path}")
    
    try:
        # Try to get the raw AI response
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[0]  # First page
        
        # Convert page to image
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        img_base64 = base64.b64encode(img_data).decode()
        
        # Simple prompt
        prompt = """
        Look at this document image and tell me what you see.
        Focus on:
        1. What kind of document is this?
        2. What fields or labels do you see?
        3. What values are written in those fields?
        
        Just describe what you see in plain text.
        """
        
        print("\n🔍 Sending image to AI Vision...")
        response = extractor.model.generate_content([
            prompt, 
            {"mime_type": "image/png", "data": img_base64}
        ])
        
        print(f"\n✅ AI Response received!")
        print(f"📝 Response length: {len(response.text)} characters")
        print(f"\n📄 AI Response:")
        print("-" * 50)
        print(response.text)
        print("-" * 50)
        
        # Try to parse as JSON if it looks like JSON
        if response.text.strip().startswith('[') or response.text.strip().startswith('{'):
            try:
                parsed = json.loads(response.text)
                print(f"\n✅ Successfully parsed as JSON!")
                print(f"📊 JSON type: {type(parsed)}")
                if isinstance(parsed, list):
                    print(f"📝 Number of items: {len(parsed)}")
                    for i, item in enumerate(parsed[:3]):
                        print(f"   Item {i}: {item}")
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON parsing failed: {e}")
                print(f"🔍 This suggests the AI didn't return valid JSON")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✅ AI Vision test completed!")

if __name__ == "__main__":
    test_ai_vision() 