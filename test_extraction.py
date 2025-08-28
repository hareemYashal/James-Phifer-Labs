#!/usr/bin/env python3
"""
Test script for the Comprehensive PDF Extractor
"""

import json
import os
from pdf_extractor import ComprehensivePDFExtractor

def test_extraction():
    """Test the PDF extraction on a sample file"""
    
    # Initialize extractor
    extractor = ComprehensivePDFExtractor()
    
    # Test PDF path
    pdf_path = "Sample Documents/OCR 35.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        print("Please ensure the test PDF file exists in the Sample Documents folder.")
        return False
    
    print(f"🔍 Testing extraction on: {pdf_path}")
    print("Processing...")
    
    try:
        # Perform extraction
        result = extractor.extract_comprehensive(pdf_path)
        
        # Check if extraction was successful
        if result.get("status") == "success":
            print("✅ Extraction completed successfully!")
            print(f"📊 Total fields extracted: {result.get('total_fields', 0)}")
            print(f"☑️ Total checkboxes found: {result.get('total_checkboxes', 0)}")
            print(f"📋 Sample IDs found: {len(result.get('sample_ids', []))}")
            print(f"🔬 Analysis requests found: {len(result.get('analysis_requests', []))}")
            
            # Display sample IDs
            sample_ids = result.get('sample_ids', [])
            if sample_ids:
                print(f"\n📋 Sample IDs: {', '.join(sample_ids)}")
            
            # Display analysis requests
            analysis_requests = result.get('analysis_requests', [])
            if analysis_requests:
                print(f"🔬 Analysis Requests: {', '.join(analysis_requests)}")
            
            # Display sample-analysis mapping
            mapping = result.get('sample_analysis_mapping', {}).get('sample_analysis_map', {})
            if mapping:
                print(f"\n🔗 Sample-Analysis Mapping:")
                for sample_id, analyses in mapping.items():
                    print(f"  {sample_id}:")
                    for analysis, state in analyses.items():
                        status = "✅" if state == "checked" else "❌"
                        print(f"    {status} {analysis}: {state}")
            
            # Display new checkbox categories
            all_checkboxes = result.get('all_checkboxes', {})
            
            # Data Deliverables
            data_deliverables = all_checkboxes.get('data_deliverables_checkboxes', {})
            if data_deliverables:
                print(f"\n📊 Data Deliverables:")
                for key, value in data_deliverables.items():
                    status = "✅" if value == "checked" else "❌"
                    print(f"    {status} {key}: {value}")
            
            # Rush Options
            rush_options = all_checkboxes.get('rush_option_checkboxes', {})
            if rush_options:
                print(f"\n⚡ Rush Options:")
                for key, value in rush_options.items():
                    status = "✅" if value == "checked" else "❌"
                    print(f"    {status} {key}: {value}")
            
            # Time Zone Collected
            timezone_checkboxes = all_checkboxes.get('timezone_checkboxes', {})
            if timezone_checkboxes:
                print(f"\n🕐 Time Zone Collected:")
                for key, value in timezone_checkboxes.items():
                    status = "✅" if value == "checked" else "❌"
                    print(f"    {status} {key}: {value}")
            
            # Reportable
            reportable_checkboxes = all_checkboxes.get('reportable_checkboxes', {})
            if reportable_checkboxes:
                print(f"\n📋 Reportable:")
                for key, value in reportable_checkboxes.items():
                    status = "✅" if value == "checked" else "❌"
                    print(f"    {status} {key}: {value}")
            
            # Container Information
            container_fields = []
            for field in result.get('extracted_fields', []):
                if any(keyword in field.get('key', '').lower() for keyword in ['container', 'size', 'preservative']):
                    container_fields.append(field)
            
            if container_fields:
                print(f"\n📦 Container Information:")
                for field in container_fields:
                    print(f"    {field.get('key')}: {field.get('value')}")
            
            # Save results
            output_file = "test_extraction_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_file}")
            return True
            
        else:
            print(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_api_key():
    """Test if the API key is properly configured"""
    try:
        from config import GEMINI_API_KEY
        if GEMINI_API_KEY:
            print(f"✅ API key is configured: {GEMINI_API_KEY[:20]}...")
            return True
        else:
            print("❌ API key is not configured")
            return False
    except Exception as e:
        print(f"❌ Error checking API key: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 PDF Extraction Test Suite")
    print("=" * 50)
    
    # Test API key
    print("\n1. Testing API key configuration...")
    api_key_ok = test_api_key()
    
    if not api_key_ok:
        print("\n❌ API key test failed. Please check your configuration.")
        return
    
    # Test extraction
    print("\n2. Testing PDF extraction...")
    extraction_ok = test_extraction()
    
    if extraction_ok:
        print("\n✅ All tests passed!")
        print("\n🚀 The extraction system is working correctly.")
        print("You can now:")
        print("  - Run the API server with: python api.py")
        print("  - Use the extraction directly with: python pdf_extractor.py")
        print("\n📋 New features added:")
        print("  - Data Deliverables checkboxes (Level II, III, IV, Equis, Others)")
        print("  - Rush options (Same Day, 1 Day, 2 Day, 3 Day, Others)")
        print("  - Time Zone Collected checkboxes (AM, PT, MT, CT, ET)")
        print("  - Container Size and Preservative Type values")
        print("  - Reportable checkboxes (Yes, No)")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
