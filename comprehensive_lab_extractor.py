#!/usr/bin/env python3
"""
Comprehensive Lab Test Document Extractor
Captures ALL fields including multiple sample IDs, their details, and vertical analysis requests with checkboxes
"""

import os
import json
import base64
import re
from enhanced_extractor import EnhancedPDFExtractor
from config import GEMINI_API_KEY

def extract_with_comprehensive_ai_prompt(pdf_path):
    """Extract ALL fields using a comprehensive AI prompt for multiple samples and analysis requests."""
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
            
            # Comprehensive prompt specifically for lab test documents with multiple samples
            prompt = f"""
            Analyze this lab test document image (page {page_num + 1}) and extract ALL information.
            
            CRITICAL: Extract EVERY SINGLE FIELD and DETAIL from this form, including:
            
            1. **ALL FORM HEADERS AND TITLES**:
               - Document title, form name, revision date
               - Any headers, section titles, or labels
            
            2. **ALL CLIENT INFORMATION FIELDS**:
               - Client Name, Address, Report To, Email, Phone, PO#, Project#
               - Any other client-related fields
            
            3. **ALL WORK ORDER AND DATE FIELDS**:
               - Work Order number, Year, Date, Time
               - Any date/time related fields
            
            4. **ALL SAMPLE INFORMATION** (for EACH sample):
               - Customer Sample ID (XM-15, XM-16, XM-17, etc.)
               - Matrix/Code, Comp/Grade
               - Start Date, Start Time, End Date, End Time
               - # Containers, Sample Type, Sample Source
               - Any other sample-related fields
            
            5. **ALL ANALYSIS REQUEST FIELDS**:
               - Analysis request names (horizontal, vertical, diagonal)
               - Checkboxes for each analysis request per sample
               - Parameter fields, preservation codes
            
            6. **ALL HAZARD AND SAFETY FIELDS**:
               - Hazard checkboxes (Non-Hazard, Flammable, Skin Irritant, etc.)
               - Safety information, warnings
            
            7. **ALL TECHNICAL PARAMETERS**:
               - Filtered (Yes/No), Cooled (Yes/No)
               - Container Type, Container Volume
               - Temperature fields, flow fields
            
            8. **ALL ADMINISTRATIVE FIELDS**:
               - Relinquished By, Received By fields
               - Date/Time stamps, initials
               - Page numbers, form numbers
            
            9. **ALL OTHER VISIBLE TEXT AND FIELDS**:
               - Any text, numbers, symbols, or marks
               - Empty fields, blank spaces (mark as "NIL")
               - Any other information visible on the page
            
            IMPORTANT RULES:
            - Extract EVERYTHING you can see, no matter how small
            - If a field has no value, mark it as "NIL"
            - Include ALL text orientations (horizontal, vertical, diagonal, upside down)
            - Capture ALL checkboxes and their states
            - Don't skip any field, label, or piece of information
            
            Return your response in this exact JSON format:
            {{
                "form_headers": [
                    {{"key": "Document Title", "value": "Chain of Custody Record", "type": "header"}},
                    {{"key": "Form Revision", "value": "July 2014", "type": "header"}}
                ],
                "client_info": [
                    {{"key": "Client Name", "value": "NIL", "type": "field"}},
                    {{"key": "Address", "value": "NIL", "type": "field"}},
                    {{"key": "Report To", "value": "NIL", "type": "field"}}
                ],
                "work_order_info": [
                    {{"key": "Work Order", "value": "12345", "type": "field"}},
                    {{"key": "Year", "value": "2025", "type": "field"}}
                ],
                "customer_samples": [
                    {{
                        "sample_id": "XM-15",
                        "matrix": "M4",
                        "comp_grade": "4",
                        "start_date": "4/7/25",
                        "start_time": "6am",
                        "end_date": "4/8/25",
                        "end_time": "6am",
                        "containers": "2",
                        "sample_type": "Grab",
                        "sample_source": "WW",
                        "analysis_requests": [
                            {{"name": "Analysis Request 1", "checkbox_state": "checked", "marked": true}},
                            {{"name": "Analysis Request 2", "checkbox_state": "unchecked", "marked": false}},
                            {{"name": "Analysis Request 3", "checkbox_state": "checked", "marked": true}}
                        ]
                    }},
                    {{
                        "sample_id": "XM-16",
                        "matrix": "M5",
                        "comp_grade": "3",
                        "start_date": "4/9/25",
                        "start_time": "8am",
                        "end_date": "4/10/25",
                        "end_time": "8am",
                        "containers": "1",
                        "sample_type": "Composite",
                        "sample_source": "GW",
                        "analysis_requests": [
                            {{"name": "Analysis Request 1", "checkbox_state": "checked", "marked": true}},
                            {{"name": "Analysis Request 2", "checkbox_state": "checked", "marked": true}},
                            {{"name": "Analysis Request 3", "checkbox_state": "unchecked", "marked": false}}
                        ]
                    }}
                ],
                "hazard_info": [
                    {{"key": "Non-Hazard", "value": "checked", "type": "checkbox"}},
                    {{"key": "Flammable", "value": "unchecked", "type": "checkbox"}},
                    {{"key": "Skin Irritant", "value": "unchecked", "type": "checkbox"}}
                ],
                "technical_params": [
                    {{"key": "Filtered", "value": "Yes", "type": "field"}},
                    {{"key": "Cooled", "value": "No", "type": "field"}},
                    {{"key": "Container Type", "value": "Plastic", "type": "field"}}
                ],
                "administrative": [
                    {{"key": "Relinquished By", "value": "NIL", "type": "field"}},
                    {{"key": "Received By", "value": "NIL", "type": "field"}},
                    {{"key": "Initials", "value": "NIL", "type": "field"}}
                ]
            }}
            
            Be EXTREMELY thorough - extract EVERY SINGLE FIELD, LABEL, TEXT, and DETAIL you can see.
            If you see it, extract it. Don't miss anything.
            Only return valid JSON, nothing else.
            """
            
            response = extractor.model.generate_content([
                prompt, 
                {"mime_type": "image/png", "data": img_base64}
            ])
            
            # Try to extract JSON from response
            text = response.text.strip()
            
            # Look for JSON object in the response (new structured format)
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    structured_data = json.loads(json_str)
                    
                    if isinstance(structured_data, dict):
                        # Process structured data with organized sections
                        
                        # Process form headers
                        if 'form_headers' in structured_data:
                            for field in structured_data['form_headers']:
                                if isinstance(field, dict) and 'key' in field:
                                    field['page'] = page_num + 1
                                    field['method'] = 'AI Vision'
                                    field['type'] = field.get('type', 'header')
                                    field['value'] = field.get('value', 'NIL')
                                    field['orientation'] = 'horizontal'
                                    all_fields.append(field)
                        
                        # Process client info
                        if 'client_info' in structured_data:
                            for field in structured_data['client_info']:
                                if isinstance(field, dict) and 'key' in field:
                                    field['page'] = page_num + 1
                                    field['method'] = 'AI Vision'
                                    field['type'] = field.get('type', 'field')
                                    field['value'] = field.get('value', 'NIL')
                                    field['orientation'] = 'horizontal'
                                    all_fields.append(field)
                        
                        # Process work order info
                        if 'work_order_info' in structured_data:
                            for field in structured_data['work_order_info']:
                                if isinstance(field, dict) and 'key' in field:
                                    field['page'] = page_num + 1
                                    field['method'] = 'AI Vision'
                                    field['type'] = field.get('type', 'field')
                                    field['value'] = field.get('value', 'NIL')
                                    field['orientation'] = 'horizontal'
                                    all_fields.append(field)
                        
                        # Process customer samples (this is the main focus)
                        if 'customer_samples' in structured_data:
                            for sample in structured_data['customer_samples']:
                                if isinstance(sample, dict) and 'sample_id' in sample:
                                    # Add complete sample data
                                    sample['page'] = page_num + 1
                                    sample['method'] = 'AI Vision'
                                    sample['type'] = 'sample_data'
                                    all_fields.append(sample)
                                    
                                    # Also add individual sample fields for backward compatibility
                                    for key, value in sample.items():
                                        if key not in ['analysis_requests', 'page', 'method', 'type']:
                                            all_fields.append({
                                                'key': f"{sample['sample_id']}_{key}",
                                                'value': value,
                                                'page': page_num + 1,
                                                'method': 'AI Vision',
                                                'type': 'sample_field',
                                                'sample_id': sample['sample_id']
                                            })
                                    
                                    # Add analysis requests as separate fields
                                    if 'analysis_requests' in sample and isinstance(sample['analysis_requests'], list):
                                        for req in sample['analysis_requests']:
                                            if isinstance(req, dict) and 'name' in req:
                                                all_fields.append({
                                                    'key': f"{sample['sample_id']}_{req['name']}",
                                                    'value': req.get('checkbox_state', 'unknown'),
                                                    'page': page_num + 1,
                                                    'method': 'AI Vision',
                                                    'type': 'analysis_request',
                                                    'sample_id': sample['sample_id'],
                                                    'analysis_name': req['name'],
                                                    'marked': req.get('marked', False)
                                                })
                        
                        # Process hazard info
                        if 'hazard_info' in structured_data:
                            for field in structured_data['hazard_info']:
                                if isinstance(field, dict) and 'key' in field:
                                    field['page'] = page_num + 1
                                    field['method'] = 'AI Vision'
                                    field['type'] = field.get('type', 'checkbox')
                                    field['value'] = field.get('value', 'NIL')
                                    field['orientation'] = 'horizontal'
                                    all_fields.append(field)
                        
                        # Process technical params
                        if 'technical_params' in structured_data:
                            for field in structured_data['technical_params']:
                                if isinstance(field, dict) and 'key' in field:
                                    field['page'] = page_num + 1
                                    field['method'] = 'AI Vision'
                                    field['type'] = field.get('type', 'field')
                                    field['value'] = field.get('value', 'NIL')
                                    field['orientation'] = 'horizontal'
                                    all_fields.append(field)
                        
                        # Process administrative
                        if 'administrative' in structured_data:
                            for field in structured_data['administrative']:
                                if isinstance(field, dict) and 'key' in field:
                                    field['page'] = page_num + 1
                                    field['method'] = 'AI Vision'
                                    field['type'] = field.get('type', 'field')
                                    field['value'] = field.get('value', 'NIL')
                                    field['orientation'] = 'horizontal'
                                    all_fields.append(field)
                        
                except json.JSONDecodeError:
                    print(f"   ⚠️  JSON parsing failed on page {page_num + 1}")
            
            # If no structured JSON found, try to extract key-value pairs from text
            else:
                # Enhanced pattern matching for various formats
                lines = text.split('\n')
                for line in lines:
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key:
                                all_fields.append({
                                    'key': key,
                                    'value': value if value else 'NIL',
                                    'page': page_num + 1,
                                    'method': 'AI Vision (text)',
                                    'type': 'text',
                                    'orientation': 'horizontal'
                                })
                    # Look for checkbox patterns
                    elif 'checkbox' in line.lower() or '☐' in line or '☑' in line or '□' in line or '■' in line:
                        all_fields.append({
                            'key': line.strip(),
                            'value': 'checkbox',
                            'page': page_num + 1,
                            'method': 'AI Vision (text)',
                            'type': 'checkbox',
                            'orientation': 'horizontal'
                        })
        
        doc.close()
        return all_fields
        
    except Exception as e:
        print(f"   ❌ AI Vision extraction failed: {e}")
        return []

def extract_lab_test_fields_comprehensive(pdf_path):
    """Extract ALL fields using comprehensive methods."""
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
    
    # Method 3: Comprehensive AI Vision
    if GEMINI_API_KEY != 'your_gemini_api_key_here':
        print(f"   🔍 Trying Comprehensive AI Vision...")
        ai_fields = extract_with_comprehensive_ai_prompt(pdf_path)
        if ai_fields:
            all_fields.extend(ai_fields)
            print(f"   ✅ AI Vision: {len(ai_fields)} fields")
        else:
            print(f"   ⚠️  AI Vision: No fields found")
    else:
        print("   ⚠️  AI Vision skipped (no API key)")
    
    # Clean and organize fields
    cleaned_fields = []
    seen_keys = set()
    
    for field in all_fields:
        key = field.get('key', '').strip() if field.get('key') else ''
        value = field.get('value', '')
        
        # Handle None values and convert to string
        if value is None:
            value = 'NIL'
        else:
            value = str(value).strip()
        
        # Handle empty values - mark as NIL
        if not value or value.lower() in ['', 'none', 'null', 'nil', 'empty']:
            value = 'NIL'
        
        if key and key not in seen_keys:
            cleaned_field = {
                'field_name': key,
                'value': value,
                'type': field.get('type', 'unknown'),
                'page': field.get('page', 1),
                'extraction_method': field.get('method', 'unknown'),
                'orientation': field.get('orientation', 'horizontal')
            }
            cleaned_fields.append(cleaned_field)
            seen_keys.add(key)
    
    return cleaned_fields

def organize_fields_by_category(fields):
    """Organize fields into logical categories for better display."""
    categories = {
        'headers': [],
        'client_info': [],
        'work_order': [],
        'sample_data': [],
        'analysis_requests': [],
        'hazards': [],
        'technical': [],
        'administrative': [],
        'checkboxes': [],
        'other': []
    }
    
    for field in fields:
        field_name = field.get('field_name', '').lower()
        field_type = field.get('type', '').lower()
        
        # Categorize based on field name and type
        if any(word in field_name for word in ['title', 'header', 'form', 'revision']):
            categories['headers'].append(field)
        elif any(word in field_name for word in ['client', 'address', 'email', 'phone', 'po', 'project']):
            categories['client_info'].append(field)
        elif any(word in field_name for word in ['work order', 'date', 'time', 'year']):
            categories['work_order'].append(field)
        elif any(word in field_name for word in ['sample', 'matrix', 'grade', 'container']):
            categories['sample_data'].append(field)
        elif any(word in field_name for word in ['analysis', 'parameter', 'preservation']):
            categories['analysis_requests'].append(field)
        elif any(word in field_name for word in ['hazard', 'flammable', 'poison', 'irritant']):
            categories['hazards'].append(field)
        elif any(word in field_name for word in ['filtered', 'cooled', 'temperature', 'flow']):
            categories['technical'].append(field)
        elif any(word in field_name for word in ['relinquished', 'received', 'initials', 'page']):
            categories['administrative'].append(field)
        elif field_type == 'checkbox':
            categories['checkboxes'].append(field)
        else:
            categories['other'].append(field)
    
    return categories

def organize_sample_data(fields):
    """Organize fields into structured sample data."""
    samples = {}
    
    for field in fields:
        if field.get('type') == 'sample_data':
            # This is a complete sample record
            sample_id = field.get('sample_id', 'Unknown')
            samples[sample_id] = field
        elif field.get('type') == 'sample_field':
            # This is an individual sample field
            sample_id = field.get('sample_id', 'Unknown')
            if sample_id not in samples:
                samples[sample_id] = {'sample_id': sample_id}
            
            # Extract field name from key (e.g., "XM-15_matrix" -> "matrix")
            key = field.get('field_name', '')
            if '_' in key:
                field_name = key.split('_', 1)[1]
                samples[sample_id][field_name] = field.get('value')
    
    return samples

def main():
    """Main function for comprehensive lab test extraction."""
    print("🔬 COMPREHENSIVE LAB TEST DOCUMENT EXTRACTOR")
    print("=" * 60)
    print("Extracts ALL field names and values including multiple sample IDs and analysis requests")
    print("Uses comprehensive AI Vision to capture everything visible")
    print()
    
    # Get PDF file path
    pdf_path = input("📄 Enter path to lab test PDF: ").strip().strip('"')
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print(f"\n✅ File found: {os.path.basename(pdf_path)}")
    
    # Check API key
    if GEMINI_API_KEY == 'your_gemini_api_key_here':
        print("\n⚠️  No Gemini API key set - comprehensive extraction will be limited")
        print("   To enable comprehensive AI vision analysis:")
        print("   1. Get a key from: https://makersuite.google.com/app/apikey")
        print("   2. Update config.py with your API key")
        print("   3. Restart the program")
    
    # Extract fields
    print(f"\n🔍 EXTRACTING ALL FIELDS...")
    fields = extract_lab_test_fields_comprehensive(pdf_path)
    
    if not fields:
        print("\n❌ No fields could be extracted from the document")
        print("\n💡 This might happen if:")
        print("   • The PDF is heavily image-based/scanned")
        print("   • Text is not clearly readable")
        print("   • The document structure is complex")
        return
    
    # Organize sample data
    sample_data = organize_sample_data(fields)
    
    # Organize customer samples into structured format
    structured_customer_samples = {}
    for field in fields:
        if field.get('type') == 'sample_data' and 'sample_id' in field:
            sample_id = field['sample_id']
            structured_customer_samples[sample_id] = {
                'sample_id': sample_id,
                'matrix': field.get('matrix', 'NIL'),
                'comp_grade': field.get('comp_grade', 'NIL'),
                'start_date': field.get('start_date', 'NIL'),
                'start_time': field.get('start_time', 'NIL'),
                'end_date': field.get('end_date', 'NIL'),
                'end_time': field.get('end_time', 'NIL'),
                'containers': field.get('containers', 'NIL'),
                'sample_type': field.get('sample_type', 'NIL'),
                'sample_source': field.get('sample_source', 'NIL'),
                'analysis_requests': []
            }
            
            # Add analysis requests for this sample
            for analysis_field in fields:
                if (analysis_field.get('type') == 'analysis_request' and 
                    analysis_field.get('sample_id') == sample_id):
                    structured_customer_samples[sample_id]['analysis_requests'].append({
                        'name': analysis_field.get('analysis_name', 'Unknown'),
                        'checkbox_state': analysis_field.get('value', 'unknown'),
                        'marked': analysis_field.get('marked', False)
                    })
    
    # Organize fields by category
    categories = organize_fields_by_category(fields)
    
    # Display results
    print(f"\n🎉 EXTRACTION COMPLETED!")
    print("=" * 80)
    
    # Display categories
    print(f"\n📊 EXTRACTION CATEGORIES:")
    for category_name, category_fields in categories.items():
        if category_fields:
            print(f"   {category_name.replace('_', ' ').title()}: {len(category_fields)}")
    
    # Show organized sample data
    if sample_data:
        print(f"\n📋 ORGANIZED SAMPLE DATA:")
        print("=" * 100)
        for sample_id, sample in sample_data.items():
            print(f"\n🔬 SAMPLE ID: {sample_id}")
            print("-" * 50)
            for key, value in sample.items():
                if key != 'analysis_requests':
                    print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Show analysis requests for this sample
            if 'analysis_requests' in sample and isinstance(sample['analysis_requests'], list):
                print(f"   📊 Analysis Requests:")
                for req in sample['analysis_requests']:
                    status = "☑️ CHECKED" if req.get('marked') else "☐ UNCHECKED"
                    print(f"      • {req.get('name', 'Unknown')}: {status}")
    
    # Show structured customer samples
    if structured_customer_samples:
        print(f"\n🔬 CUSTOMER SAMPLES - STRUCTURED FORMAT:")
        print("=" * 120)
        
        for sample_id, sample_info in structured_customer_samples.items():
            print(f"\n📋 CUSTOMER SAMPLE ID: {sample_id}")
            print("=" * 80)
            print(f"   Sample ID Name: {sample_info['sample_id']}")
            print(f"   Matrix: {sample_info['matrix']}")
            print(f"   Comp/Grade: {sample_info['comp_grade']}")
            print(f"   Start Date: {sample_info['start_date']}")
            print(f"   Start Time: {sample_info['start_time']}")
            print(f"   End Date: {sample_info['end_date']}")
            print(f"   End Time: {sample_info['end_time']}")
            print(f"   # Containers: {sample_info['containers']}")
            print(f"   Sample Type: {sample_info['sample_type']}")
            print(f"   Sample Source: {sample_info['sample_source']}")
            
            # Show analysis requests for this sample
            if sample_info['analysis_requests']:
                print(f"   📊 Analysis Requests:")
                for i, req in enumerate(sample_info['analysis_requests'], 1):
                    status = "☑️ CHECKED" if req['marked'] else "☐ UNCHECKED"
                    print(f"      {i:2d}. {req['name']}: {req['checkbox_state']} ({status})")
            else:
                print(f"   📊 Analysis Requests: None found")
    
    # Show fields organized by category
    print(f"\n📋 FIELDS ORGANIZED BY CATEGORY:")
    print("=" * 100)
    
    for category_name, category_fields in categories.items():
        if category_fields:
            print(f"\n🔹 {category_name.replace('_', ' ').upper()}:")
            print("-" * 60)
            for field in category_fields:
                value_display = field['value'] if field['value'] != 'NIL' else 'NIL'
                print(f"   • {field['field_name']}: {value_display}")
    
    # Show all extracted fields
    print(f"\n📝 ALL EXTRACTED FIELDS:")
    print("-" * 100)
    print(f"{'Field Name':<35} {'Value':<40} {'Type':<15} {'Method':<10}")
    print("-" * 100)
    
    for field in fields:
        field_name = field['field_name'][:34] if len(field['field_name']) > 34 else field['field_name']
        value = str(field['value'])[:39] if len(str(field['value'])) > 39 else str(field['value'])
        field_type = field['type'][:14] if len(field['type']) > 14 else field['type']
        method = field['extraction_method'][:9] if len(field['extraction_method']) > 9 else field['extraction_method']
        print(f"{field_name:<35} {value:<40} {field_type:<15} {method:<10}")
    
    # Show empty fields separately
    if [f for f in fields if f['value'] == 'NIL']:
        print(f"\n🔍 EMPTY FIELDS (marked as 'NIL'):")
        print("-" * 60)
        for field in [f for f in fields if f['value'] == 'NIL']:
            print(f"   • {field['field_name']}")
    
    # Show checkbox fields separately
    if [f for f in fields if f['type'] == 'checkbox']:
        print(f"\n☑️  CHECKBOX FIELDS:")
        print("-" * 60)
        for field in [f for f in fields if f['type'] == 'checkbox']:
            print(f"   • {field['field_name']}: {field['value']}")
    
    # Save results
    results_file = "comprehensive_lab_extraction_results.json"
    
    results = {
        'pdf_path': pdf_path,
        'file_size_bytes': os.path.getsize(pdf_path),
        'file_size_mb': round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
        'extraction_summary': {
            'total_fields': len(fields),
            'customer_samples_count': len(structured_customer_samples),
            'sample_fields': len([f for f in fields if f['type'] == 'sample_field']),
            'analysis_request_fields': len([f for f in fields if f['type'] == 'analysis_request']),
            'checkbox_fields': len([f for f in fields if f['type'] == 'checkbox']),
            'text_fields': len([f for f in fields if f['type'] == 'text']),
            'empty_fields': len([f for f in fields if f['value'] == 'NIL']),
            'other_fields': len([f for f in fields if f['type'] not in ['sample_data', 'sample_field', 'analysis_request', 'checkbox', 'text']])
        },
        'customer_samples': structured_customer_samples,
        'categorized_fields': categories,
        'organized_sample_data': sample_data,
        'extracted_fields': fields,
        'status': 'success'
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    main() 