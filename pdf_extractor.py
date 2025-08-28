import os
import json
import re
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import google.generativeai as genai
from config import GEMINI_API_KEY

class ComprehensivePDFExtractor:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(pdf_path)
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_content += f"\n--- Page {page_num + 1} ---\n"
                text_content += page.get_text()
                
            doc.close()
            return text_content
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_images_from_pdf(self, pdf_path, max_pages=5):
        """Extract images from PDF for AI vision analysis"""
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(min(len(doc), max_pages)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
                img_data = pix.tobytes("png")
                
                # Convert to base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                images.append({
                    'page': page_num + 1,
                    'image_data': img_base64,
                    'mime_type': 'image/png'
                })
                
            doc.close()
            return images
        except Exception as e:
            print(f"Error extracting images from PDF: {e}")
            return []
    
    def analyze_with_ai_vision(self, images, pdf_path):
        """Analyze PDF images using Gemini 2.0 Flash Vision"""
        try:
            # Prepare the prompt for comprehensive extraction
            prompt = """
            Analyze this Chain-of-Custody Analytical Request Document image and extract ALL information in the exact JSON format specified below.

            IMPORTANT REQUIREMENTS:
            1. Extract EVERY SINGLE field, value, checkbox, and detail visible in the document
            2. For ALL checkboxes (both box-style and bracket-style [ ]), indicate their state as "checked", "unchecked", or "NIL" if empty
            3. Map which Sample IDs are checked for which Analysis Requests
            4. If any field is empty or not filled, write "NIL" as the value
            5. Include all text fields, headers, sample information, analysis checkboxes, and any other visible elements

            SPECIFIC FIELDS TO EXTRACT:

            DOCUMENT HEADERS AND BASIC INFO:
            - Document titles and headers
            - Company/client information fields
            - Contact information and addresses

            SAMPLE INFORMATION:
            - Sample IDs (XM-15, XM-16, etc.)
            - Matrix information
            - Comp grade values
            - Start dates and times
            - End dates and times
            - Container information
            - Sample type and source

            ANALYSIS REQUEST CHECKBOXES:
            - All analysis request checkboxes for each sample ID
            - Map which Sample IDs have which Analysis Requests checked

            TECHNICAL CHECKBOXES:
            - Field Filtered if applicable
            - Any other technical checkboxes

            DATA DELIVERABLES CHECKBOXES (Look for these specific options):
            - Level II
            - Level III
            - Level IV
            - Equis
            - Others

            RUSH OPTIONS (Look for "Rush (Pre-approval required)" and these options):
            - Same Day
            - 1 Day
            - 2 Day
            - 3 Day
            - Others

            TIME ZONE COLLECTED CHECKBOXES (Look for these specific options):
            - AM
            - PT
            - MT
            - CT
            - ET

            CONTAINER INFORMATION:
            - Container Size (numbers written in boxes below container size labels)
            - Container Preservative Type (values written in boxes below preservative type labels)

            REPORTABLE CHECKBOXES (Look for "Reportable" and these options):
            - Yes
            - No

            OTHER CHECKBOXES:
            - All other checkboxes on the form
            - Delivery method checkboxes (In-Person, Courier, FedEx, UPS, Other)
            - Any additional checkbox options

            ADMINISTRATIVE FIELDS:
            - Collected By
            - Printed Name
            - Signature
            - Date/Time
            - Packing Number
            - Page numbers
            - Any other administrative fields

            RESPOND IN THIS EXACT JSON FORMAT:
            {
                "extracted_fields": [
                    {
                        "key": "field_name",
                        "value": "field_value_or_NIL",
                        "type": "header|field|sample_field|analysis_checkbox|checkbox",
                        "page": 1,
                        "method": "AI Vision"
                    }
                ],
                "all_checkboxes": {
                    "hazard_checkboxes": {},
                    "technical_checkboxes": {},
                    "administrative_checkboxes": {},
                    "analysis_checkboxes": {},
                    "data_deliverables_checkboxes": {},
                    "rush_option_checkboxes": {},
                    "timezone_checkboxes": {},
                    "reportable_checkboxes": {},
                    "other_checkboxes": {},
                    "all_checkboxes_summary": {}
                },
                "sample_analysis_mapping": {
                    "sample_ids": [],
                    "analysis_requests": [],
                    "sample_analysis_map": {}
                },
                "sample_ids": [],
                "analysis_requests": []
            }

            For sample fields, use type "sample_field" and include "sample_id" field.
            For analysis checkboxes, use type "analysis_checkbox" and include both "sample_id" and "analysis_name" fields.
            For regular checkboxes, use type "checkbox" and include "checkbox_type" field.
            For container fields, extract the actual numbers/values written in the boxes.
            """
            
            # Process each image and combine results
            all_fields = []
            all_checkboxes = {
                "hazard_checkboxes": {},
                "technical_checkboxes": {},
                "administrative_checkboxes": {},
                "analysis_checkboxes": {},
                "data_deliverables_checkboxes": {},
                "rush_option_checkboxes": {},
                "timezone_checkboxes": {},
                "reportable_checkboxes": {},
                "other_checkboxes": {},
                "all_checkboxes_summary": {}
            }
            sample_ids = []
            analysis_requests = []
            sample_analysis_map = {}
            
            for img_info in images:
                try:
                    # Create the image for Gemini
                    image_data = base64.b64decode(img_info['image_data'])
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Analyze with Gemini
                    response = self.model.generate_content([prompt, image])
                    response_text = response.text
                    
                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        result = json.loads(json_str)
                        
                        # Process extracted fields
                        if 'extracted_fields' in result:
                            for field in result['extracted_fields']:
                                field['page'] = img_info['page']
                                field['method'] = "AI Vision"
                                all_fields.append(field)
                                
                                # Categorize checkboxes
                                if field.get('type') == 'analysis_checkbox':
                                    sample_id = field.get('sample_id')
                                    analysis_name = field.get('analysis_name')
                                    if sample_id and analysis_name:
                                        if sample_id not in sample_ids:
                                            sample_ids.append(sample_id)
                                        if analysis_name not in analysis_requests:
                                            analysis_requests.append(analysis_name)
                                        
                                        if sample_id not in sample_analysis_map:
                                            sample_analysis_map[sample_id] = {}
                                        sample_analysis_map[sample_id][analysis_name] = field['value']
                                        
                                elif field.get('type') == 'sample_field':
                                    sample_id = field.get('sample_id')
                                    if sample_id and sample_id not in sample_ids:
                                        sample_ids.append(sample_id)
                                        
                                elif field.get('type') == 'checkbox':
                                    checkbox_type = field.get('checkbox_type', 'other')
                                    checkbox_key = field.get('key', 'Unknown')
                                    
                                    # Categorize specific checkbox types
                                    if 'data_deliverables' in checkbox_type.lower() or any(keyword in checkbox_key.lower() for keyword in ['level ii', 'level iii', 'level iv', 'equis']):
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['data_deliverables_checkboxes'] = {}
                                        all_checkboxes['data_deliverables_checkboxes'][checkbox_key] = field['value']
                                    elif 'rush' in checkbox_type.lower() or any(keyword in checkbox_key.lower() for keyword in ['same day', '1 day', '2 day', '3 day']):
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['rush_option_checkboxes'] = {}
                                        all_checkboxes['rush_option_checkboxes'][checkbox_key] = field['value']
                                    elif 'timezone' in checkbox_type.lower() or checkbox_key.upper() in ['AM', 'PT', 'MT', 'CT', 'ET']:
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['timezone_checkboxes'] = {}
                                        all_checkboxes['timezone_checkboxes'][checkbox_key] = field['value']
                                    elif 'reportable' in checkbox_type.lower() or checkbox_key.lower() in ['yes', 'no']:
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['reportable_checkboxes'] = {}
                                        all_checkboxes['reportable_checkboxes'][checkbox_key] = field['value']
                                    elif 'hazard' in checkbox_type.lower():
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['hazard_checkboxes'] = {}
                                        all_checkboxes['hazard_checkboxes'][checkbox_key] = field['value']
                                    elif 'technical' in checkbox_type.lower():
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['technical_checkboxes'] = {}
                                        all_checkboxes['technical_checkboxes'][checkbox_key] = field['value']
                                    elif 'administrative' in checkbox_type.lower():
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['administrative_checkboxes'] = {}
                                        all_checkboxes['administrative_checkboxes'][checkbox_key] = field['value']
                                    else:
                                        if checkbox_type not in all_checkboxes:
                                            all_checkboxes['other_checkboxes'] = {}
                                        all_checkboxes['other_checkboxes'][checkbox_key] = field['value']
                                    
                                    # Add to summary
                                    all_checkboxes['all_checkboxes_summary'][checkbox_key] = {
                                        "value": field['value'],
                                        "type": checkbox_type,
                                        "page": field['page'],
                                        "sample_id": None
                                    }
                        
                        # Process sample analysis mapping
                        if 'sample_analysis_mapping' in result:
                            mapping = result['sample_analysis_mapping']
                            if 'sample_ids' in mapping:
                                for sid in mapping['sample_ids']:
                                    if sid not in sample_ids:
                                        sample_ids.append(sid)
                            if 'analysis_requests' in mapping:
                                for ar in mapping['analysis_requests']:
                                    if ar not in analysis_requests:
                                        analysis_requests.append(ar)
                            if 'sample_analysis_map' in mapping:
                                for sid, analysis_map in mapping['sample_analysis_map'].items():
                                    if sid not in sample_analysis_map:
                                        sample_analysis_map[sid] = {}
                                    sample_analysis_map[sid].update(analysis_map)
                        
                except Exception as e:
                    print(f"Error processing image for page {img_info['page']}: {e}")
                    continue
            
            return {
                'extracted_fields': all_fields,
                'all_checkboxes': all_checkboxes,
                'sample_analysis_mapping': {
                    'sample_ids': sample_ids,
                    'analysis_requests': analysis_requests,
                    'sample_analysis_map': sample_analysis_map
                },
                'sample_ids': sample_ids,
                'analysis_requests': analysis_requests
            }
            
        except Exception as e:
            print(f"Error in AI vision analysis: {e}")
            return {
                'extracted_fields': [],
                'all_checkboxes': {
                    "hazard_checkboxes": {},
                    "technical_checkboxes": {},
                    "administrative_checkboxes": {},
                    "analysis_checkboxes": {},
                    "data_deliverables_checkboxes": {},
                    "rush_option_checkboxes": {},
                    "timezone_checkboxes": {},
                    "reportable_checkboxes": {},
                    "other_checkboxes": {},
                    "all_checkboxes_summary": {}
                },
                'sample_analysis_mapping': {
                    'sample_ids': [],
                    'analysis_requests': [],
                    'sample_analysis_map': {}
                },
                'sample_ids': [],
                'analysis_requests': []
            }
    
    def extract_comprehensive(self, pdf_path):
        """Main extraction method that combines text and vision analysis"""
        try:
            # Get file information
            file_size_bytes = os.path.getsize(pdf_path)
            file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
            
            # Extract images for AI vision analysis
            images = self.extract_images_from_pdf(pdf_path)
            
            # Perform AI vision analysis
            ai_results = self.analyze_with_ai_vision(images, pdf_path)
            
            # Calculate totals
            total_fields = len(ai_results['extracted_fields'])
            total_checkboxes = len(ai_results['all_checkboxes']['all_checkboxes_summary'])
            
            # Prepare final response
            response = {
                "status": "success",
                "pdf_path": pdf_path,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": file_size_mb,
                "extraction_methods": ["Comprehensive AI Vision"],
                "extracted_fields": ai_results['extracted_fields'],
                "all_checkboxes": ai_results['all_checkboxes'],
                "sample_analysis_mapping": ai_results['sample_analysis_mapping'],
                "total_fields": total_fields,
                "total_checkboxes": total_checkboxes,
                "sample_ids": ai_results['sample_ids'],
                "analysis_requests": ai_results['analysis_requests']
            }
            
            return response
            
        except Exception as e:
            print(f"Error in comprehensive extraction: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pdf_path": pdf_path
            }

def main():
    """Interactive PDF extraction with user input"""
    print("🔍 Comprehensive PDF Extraction System")
    print("=" * 50)
    print("This system extracts all fields, values, and checkboxes from PDF documents")
    print("using Google Gemini 2.0 Flash AI vision analysis.")
    print()
    
    # Initialize extractor
    extractor = ComprehensivePDFExtractor()
    
    while True:
        print("\nOptions:")
        print("1. Extract from a PDF file")
        print("2. Use sample PDF (OCR 35.pdf)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            # Get PDF path from user
            pdf_path = input("\n📄 Enter the full path to your PDF file: ").strip()
            
            if not pdf_path:
                print("❌ No path provided. Please try again.")
                continue
                
            if not os.path.exists(pdf_path):
                print(f"❌ File not found: {pdf_path}")
                print("Please check the path and try again.")
                continue
                
            if not pdf_path.lower().endswith('.pdf'):
                print("❌ Only PDF files are supported.")
                continue
            
            print(f"\n✅ Processing: {os.path.basename(pdf_path)}")
            print("🔍 Extracting all fields and checkboxes...")
            
        elif choice == "2":
            # Use sample PDF
            pdf_path = "Sample Documents/OCR 35.pdf"
            
            if not os.path.exists(pdf_path):
                print(f"❌ Sample PDF not found: {pdf_path}")
                print("Please ensure the sample PDF exists in the Sample Documents folder.")
                continue
                
            print(f"\n✅ Using sample PDF: {os.path.basename(pdf_path)}")
            print("🔍 Extracting all fields and checkboxes...")
            
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
            continue
        
        try:
            # Perform extraction
            result = extractor.extract_comprehensive(pdf_path)
            
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
                filename = os.path.splitext(os.path.basename(pdf_path))[0]
                output_file = f"{filename}_extraction_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 Results saved to: {output_file}")
                
                # Ask if user wants to continue
                continue_choice = input("\n🔍 Extract another PDF? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes']:
                    print("\n👋 Goodbye!")
                    break
                    
            else:
                print(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            print("Please check your PDF file and try again.")

if __name__ == "__main__":
    main()
