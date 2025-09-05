import os
import json
import re
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import google.generativeai as genai
from config import GEMINI_API_KEY
import logging
from datetime import datetime

class RestructuredPDFExtractor:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup comprehensive logging for debugging"""
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Clean up old log files to prevent disk space issues
        self.cleanup_old_logs()
            
        # Create timestamp for log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/pdf_extraction_{timestamp}.log"
        
        # Configure logging with reduced verbosity
        logging.basicConfig(
            level=logging.WARNING,  # Only log warnings and errors
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()  # Also log to console
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Restructured PDF Extractor initialized with Gemini 2.5 Flash. Log file: {log_filename}")
        print(f"Logging initialized with Gemini 2.5 Flash. Log file: {log_filename}")
        
    def cleanup_old_logs(self):
        """Clean up old log files to prevent disk space issues"""
        try:
            import glob
            import time
            
            # Keep only the last 5 log files
            log_files = glob.glob('logs/pdf_extraction_*.log')
            if len(log_files) > 5:
                # Sort by modification time and remove oldest
                log_files.sort(key=os.path.getmtime)
                for old_log in log_files[:-5]:
                    try:
                        os.remove(old_log)
                        print(f"Cleaned up old log file: {old_log}")
                    except:
                        pass
        except Exception as e:
            print(f"Warning: Could not clean up old logs: {e}")
        
    def repair_json(self, json_str):
        """Try to repair common JSON issues"""
        try:
            self.logger.info("Attempting JSON repair...")
            
            # Remove markdown code blocks if present
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'```\s*$', '', json_str)
            json_str = json_str.strip()
            
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix unescaped quotes in strings
            json_str = re.sub(r'(?<!\\)"(?=.*":)', r'\\"', json_str)
            
            # Try to close unclosed objects/arrays
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')
            
            # Add missing closing braces
            json_str += '}' * open_braces
            json_str += ']' * open_brackets
            
            # Test if it's valid now
            json.loads(json_str)
            self.logger.info("JSON repair successful")
            return json_str
            
        except Exception as e:
            self.logger.error(f"JSON repair failed: {e}")
            return None
    
    def repair_truncated_json(self, json_str):
        """Try to repair truncated JSON by finding the last complete structure"""
        try:
            self.logger.info("Attempting truncated JSON repair...")
            
            # Remove markdown code blocks if present
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'```\s*$', '', json_str)
            json_str = json_str.strip()
            
            # Find the last complete object/array by working backwards
            # Look for the last complete closing brace or bracket
            last_brace_pos = json_str.rfind('}')
            last_bracket_pos = json_str.rfind(']')
            
            if last_brace_pos > last_bracket_pos:
                # Find the matching opening brace
                brace_count = 0
                for i in range(last_brace_pos, -1, -1):
                    if json_str[i] == '}':
                        brace_count += 1
                    elif json_str[i] == '{':
                        brace_count -= 1
                        if brace_count == 0:
                            # Found the matching opening brace
                            truncated_json = json_str[:last_brace_pos + 1]
                            break
                else:
                    # If we can't find matching braces, try to close what we have
                    truncated_json = json_str
            else:
                # Find the matching opening bracket
                bracket_count = 0
                for i in range(last_bracket_pos, -1, -1):
                    if json_str[i] == ']':
                        bracket_count += 1
                    elif json_str[i] == '[':
                        bracket_count -= 1
                        if bracket_count == 0:
                            # Found the matching opening bracket
                            truncated_json = json_str[:last_bracket_pos + 1]
                            break
                else:
                    # If we can't find matching brackets, try to close what we have
                    truncated_json = json_str
            
            # Try to close any remaining unclosed structures
            open_braces = truncated_json.count('{') - truncated_json.count('}')
            open_brackets = truncated_json.count('[') - truncated_json.count(']')
            
            # Add missing closing braces
            truncated_json += '}' * open_braces
            truncated_json += ']' * open_brackets
            
            # Test if it's valid now
            result = json.loads(truncated_json)
            self.logger.info("Truncated JSON repair successful")
            return truncated_json
            
        except Exception as e:
            self.logger.error(f"Truncated JSON repair failed: {e}")
            # Try a more aggressive approach - find the largest valid JSON portion
            return self.extract_largest_valid_json(json_str)
    
    def extract_largest_valid_json(self, json_str):
        """Extract the largest valid JSON portion by progressively removing characters from the end"""
        try:
            self.logger.info("Attempting to extract largest valid JSON portion...")
            
            # Remove markdown code blocks if present
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'```\s*$', '', json_str)
            json_str = json_str.strip()
            
            # Try to find the largest valid JSON by progressively removing from the end
            original_length = len(json_str)
            
            # Start from 95% of the original length and work backwards
            for percentage in [95, 90, 85, 80, 75, 70, 65, 60, 55, 50]:
                test_length = int(original_length * percentage / 100)
                test_json = json_str[:test_length]
                
                # Try to close any unclosed structures
                open_braces = test_json.count('{') - test_json.count('}')
                open_brackets = test_json.count('[') - test_json.count(']')
                
                # Add missing closing braces
                test_json += '}' * open_braces
                test_json += ']' * open_brackets
                
                try:
                    result = json.loads(test_json)
                    self.logger.info(f"Successfully extracted valid JSON at {percentage}% of original length")
                    return test_json
                except:
                    continue
            
            # If progressive approach fails, try to find the extracted_fields array specifically
            return self.extract_extracted_fields_only(json_str)
            
        except Exception as e:
            self.logger.error(f"Largest valid JSON extraction failed: {e}")
            return None
    
    def extract_extracted_fields_only(self, json_str):
        """Extract just the extracted_fields array and create a minimal valid JSON"""
        try:
            self.logger.info("Attempting to extract extracted_fields array only...")
            
            # Remove markdown code blocks if present
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'```\s*$', '', json_str)
            json_str = json_str.strip()
            
            # Find the start of extracted_fields array
            start_marker = '"extracted_fields": ['
            start_pos = json_str.find(start_marker)
            
            if start_pos == -1:
                self.logger.error("Could not find extracted_fields array")
                return None
            
            # Find the end of the extracted_fields array by counting brackets
            array_start = start_pos + len(start_marker) - 1  # Position of the opening [
            bracket_count = 0
            end_pos = -1
            
            for i in range(array_start, len(json_str)):
                if json_str[i] == '[':
                    bracket_count += 1
                elif json_str[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i
                        break
            
            if end_pos == -1:
                # If we can't find the end, try to find the last complete field
                self.logger.info("Could not find end of extracted_fields array, looking for last complete field...")
                return self.extract_last_complete_fields(json_str, array_start)
            
            # Extract the extracted_fields array
            extracted_fields_str = json_str[start_pos:end_pos + 1]
            
            # Create a minimal valid JSON with just the extracted_fields
            minimal_json = f'{{"extracted_fields": {extracted_fields_str}, "all_checkboxes": {{"all_checkboxes_summary": {{}}}}, "sample_analysis_mapping": {{"sample_ids": [], "analysis_request": [], "sample_analysis_map": {{}}}}, "sample_ids": [], "analysis_request": []}}'
            
            # Test if it's valid
            result = json.loads(minimal_json)
            self.logger.info("Successfully extracted extracted_fields array")
            return minimal_json
            
        except Exception as e:
            self.logger.error(f"Extracted fields extraction failed: {e}")
            return None
    
    def extract_last_complete_fields(self, json_str, array_start):
        """Extract the last complete fields from the extracted_fields array"""
        try:
            self.logger.info("Attempting to extract last complete fields...")
            
            # Look for the last complete field by finding the last complete object
            # Start from the end and work backwards to find the last complete field
            last_complete_pos = -1
            
            # Find the last complete closing brace that represents a complete field
            brace_count = 0
            for i in range(len(json_str) - 1, array_start, -1):
                if json_str[i] == '}':
                    brace_count += 1
                elif json_str[i] == '{':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found a complete object, check if it's followed by a comma or closing bracket
                        if i + 1 < len(json_str) and json_str[i + 1] in [',', ']']:
                            last_complete_pos = i + 1
                            break
            
            if last_complete_pos == -1:
                # Try a more aggressive approach - find any complete object
                self.logger.info("Trying aggressive field extraction...")
                return self.extract_any_complete_fields(json_str, array_start)
            
            # Extract up to the last complete field
            partial_array = json_str[array_start:last_complete_pos]
            
            # Close the array
            if not partial_array.endswith(']'):
                partial_array += ']'
            
            # Create a minimal valid JSON
            minimal_json = f'{{"extracted_fields": {partial_array}, "all_checkboxes": {{"all_checkboxes_summary": {{}}}}, "sample_analysis_mapping": {{"sample_ids": [], "analysis_request": [], "sample_analysis_map": {{}}}}, "sample_ids": [], "analysis_request": []}}'
            
            # Test if it's valid
            result = json.loads(minimal_json)
            self.logger.info(f"Successfully extracted {len(result.get('extracted_fields', []))} complete fields")
            return minimal_json
            
        except Exception as e:
            self.logger.error(f"Last complete fields extraction failed: {e}")
            return self.extract_any_complete_fields(json_str, array_start)
    
    def extract_any_complete_fields(self, json_str, array_start):
        """Extract any complete fields from the extracted_fields array using aggressive parsing"""
        try:
            self.logger.info("Attempting aggressive field extraction...")
            
            # Find all complete field objects by looking for complete { } pairs
            fields = []
            current_field = ""
            brace_count = 0
            in_field = False
            
            for i in range(array_start, len(json_str)):
                char = json_str[i]
                current_field += char
                
                if char == '{':
                    if not in_field:
                        in_field = True
                        current_field = char
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and in_field:
                        # Found a complete field
                        try:
                            # Test if this is a valid field object
                            field_obj = json.loads(current_field)
                            if isinstance(field_obj, dict) and 'key' in field_obj:
                                fields.append(field_obj)
                                self.logger.info(f"Found valid field: {field_obj.get('key', 'unknown')}")
                        except:
                            pass  # Skip invalid fields
                        in_field = False
                        current_field = ""
            
            if fields:
                # Create a valid JSON with the extracted fields
                fields_json = json.dumps(fields)
                minimal_json = f'{{"extracted_fields": {fields_json}, "all_checkboxes": {{"all_checkboxes_summary": {{}}}}, "sample_analysis_mapping": {{"sample_ids": [], "analysis_request": [], "sample_analysis_map": {{}}}}, "sample_ids": [], "analysis_request": []}}'
                
                # Test if it's valid
                result = json.loads(minimal_json)
                self.logger.info(f"Successfully extracted {len(fields)} fields using aggressive parsing")
                return minimal_json
            else:
                self.logger.error("No valid fields found using aggressive parsing")
                return None
                
        except Exception as e:
            self.logger.error(f"Aggressive field extraction failed: {e}")
            return None
    
    def emergency_field_extraction(self, json_str):
        """Emergency field extraction - extract any recognizable field patterns"""
        try:
            self.logger.info("Attempting emergency field extraction...")
            
            # Look for any field-like patterns in the JSON string
            fields = []
            
            # Find all potential field objects using regex
            import re
            
            # Look for field patterns like {"key": "...", "value": "...", "type": "..."}
            field_pattern = r'\{\s*"key"\s*:\s*"[^"]*"\s*,\s*"value"\s*:\s*"[^"]*"\s*,\s*"type"\s*:\s*"[^"]*"'
            matches = re.findall(field_pattern, json_str, re.IGNORECASE)
            
            for match in matches:
                try:
                    # Try to parse this as a field object
                    field_obj = json.loads(match + '}')
                    if isinstance(field_obj, dict) and 'key' in field_obj and 'value' in field_obj:
                        # Add default values for missing fields
                        field_obj.setdefault('page', 1)
                        field_obj.setdefault('method', 'AI Vision')
                        fields.append(field_obj)
                        self.logger.info(f"Emergency extraction found field: {field_obj.get('key', 'unknown')}")
                except:
                    pass  # Skip invalid matches
            
            if fields:
                # Create a valid JSON with the extracted fields
                fields_json = json.dumps(fields)
                minimal_json = f'{{"extracted_fields": {fields_json}, "all_checkboxes": {{"all_checkboxes_summary": {{}}}}, "sample_analysis_mapping": {{"sample_ids": [], "analysis_request": [], "sample_analysis_map": {{}}}}, "sample_ids": [], "analysis_request": []}}'
                
                # Test if it's valid
                result = json.loads(minimal_json)
                self.logger.info(f"Emergency extraction found {len(fields)} fields")
                return minimal_json
            else:
                self.logger.error("No fields found in emergency extraction")
                return None
                
        except Exception as e:
            self.logger.error(f"Emergency field extraction failed: {e}")
            return None
        
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
            self.logger.info(f"Starting image extraction from: {pdf_path}")
            self.logger.info(f"Max pages to process: {max_pages}")
            
            doc = fitz.open(pdf_path)
            images = []
            
            self.logger.info(f"PDF has {len(doc)} pages, processing {min(len(doc), max_pages)}")
            
            for page_num in range(min(len(doc), max_pages)):
                self.logger.info(f"Processing page {page_num + 1}/{min(len(doc), max_pages)}")
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
                
                self.logger.info(f"Page {page_num + 1} image size: {len(img_data)} bytes ({len(img_data)/1024/1024:.2f} MB)")
                self.logger.info(f"Page {page_num + 1} base64 size: {len(img_base64)} chars ({len(img_base64)/1024/1024:.2f} MB)")
                
            doc.close()
            self.logger.info(f"Image extraction completed. Total images: {len(images)}")
            return images
        except Exception as e:
            self.logger.error(f"Error extracting images from PDF: {e}")
            print(f"Error extracting images from PDF: {e}")
            return []
    
    def normalize_checkbox_value(self, value):
        """Normalize checkbox values to 'checked' or 'unchecked'"""
        if not value or value.lower() in ['nil', 'n/a', '-', '']:
            return 'unchecked'
        elif value.lower() in ['checked', 'x', '✓', 'yes', 'y']:
            return 'checked'
        else:
            return 'unchecked'
    
    def analyze_with_ai_vision(self, images, pdf_path):
        """Analyze PDF images using Gemini 2.0 Flash Vision"""
        try:
            self.logger.info(f"Starting AI vision analysis for {len(images)} images")
            self.logger.info(f"PDF path: {pdf_path}")
            
            # Prepare the prompt for comprehensive extraction
            prompt = """
            Analyze this Chain-of-Custody Analytical Request Document image and extract ALL information in the exact JSON format specified below.

            CRITICAL INSTRUCTIONS:
            1. Return ONLY valid JSON - no markdown, no explanations, no extra text
            2. Ensure all strings are properly escaped
            3. Ensure all arrays and objects are properly closed
            4. Do not include trailing commas
            5. Keep the response focused and concise

            IMPORTANT REQUIREMENTS:
            1. Extract EVERY SINGLE field, value, checkbox, and detail visible in the document
            2. For ALL checkboxes (both box-style and bracket-style [ ]), indicate their state as "checked" or "unchecked" (NOT "-" or "NIL")
            3. Map which Sample IDs are checked for which Analysis Requests
            4. If any field is empty or not filled, write "NIL" as the value
            5. Include all text fields, headers, sample information, analysis checkboxes, and any other visible elements
            6. For R & C Work Order format, extract parameter checkboxes with their associated metadata (Filtered, Cooled, Container Type, etc.)
            
            CRITICAL ANALYSIS CHECKBOX EXTRACTION:
            - Look for analysis code checkboxes (8240, 8080, TPH, etc.) for each sample
            - If a checkbox is marked/checked for a sample, set value to "checked"
            - If a checkbox is empty/unmarked for a sample, set value to "unchecked"
            - Use type "analysis_checkbox" and include both "sample_id" and "analysis_name" fields
            - Example: {"key": "analysis_8240_dw01", "value": "checked", "type": "analysis_checkbox", "sample_id": "DW-01", "analysis_name": "8240"}
            - Pay special attention to which analysis codes are checked for each sample ID

            SPECIAL INSTRUCTIONS FOR R & C WORK ORDER FORMAT:
            If you see fields like "R & C Work Order", "YR__ DATE", "TIME", "SAMPLE DESCRIPTION", "Total Number of Containers", 
            "Filtered (Y/N)", "Cooled (Y/N)", "Container Type", "Container Volume", "Sample Type", "Sample Source", 
            then this is an R & C Work Order format. For this format:
            - Use field names exactly as: "r_and_c_work_order", "yr_date", "time", "sample_description", "total_number_of_containers"
            - Use field names for metadata: "filtered_yes_no", "cooled_yes_no", "container_type_plastic_glass", "container_volume_ml", "sample_type_grab_composite", "sample_source_ww_gw_dw_sw_s_other"
            - For parameter checkboxes, use field names like "parameter_8260", "parameter_8270", etc.
            - Always include the "sample_id" field for sample-related data

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
                    "analysis_request": [],
                    "sample_analysis_map": {}
                },
                "sample_ids": [],
                "analysis_request": []
            }

            For sample fields, use type "sample_field" and include "sample_id" field.
            For analysis checkboxes, use type "analysis_checkbox" and include both "sample_id" and "analysis_name" fields.
            For regular checkboxes, use type "checkbox" and include "checkbox_type" field.
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
            analysis_request = []
            sample_analysis_map = {}
            
            for img_info in images:
                try:
                    self.logger.info(f"Processing {len(images)} images for AI analysis")
                    self.logger.info(f"Processing page {img_info['page']} for AI vision analysis")
                    
                    # Create the image for Gemini
                    self.logger.info(f"Decoding base64 image for page {img_info['page']}")
                    image_data = base64.b64decode(img_info['image_data'])
                    image = Image.open(io.BytesIO(image_data))
                    self.logger.info(f"Image created successfully. Size: {image.size}")
                    
                    # Analyze with Gemini with retry mechanism
                    self.logger.info(f"Sending request to Gemini AI for page {img_info['page']}")
                    response = None
                    response_text = ""
                    
                    # Retry mechanism for AI requests
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            response = self.model.generate_content([prompt, image])
                            response_text = response.text
                            if response_text and len(response_text) > 100:  # Basic quality check
                                break
                            else:
                                self.logger.warning(f"Attempt {attempt + 1}: Poor response quality, retrying...")
                        except Exception as e:
                            self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                            if attempt == max_retries - 1:
                                raise e
                            import time
                            time.sleep(2)  # Wait before retry
                    
                    if not response_text:
                        self.logger.error(f"All retry attempts failed for page {img_info['page']}")
                        continue
                    
                    self.logger.info(f"AI Response received for page {img_info['page']}")
                    self.logger.info(f"Response length: {len(response_text)} characters")
                    self.logger.info(f"Response preview (first 500 chars): {response_text[:500]}")
                    
                    # Save raw response for debugging
                    debug_filename = f"debug_ai_response_page_{img_info['page']}.txt"
                    with open(debug_filename, 'w', encoding='utf-8') as f:
                        f.write(response_text)
                    self.logger.info(f"Raw AI response saved to: {debug_filename}")
                    
                    # Extract JSON from response
                    self.logger.info(f"Extracting JSON from AI response for page {img_info['page']}")
                    self.logger.info(f"Removing markdown code blocks from response")
                    
                    # Clean the response
                    cleaned_response = response_text
                    cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
                    cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
                    self.logger.info(f"Cleaned response length: {len(cleaned_response)} characters")
                    
                    # Find JSON match
                    json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        self.logger.info(f"Found JSON match. Length: {len(json_str)} characters")
                        
                        # Try to trim to last complete brace
                        last_brace = json_str.rfind('}')
                        if last_brace > 0:
                            json_str = json_str[:last_brace + 1]
                            self.logger.info(f"Trimmed JSON to last brace. New length: {len(json_str)} characters")
                        
                        # Attempt to parse JSON
                        self.logger.info(f"Attempting to parse JSON for page {img_info['page']}")
                        result = None
                        try:
                            result = json.loads(json_str)
                            self.logger.info(f"JSON parsing successful for page {img_info['page']}")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON parsing error on page {img_info['page']}: {e}")
                            self.logger.error(f"Problematic JSON (first 500 chars): {json_str[:500]}")
                            self.logger.error(f"Problematic JSON (last 500 chars): {json_str[-500:]}")
                            
                            # Try to repair JSON
                            self.logger.info(f"Attempting advanced JSON repair for page {img_info['page']}")
                            repaired_json = self.repair_json(json_str)
                            if repaired_json:
                                try:
                                    result = json.loads(repaired_json)
                                    self.logger.info(f"Partial JSON extraction successful for page {img_info['page']}")
                                except:
                                    # Try truncated JSON repair as fallback
                                    self.logger.info(f"Trying truncated JSON repair for page {img_info['page']}")
                                    truncated_json = self.repair_truncated_json(json_str)
                                    if truncated_json:
                                        try:
                                            result = json.loads(truncated_json)
                                            self.logger.info(f"Truncated JSON extraction successful for page {img_info['page']}")
                                        except Exception as e:
                                            self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}: {e}")
                                            continue
                                    else:
                                        # Try emergency field extraction as last resort
                                        self.logger.info(f"Trying emergency field extraction for page {img_info['page']}")
                                        emergency_json = self.emergency_field_extraction(json_str)
                                        if emergency_json:
                                            try:
                                                result = json.loads(emergency_json)
                                                self.logger.info(f"Emergency field extraction successful for page {img_info['page']}")
                                            except Exception as e:
                                                self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}: {e}")
                                                continue
                                        else:
                                            self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}")
                                            continue
                            else:
                                # Try truncated JSON repair as fallback
                                self.logger.info(f"Trying truncated JSON repair for page {img_info['page']}")
                                truncated_json = self.repair_truncated_json(json_str)
                                if truncated_json:
                                    try:
                                        result = json.loads(truncated_json)
                                        self.logger.info(f"Truncated JSON extraction successful for page {img_info['page']}")
                                    except Exception as e:
                                        self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}: {e}")
                                        continue
                                else:
                                    # Try emergency field extraction as last resort
                                    self.logger.info(f"Trying emergency field extraction for page {img_info['page']}")
                                    emergency_json = self.emergency_field_extraction(json_str)
                                    if emergency_json:
                                        try:
                                            result = json.loads(emergency_json)
                                            self.logger.info(f"Emergency field extraction successful for page {img_info['page']}")
                                        except Exception as e:
                                            self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}: {e}")
                                            continue
                                    else:
                                        # Try emergency field extraction as last resort
                                        self.logger.info(f"Trying emergency field extraction for page {img_info['page']}")
                                        emergency_json = self.emergency_field_extraction(json_str)
                                        if emergency_json:
                                            try:
                                                result = json.loads(emergency_json)
                                                self.logger.info(f"Emergency field extraction successful for page {img_info['page']}")
                                            except Exception as e:
                                                self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}: {e}")
                                                continue
                                        else:
                                            self.logger.error(f"All JSON repair attempts failed for page {img_info['page']}")
                                            continue
                        
                        # Skip processing if no valid result was obtained
                        if result is None:
                            self.logger.error(f"No valid JSON result for page {img_info['page']}, skipping")
                            continue
                        
                        # Process extracted fields
                        if 'extracted_fields' in result:
                            self.logger.info(f"Processing {len(result['extracted_fields'])} extracted fields for page {img_info['page']}")
                            for field in result['extracted_fields']:
                                field['page'] = img_info['page']
                                field['method'] = "AI Vision"
                                
                                # Normalize checkbox values
                                if field.get('type') in ['checkbox', 'analysis_checkbox']:
                                    field['value'] = self.normalize_checkbox_value(field.get('value', ''))
                                
                                all_fields.append(field)
                                
                                # Categorize checkboxes
                                if field.get('type') == 'analysis_checkbox':
                                    sample_id = field.get('sample_id')
                                    analysis_name = field.get('analysis_name')
                                    if sample_id and analysis_name:
                                        if sample_id not in sample_ids:
                                            sample_ids.append(sample_id)
                                        if analysis_name not in analysis_request:
                                            analysis_request.append(analysis_name)
                                        
                                        if sample_id not in sample_analysis_map:
                                            sample_analysis_map[sample_id] = {}
                                        sample_analysis_map[sample_id][analysis_name] = field['value']
                                        
                                elif field.get('type') == 'sample_field':
                                    # Handle multiple formats:
                                    # 1. Old format: field.get('sample_id')
                                    # 2. New format: key='sample_id', value='DW-01'
                                    # 3. Latest format: key='dw_01_sample_id', value='DW-01'
                                    # 4. Current format: key='customer_sample_id', value='DW-01'
                                    sample_id = field.get('sample_id')
                                    if not sample_id:
                                        key = field.get('key', '')
                                        if key in ['sample_id', 'customer_sample_id', 'customer sample id'] or key.endswith('_sample_id'):
                                            sample_id = field.get('value')
                                    if sample_id and sample_id not in sample_ids:
                                        sample_ids.append(sample_id)
                                        
                                elif field.get('type') == 'checkbox':
                                    checkbox_type = field.get('checkbox_type', 'other')
                                    checkbox_key = field.get('key', 'Unknown')
                                    
                                    # Categorize specific checkbox types
                                    if 'data_deliverables' in checkbox_type.lower() or any(keyword in checkbox_key.lower() for keyword in ['level ii', 'level iii', 'level iv', 'equis']):
                                        all_checkboxes['data_deliverables_checkboxes'][checkbox_key] = field['value']
                                    elif 'rush' in checkbox_type.lower() or any(keyword in checkbox_key.lower() for keyword in ['same day', '1 day', '2 day', '3 day']):
                                        all_checkboxes['rush_option_checkboxes'][checkbox_key] = field['value']
                                    elif 'timezone' in checkbox_type.lower() or checkbox_key.upper() in ['AM', 'PT', 'MT', 'CT', 'ET']:
                                        all_checkboxes['timezone_checkboxes'][checkbox_key] = field['value']
                                    elif 'reportable' in checkbox_type.lower() or checkbox_key.lower() in ['yes', 'no']:
                                        all_checkboxes['reportable_checkboxes'][checkbox_key] = field['value']
                                    elif 'hazard' in checkbox_type.lower():
                                        all_checkboxes['hazard_checkboxes'][checkbox_key] = field['value']
                                    elif 'technical' in checkbox_type.lower():
                                        all_checkboxes['technical_checkboxes'][checkbox_key] = field['value']
                                    elif 'administrative' in checkbox_type.lower():
                                        all_checkboxes['administrative_checkboxes'][checkbox_key] = field['value']
                                    else:
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
                            if 'analysis_request' in mapping:
                                for ar in mapping['analysis_request']:
                                    if ar not in analysis_request:
                                        analysis_request.append(ar)
                            if 'sample_analysis_map' in mapping:
                                for sid, analysis_map in mapping['sample_analysis_map'].items():
                                    if sid not in sample_analysis_map:
                                        sample_analysis_map[sid] = {}
                                    if isinstance(analysis_map, dict):
                                        sample_analysis_map[sid].update(analysis_map)
                        
                except Exception as e:
                    self.logger.error(f"Error processing image for page {img_info['page']}: {e}")
                    print(f"Error processing image for page {img_info['page']}: {e}")
                    continue
            
            self.logger.info(f"AI vision analysis completed")
            self.logger.info(f"Extraction Summary:")
            self.logger.info(f"Total fields: {len(all_fields)}")
            self.logger.info(f"Total checkboxes: {len(all_checkboxes['all_checkboxes_summary'])}")
            self.logger.info(f"Sample IDs: {len(sample_ids)}")
            self.logger.info(f"Analysis requests: {len(analysis_request)}")
            
            return {
                'extracted_fields': all_fields,
                'all_checkboxes': all_checkboxes,
                'sample_analysis_mapping': {
                    'sample_ids': sample_ids,
                    'analysis_request': analysis_request,
                    'sample_analysis_map': sample_analysis_map
                },
                'sample_ids': sample_ids,
                'analysis_request': analysis_request
            }
            
        except Exception as e:
            self.logger.error(f"Error in AI vision analysis: {e}")
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
                    'analysis_request': [],
                    'sample_analysis_map': {}
                },
                'sample_ids': [],
                'analysis_request': []
            }
    
    def validate_field_value(self, field_key, field_value, field_type):
        """Validate and score field values for confidence"""
        key = str(field_key).lower().strip()
        value = str(field_value).strip() if field_value else ""
        
        confidence_score = 0.5  # Default medium confidence
        validation_notes = []
        
        # Skip validation for NIL values
        if value.upper() in ['NIL', 'N/A', '-', '', 'NULL', 'EMPTY']:
            return "NIL", confidence_score, ["Empty field"]
        
        # Email validation
        if 'email' in key:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, value):
                confidence_score = 0.9
                validation_notes.append("Valid email format")
            else:
                confidence_score = 0.3
                validation_notes.append("Invalid email format")
        
        # Phone number validation
        elif 'phone' in key:
            import re
            phone_pattern = r'^[\d\s\-\(\)\+\.]+$'
            if re.match(phone_pattern, value) and len(value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '').replace('.', '')) >= 10:
                confidence_score = 0.8
                validation_notes.append("Valid phone format")
            else:
                confidence_score = 0.4
                validation_notes.append("Questionable phone format")
        
        # Date validation
        elif 'date' in key:
            import re
            date_patterns = [
                r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$',  # MM-DD-YY or MM/DD/YYYY
                r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$',  # DD-MM-YY or DD/MM/YYYY
                r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$'     # YYYY-MM-DD
            ]
            if any(re.match(pattern, value) for pattern in date_patterns):
                confidence_score = 0.8
                validation_notes.append("Valid date format")
            else:
                confidence_score = 0.4
                validation_notes.append("Questionable date format")
        
        # Time validation
        elif 'time' in key:
            import re
            time_patterns = [
                r'^\d{1,2}:\d{2}$',      # HH:MM
                r'^\d{3,4}$',            # HHMM
                r'^\d{1,2}:\d{2}\s*[AP]M$'  # HH:MM AM/PM
            ]
            if any(re.match(pattern, value.upper()) for pattern in time_patterns):
                confidence_score = 0.8
                validation_notes.append("Valid time format")
            else:
                confidence_score = 0.4
                validation_notes.append("Questionable time format")
        
        # Sample ID validation
        elif 'sample' in key and 'id' in key:
            import re
            if re.match(r'^[A-Z]{1,3}-\d{1,3}[A-Z]?$', value.upper()):
                confidence_score = 0.9
                validation_notes.append("Valid sample ID format")
            elif re.match(r'^[A-Z]{1,3}\d{1,3}[A-Z]?$', value.upper()):
                confidence_score = 0.8
                validation_notes.append("Valid sample ID format (no dash)")
            else:
                confidence_score = 0.5
                validation_notes.append("Non-standard sample ID format")
        
        # Analysis code validation
        elif 'analysis' in key or any(code in value.upper() for code in ['8240', '8080', 'TPH', '8260', '8270']):
            import re
            if re.match(r'^\d{4}$', value) or value.upper() in ['TPH', 'VOC', 'SVOC', 'PESTICIDES']:
                confidence_score = 0.9
                validation_notes.append("Valid analysis code")
            else:
                confidence_score = 0.6
                validation_notes.append("Questionable analysis code")
        
        # Matrix type validation
        elif 'matrix' in key:
            valid_matrices = ['DW', 'SW', 'GW', 'WW', 'S', 'SOIL', 'AIR', 'WATER']
            if value.upper() in valid_matrices:
                confidence_score = 0.9
                validation_notes.append("Valid matrix type")
            else:
                confidence_score = 0.6
                validation_notes.append("Non-standard matrix type")
        
        # Comp/Grab validation
        elif 'comp' in key or 'grab' in key:
            if value.upper() in ['G', 'C', 'Grab', 'Composite', 'Grab Sample', 'Composite Sample']:
                confidence_score = 0.9
                validation_notes.append("Valid comp/grab value")
            else:
                confidence_score = 0.6
                validation_notes.append("Non-standard comp/grab value")
        
        # Container count validation
        elif 'container' in key or 'cont' in key:
            if value.isdigit() and 1 <= int(value) <= 100:
                confidence_score = 0.8
                validation_notes.append("Reasonable container count")
            elif value.isdigit():
                confidence_score = 0.6
                validation_notes.append("Unusual container count")
            else:
                confidence_score = 0.4
                validation_notes.append("Non-numeric container count")
        
        # General text validation
        else:
            if len(value) > 0:
                confidence_score = 0.7
                validation_notes.append("Non-empty text field")
            else:
                confidence_score = 0.3
                validation_notes.append("Empty text field")
        
        return value, confidence_score, validation_notes
    
    def restructure_sample_data(self, sample_data_fields, sample_ids, analysis_request, sample_analysis_map):
        """Restructure sample data to group by Customer Sample ID"""
        restructured_data = []
        
        # Group fields by sample ID for better processing
        sample_field_groups = {}
        current_sample_id = None
        
        for field in sample_data_fields:
            if field.get('type') == 'sample_field':
                # Check if this field has a sample_id attribute
                sample_id = field.get('sample_id')
                if sample_id:
                    current_sample_id = sample_id
                    if sample_id not in sample_field_groups:
                        sample_field_groups[sample_id] = []
                    sample_field_groups[sample_id].append(field)
                else:
                    # If no sample_id attribute, check if this is a sample_id field itself
                    key = str(field.get('key', '')).lower()
                    if key == 'sample_id':
                        current_sample_id = field.get('value')
                        if current_sample_id and current_sample_id not in sample_field_groups:
                            sample_field_groups[current_sample_id] = []
                    elif current_sample_id:
                        # Associate this field with the current sample ID
                        if current_sample_id not in sample_field_groups:
                            sample_field_groups[current_sample_id] = []
                        sample_field_groups[current_sample_id].append(field)
        
        # Create a mapping of field types to their values for fallback
        field_type_mapping = {}
        for field in sample_data_fields:
            if field.get('type') == 'sample_field':
                key = str(field.get('key', '')).lower()
                value = field.get('value', 'NIL')
                if key not in field_type_mapping:
                    field_type_mapping[key] = []
                field_type_mapping[key].append(value)
        
        for sample_id in sample_ids:
            self.logger.debug(f"Original sample_id from list: '{sample_id}'")
            sample_info = {
                "Customer Sample ID": sample_id,
                "Matrix": "NIL",
                "Comp/Grab": "NIL", 
                "Composite Start Date": "NIL",
                "Composite Start Time": "NIL",
                "Composite or Collected End Date": "NIL",
                "Composite or Collected End Time": "NIL",
                "# Cont": "NIL",
                "Residual Chloride Result": "NIL",
                "Residual Chloride Units": "NIL",
                "Sample Comment": "NIL",
                "analysis_request": {}
            }
            
            # Extract sample-specific fields from the grouped data
            if sample_id in sample_field_groups:
                for field in sample_field_groups[sample_id]:
                    key = str(field.get('key', '')).lower()
                    value = field.get('value', 'NIL')
                    
                    # Map field names to our structure with more comprehensive matching
                    # Handle field names that include sample ID (e.g., "matrix_dw_01", "collected_date_start_01", "dw_01_matrix", "matrix_01")
                    # Handle numbered field patterns like "matrix_1", "comp_grab_1", etc.
                    if (key.startswith("matrix_") or key.endswith("_matrix") or 
                        key.startswith("matrix_type_sample_") or key.endswith("_matrix_type_sample") or
                        key == "matrix"):
                        sample_info["Matrix"] = value
                    elif (key.startswith("comp_grab_") or key.endswith("_comp_grab") or 
                          key.startswith("grab_comp_") or key.endswith("_grab_comp") or
                          key in ["comp/grab", "comp_grab", "composite_grab", "grab_comp"]):
                        sample_info["Comp/Grab"] = value
                    elif (key.startswith("collected_date_start_") or key.endswith("_collected_date_start") or 
                          key.startswith("collected_date_mf_p_i") or key.endswith("_collected_date_mf_p_i") or
                          key.startswith("date_sh_50") or key.endswith("_date_sh_50") or
                          key.startswith("date_collected_sh_50") or key.endswith("_date_collected_sh_50") or
                          key.startswith("composite_start_date_") or key.endswith("_composite_start_date") or
                          key.startswith("collected_as_composite_start_date_") or key.endswith("_collected_as_composite_start_date") or
                          key.startswith("collected_or_composite_start_date_") or key.endswith("_collected_or_composite_start_date") or
                          key.startswith("collected_date_") or key.endswith("_collected_date") or
                          key in ["composite_start_date", "composite start date", "collected_date_mf_p_i", "date_sh_50", "date_collected_sh_50"]):
                        sample_info["Composite Start Date"] = value
                    elif (key.startswith("collected_time_start_") or key.endswith("_collected_time_start") or 
                          key.startswith("collected_time_mf_p_i") or key.endswith("_collected_time_mf_p_i") or
                          key.startswith("time_sh_50") or key.endswith("_time_sh_50") or
                          key.startswith("time_collected_sh_50") or key.endswith("_time_collected_sh_50") or
                          key.startswith("composite_start_time_") or key.endswith("_composite_start_time") or
                          key.startswith("collected_as_composite_start_time_") or key.endswith("_collected_as_composite_start_time") or
                          key.startswith("collected_or_composite_start_time_") or key.endswith("_collected_or_composite_start_time") or
                          key.startswith("collected_time_") or key.endswith("_collected_time") or
                          key == "time_collected_composite_start" or key in ["composite_start_time", "composite start time", "collected_time_mf_p_i", "time_sh_50", "time_collected_sh_50"]):
                        sample_info["Composite Start Time"] = value
                    elif (key.startswith("collected_date_end_") or key.endswith("_collected_date_end") or 
                          key.startswith("collected_as_composite_end_date_") or key.endswith("_collected_as_composite_end_date") or
                          key.startswith("collected_at_composite_end_date_") or key.endswith("_collected_at_composite_end_date") or
                          key.startswith("collected_or_composite_end_date_") or key.endswith("_collected_or_composite_end_date") or
                          key.startswith("composite_end_date_") or key.endswith("_composite_end_date") or
                          key in ["composite_end_date", "composite end date", "collected_composite_end_date", "collected or composite end date", "date_collected_composite_end", "collected_or_composite_end_date"] or 
                          key.startswith("collected_composite_end_date_")):
                        sample_info["Composite or Collected End Date"] = value
                    elif (key.startswith("collected_time_end_") or key.endswith("_collected_time_end") or 
                          key.startswith("collected_as_composite_end_time_") or key.endswith("_collected_as_composite_end_time") or
                          key.startswith("collected_at_composite_end_time_") or key.endswith("_collected_at_composite_end_time") or
                          key.startswith("collected_or_composite_end_time_") or key.endswith("_collected_or_composite_end_time") or
                          key.startswith("composite_end_time_") or key.endswith("_composite_end_time") or
                          key == "time_collected_composite_end" or key in ["composite_end_time", "composite end time", "collected_composite_end_time", "collected or composite end time", "collected_or_composite_end_time"] or 
                          key.startswith("collected_composite_end_time_")):
                        sample_info["Composite or Collected End Time"] = value
                    # Handle the exact field names that the AI is currently using
                    elif key == "collected_or_composite_end_date":
                        sample_info["Composite or Collected End Date"] = value
                    elif key == "collected_or_composite_end_time":
                        sample_info["Composite or Collected End Time"] = value
                    # Handle specific field patterns mentioned in user examples
                    elif key.startswith("collected_or_composite_end_date_laj_410") or key.endswith("_collected_or_composite_end_date_laj_410"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("collected_or_composite_end_time_laj_410") or key.endswith("_collected_or_composite_end_time_laj_410"):
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("collected_at_composite_end_date_laj_410") or key.endswith("_collected_at_composite_end_date_laj_410"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("collected_at_composite_end_time_laj_410") or key.endswith("_collected_at_composite_end_time_laj_410"):
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("collected_composite_end_date_yot_810") or key.endswith("_collected_composite_end_date_yot_810"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("collected_composite_end_time_yot_810") or key.endswith("_collected_composite_end_time_yot_810"):
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("composite_start_date_laj_410") or key.endswith("_composite_start_date_laj_410"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("composite_start_time_laj_410") or key.endswith("_composite_start_time_laj_410"):
                        sample_info["Composite Start Time"] = value
                    elif key.startswith("collected_as_composite_start_date_eqo_271") or key.endswith("_collected_as_composite_start_date_eqo_271"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("collected_as_composite_start_time_eqo_271") or key.endswith("_collected_as_composite_start_time_eqo_271"):
                        sample_info["Composite Start Time"] = value
                    elif key.startswith("collected_as_composite_start_date_") or key.endswith("_collected_as_composite_start_date"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("collected_as_composite_start_time_") or key.endswith("_collected_as_composite_start_time"):
                        sample_info["Composite Start Time"] = value
                    elif key.startswith("collected_date_mw") or key.endswith("_collected_date_mw"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("collected_time_mw") or key.endswith("_collected_time_mw"):
                        sample_info["Composite Start Time"] = value
                    elif key.startswith("collected_date_sw") or key.endswith("_collected_date_sw"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("collected_time_sw") or key.endswith("_collected_time_sw"):
                        sample_info["Composite Start Time"] = value
                    elif key.startswith("collected_date_ss") or key.endswith("_collected_date_ss"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("collected_time_ss") or key.endswith("_collected_time_ss"):
                        sample_info["Composite Start Time"] = value
                    # Handle matrix_grab_code fields that combine both Matrix and Comp/Grab
                    elif key.startswith("matrix_grab_code_") or key.endswith("_matrix_grab_code"):
                        # This field contains both Matrix and Comp/Grab combined (e.g., "B2")
                        # We'll store it in Matrix for now and separate it later
                        sample_info["Matrix"] = value
                    # Handle result_units fields that combine both result and units
                    elif key.startswith("result_units_") or key.endswith("_result_units"):
                        # This field contains both result and units combined (e.g., "0.5 mg")
                        # We'll store it in Residual Chloride Result for now and separate it later
                        sample_info["Residual Chloride Result"] = value
                    # Handle grab_comp fields specifically (e.g., grab_comp_MF_P1)
                    elif key.startswith("grab_comp_") or key.endswith("_grab_comp"):
                        sample_info["Comp/Grab"] = value
                    # Handle fields with sample ID suffixes
                    elif key.startswith("collected_or_composite_end_date_") and key.endswith(f"_{sample_id.replace(' ', '_').replace('-', '_')}"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("collected_or_composite_end_time_") and key.endswith(f"_{sample_id.replace(' ', '_').replace('-', '_')}"):
                        sample_info["Composite or Collected End Time"] = value
                    # Handle container count fields
                    elif (key.startswith("number_of_containers_") or key.endswith("_number_of_containers") or
                          key.startswith("num_containers_") or key.endswith("_num_containers") or
                          key.startswith("num_cont_") or key.endswith("_num_cont") or
                          key.startswith("container_count_") or key.endswith("_container_count") or
                          key in ["number_of_containers", "num_containers", "num_cont", "container_count", "# cont", "cont"]):
                        sample_info["# Cont"] = value
                    # Handle result fields
                    elif (key.startswith("result_") or key.endswith("_result") or
                          key.startswith("residual_chloride_result_") or key.endswith("_residual_chloride_result") or
                          key in ["result", "residual_chloride_result", "residual chloride result"]):
                        sample_info["Residual Chloride Result"] = value
                    # Handle units fields
                    elif (key.startswith("units_") or key.endswith("_units") or
                          key.startswith("residual_chloride_units_") or key.endswith("_residual_chloride_units") or
                          key in ["units", "residual_chloride_units", "residual chloride units"]):
                        sample_info["Residual Chloride Units"] = value
                    # Handle the new field naming patterns from the current AI extraction
                    elif key.startswith("dw_") and key.endswith("_matrix"):
                        sample_info["Matrix"] = value
                    elif key.startswith("matrix_dw-") or key.startswith("matrix_dw_"):
                        sample_info["Matrix"] = value
                    # Handle sample_YOT_*_matrix_code pattern
                    elif key.startswith("sample_") and key.endswith("_matrix_code"):
                        sample_info["Matrix"] = value
                    # Handle sample_YOT_*_collected_start_date pattern (with underscores or hyphens)
                    elif key.startswith("sample_") and (key.endswith("_collected_start_date") or key.endswith("-collected_start_date")):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("sample_") and (key.endswith("_collected_start_time") or key.endswith("-collected_start_time")):
                        sample_info["Composite Start Time"] = value
                    # Handle collected_start_date and collected_start_time patterns (with underscores or hyphens)
                    elif key.startswith("collected_start_date_") or key.endswith("_collected_start_date") or key.startswith("collected_start_date-") or key.endswith("-collected_start_date"):
                        sample_info["Composite Start Date"] = value
                    elif key.startswith("collected_start_time_") or key.endswith("_collected_start_time") or key.startswith("collected_start_time-") or key.endswith("-collected_start_time"):
                        sample_info["Composite Start Time"] = value
                    # Handle collected_end_date and collected_end_time patterns (with underscores or hyphens)
                    elif key.startswith("collected_end_date_") or key.endswith("_collected_end_date") or key.startswith("collected_end_date-") or key.endswith("-collected_end_date"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("collected_end_time_") or key.endswith("_collected_end_time") or key.startswith("collected_end_time-") or key.endswith("-collected_end_time"):
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("dw_") and key.endswith("_comp_grab"):
                        sample_info["Comp/Grab"] = value
                    elif key.startswith("comp_grab_dw-") or key.startswith("comp_grab_dw_"):
                        sample_info["Comp/Grab"] = value
                    elif key.startswith("dw_") and key.endswith("_collected_or_composite_end_date"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("collected_composite_end_date_dw-") or key.startswith("collected_or_composite_end_date_dw-") or key.startswith("collected_or_composite_end_date_dw"):
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("dw_") and key.endswith("_collected_or_composite_end_time"):
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("collected_composite_end_time_dw-") or key.startswith("collected_or_composite_end_time_dw-") or key.startswith("collected_or_composite_end_time_dw"):
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("dw_") and key.endswith("_number_of_containers") or key.startswith("number_of_containers_dw") or key.startswith("num_containers_dw") or key.startswith("num_cont_dw"):
                        sample_info["# Cont"] = value
                    elif key.startswith("number_of_containers_dw-") or key.startswith("number_of_containers_dw_") or key.startswith("num_containers_dw-") or key.startswith("num_containers_dw_") or key.startswith("num_cont_dw-") or key.startswith("num_cont_dw_"):
                        sample_info["# Cont"] = value
                    # Handle generic "date" and "time" fields - these should map to end date/time based on the document structure
                    elif key == "date" and sample_info["Composite or Collected End Date"] == "NIL":
                        sample_info["Composite or Collected End Date"] = value
                    elif key == "time" and sample_info["Composite or Collected End Time"] == "NIL":
                        sample_info["Composite or Collected End Time"] = value
                    # Handle numbered field patterns like "date_01", "time_01", etc.
                    elif key.startswith("date_") and sample_info["Composite or Collected End Date"] == "NIL":
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("time_") and sample_info["Composite or Collected End Time"] == "NIL":
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("number_containers_") or key.endswith("_number_containers") or key.startswith("number_containers-") or key.endswith("-number_containers") or key in ["# cont", "# cont.", "cont", "number_of_containers", "number of containers", "num_containers", "#_cont"]:
                        sample_info["# Cont"] = value
                    elif key.startswith("residual_chlorine_result_") or key.endswith("_residual_chlorine_result") or key in ["result", "residual chlorine result", "residual chloride result", "residual_chlorine_result", "residual_chloride_result"]:
                        sample_info["Residual Chloride Result"] = value
                    elif key.startswith("residual_chlorine_units_") or key.endswith("_residual_chlorine_units") or key in ["units", "residual chlorine units", "residual chloride units", "residual_chlorine_units", "residual_chloride_units"]:
                        sample_info["Residual Chloride Units"] = value
                    # Handle sample comment fields
                    elif key.startswith("sample_comment_") or key.endswith("_sample_comment") or key.startswith("comment_") or key.endswith("_comment") or key in ["sample_comment", "comment", "comments"]:
                        sample_info["Sample Comment"] = value
            
            # Additional comprehensive field mapping - handle cases where fields might not be properly grouped by sample ID
            # This is a more aggressive approach to find and map fields that might be extracted but not properly associated
            for field in sample_data_fields:
                if field.get('type') == 'sample_field':
                    key = str(field.get('key', '')).lower()
                    value = field.get('value', 'NIL')
                    
                    # Skip if we already have a value for this field
                    if sample_info["Matrix"] != "NIL" and (key.startswith("matrix_") or key.endswith("_matrix") or key == "matrix"):
                        continue
                    if sample_info["Comp/Grab"] != "NIL" and (key.startswith("comp_grab_") or key.endswith("_comp_grab") or key in ["comp/grab", "comp_grab", "composite_grab"]):
                        continue
                    if sample_info["Composite Start Date"] != "NIL" and (key.startswith("collected_date_start_") or key.endswith("_collected_date_start") or key in ["composite_start_date", "composite start date"]):
                        continue
                    if sample_info["Composite Start Time"] != "NIL" and (key.startswith("collected_time_start_") or key.endswith("_collected_time_start") or key == "time_collected_composite_start" or key in ["composite_start_time", "composite start time"]):
                        continue
                    if sample_info["Composite or Collected End Date"] != "NIL" and (key.startswith("collected_date_end_") or key.endswith("_collected_date_end") or key in ["composite_end_date", "composite end date", "collected_composite_end_date", "collected or composite end date", "date_collected_composite_end", "collected_or_composite_end_date"] or key.startswith("collected_composite_end_date_")):
                        continue
                    if sample_info["Composite or Collected End Time"] != "NIL" and (key.startswith("collected_time_end_") or key.endswith("_collected_time_end") or key == "time_collected_composite_end" or key in ["composite_end_time", "composite end time", "collected_composite_end_time", "collected or composite end time", "collected_or_composite_end_time"] or key.startswith("collected_composite_end_time_")):
                        continue
                    if sample_info["# Cont"] != "NIL" and (key.startswith("number_containers_") or key.endswith("_number_containers") or key.startswith("number_containers-") or key.endswith("-number_containers") or key in ["# cont", "# cont.", "cont", "number_of_containers", "number of containers", "num_containers", "#_cont"]):
                        continue
                    if sample_info["Residual Chloride Result"] != "NIL" and (key.startswith("residual_chlorine_result_") or key.endswith("_residual_chlorine_result") or key in ["result", "residual chlorine result", "residual chloride result", "residual_chlorine_result", "residual_chloride_result"]):
                        continue
                    if sample_info["Residual Chloride Units"] != "NIL" and (key.startswith("residual_chlorine_units_") or key.endswith("_residual_chlorine_units") or key in ["units", "residual chlorine units", "residual chloride units", "residual_chlorine_units", "residual_chloride_units"]):
                        continue
                    if sample_info["Sample Comment"] != "NIL" and (key.startswith("sample_comment_") or key.endswith("_sample_comment") or key.startswith("comment_") or key.endswith("_comment") or key in ["sample_comment", "comment", "comments"]):
                        continue
                    
                    # Apply the same mapping logic but for ungrouped fields
                    if (key.startswith("matrix_") or key.endswith("_matrix") or 
                        key.startswith("matrix_type_sample_") or key.endswith("_matrix_type_sample") or
                        key == "matrix"):
                        sample_info["Matrix"] = value
                    elif (key.startswith("comp_grab_") or key.endswith("_comp_grab") or 
                          key.startswith("grab_comp_") or key.endswith("_grab_comp") or
                          key in ["comp/grab", "comp_grab", "composite_grab", "grab_comp"]):
                        sample_info["Comp/Grab"] = value
                    elif (key.startswith("collected_date_start_") or key.endswith("_collected_date_start") or 
                          key.startswith("collected_date_mf_p_i") or key.endswith("_collected_date_mf_p_i") or
                          key.startswith("date_sh_50") or key.endswith("_date_sh_50") or
                          key.startswith("date_collected_sh_50") or key.endswith("_date_collected_sh_50") or
                          key.startswith("composite_start_date_") or key.endswith("_composite_start_date") or
                          key.startswith("collected_as_composite_start_date_") or key.endswith("_collected_as_composite_start_date") or
                          key.startswith("collected_or_composite_start_date_") or key.endswith("_collected_or_composite_start_date") or
                          key.startswith("collected_date_") or key.endswith("_collected_date") or
                          key in ["composite_start_date", "composite start date", "collected_date_mf_p_i", "date_sh_50", "date_collected_sh_50"]):
                        sample_info["Composite Start Date"] = value
                    elif (key.startswith("collected_time_start_") or key.endswith("_collected_time_start") or 
                          key.startswith("collected_time_mf_p_i") or key.endswith("_collected_time_mf_p_i") or
                          key.startswith("time_sh_50") or key.endswith("_time_sh_50") or
                          key.startswith("time_collected_sh_50") or key.endswith("_time_collected_sh_50") or
                          key.startswith("composite_start_time_") or key.endswith("_composite_start_time") or
                          key.startswith("collected_as_composite_start_time_") or key.endswith("_collected_as_composite_start_time") or
                          key.startswith("collected_or_composite_start_time_") or key.endswith("_collected_or_composite_start_time") or
                          key.startswith("collected_time_") or key.endswith("_collected_time") or
                          key == "time_collected_composite_start" or key in ["composite_start_time", "composite start time", "collected_time_mf_p_i", "time_sh_50", "time_collected_sh_50"]):
                        sample_info["Composite Start Time"] = value
                    elif (key.startswith("collected_date_end_") or key.endswith("_collected_date_end") or 
                          key.startswith("collected_as_composite_end_date_") or key.endswith("_collected_as_composite_end_date") or
                          key.startswith("collected_at_composite_end_date_") or key.endswith("_collected_at_composite_end_date") or
                          key.startswith("collected_or_composite_end_date_") or key.endswith("_collected_or_composite_end_date") or
                          key.startswith("composite_end_date_") or key.endswith("_composite_end_date") or
                          key in ["composite_end_date", "composite end date", "collected_composite_end_date", "collected or composite end date", "date_collected_composite_end", "collected_or_composite_end_date"] or 
                          key.startswith("collected_composite_end_date_")):
                        sample_info["Composite or Collected End Date"] = value
                    elif (key.startswith("collected_time_end_") or key.endswith("_collected_time_end") or 
                          key.startswith("collected_as_composite_end_time_") or key.endswith("_collected_as_composite_end_time") or
                          key.startswith("collected_at_composite_end_time_") or key.endswith("_collected_at_composite_end_time") or
                          key.startswith("collected_or_composite_end_time_") or key.endswith("_collected_or_composite_end_time") or
                          key.startswith("composite_end_time_") or key.endswith("_composite_end_time") or
                          key == "time_collected_composite_end" or key in ["composite_end_time", "composite end time", "collected_composite_end_time", "collected or composite end time", "collected_or_composite_end_time"] or 
                          key.startswith("collected_composite_end_time_")):
                        sample_info["Composite or Collected End Time"] = value
                    # Handle generic "date" and "time" fields - these should map to end date/time based on the document structure
                    elif key == "date" and sample_info["Composite or Collected End Date"] == "NIL":
                        sample_info["Composite or Collected End Date"] = value
                    elif key == "time" and sample_info["Composite or Collected End Time"] == "NIL":
                        sample_info["Composite or Collected End Time"] = value
                    # Handle numbered field patterns like "date_01", "time_01", etc.
                    elif key.startswith("date_") and sample_info["Composite or Collected End Date"] == "NIL":
                        sample_info["Composite or Collected End Date"] = value
                    elif key.startswith("time_") and sample_info["Composite or Collected End Time"] == "NIL":
                        sample_info["Composite or Collected End Time"] = value
                    elif key.startswith("number_containers_") or key.endswith("_number_containers") or key.startswith("number_containers-") or key.endswith("-number_containers") or key in ["# cont", "# cont.", "cont", "number_of_containers", "number of containers", "num_containers", "#_cont"]:
                        sample_info["# Cont"] = value
                    elif key.startswith("residual_chlorine_result_") or key.endswith("_residual_chlorine_result") or key in ["result", "residual chlorine result", "residual chloride result", "residual_chlorine_result", "residual_chloride_result"]:
                        sample_info["Residual Chloride Result"] = value
                    elif key.startswith("residual_chlorine_units_") or key.endswith("_residual_chlorine_units") or key in ["units", "residual chlorine units", "residual chloride units", "residual_chlorine_units", "residual_chloride_units"]:
                        sample_info["Residual Chloride Units"] = value
                    # Handle sample comment fields
                    elif key.startswith("sample_comment_") or key.endswith("_sample_comment") or key.startswith("comment_") or key.endswith("_comment") or key in ["sample_comment", "comment", "comments"]:
                        sample_info["Sample Comment"] = value
                    # Additional field patterns that might be used by AI
                    elif key in ["start_date", "start_time", "end_date", "end_time", "collection_date", "collection_time"]:
                        if key in ["start_date", "collection_date"] and sample_info["Composite Start Date"] == "NIL":
                            sample_info["Composite Start Date"] = value
                        elif key in ["start_time", "collection_time"] and sample_info["Composite Start Time"] == "NIL":
                            sample_info["Composite Start Time"] = value
                        elif key == "end_date" and sample_info["Composite or Collected End Date"] == "NIL":
                            sample_info["Composite or Collected End Time"] = value
                        elif key == "end_time" and sample_info["Composite or Collected End Time"] == "NIL":
                            sample_info["Composite or Collected End Time"] = value
                    # Handle container count variations
                    elif key in ["containers", "container_count", "num_containers", "container_number", "no_containers"]:
                        sample_info["# Cont"] = value
                    # Handle residual chlorine variations
                    elif key in ["residual_chlorine", "residual_chloride", "chlorine_result", "chloride_result", "chlorine_units", "chloride_units"]:
                        if "result" in key and sample_info["Residual Chloride Result"] == "NIL":
                            sample_info["Residual Chloride Result"] = value
                        elif "units" in key and sample_info["Residual Chloride Units"] == "NIL":
                            sample_info["Residual Chloride Units"] = value
            
            # Handle special case where Matrix field contains both Matrix and Comp/Grab information
            # e.g., "DW G" should be split into Matrix="DW" and Comp/Grab="G"
            if sample_info["Matrix"] != "NIL" and sample_info["Comp/Grab"] == "NIL":
                matrix_value = sample_info["Matrix"]
                if " " in matrix_value and len(matrix_value.split()) == 2:
                    parts = matrix_value.split()
                    sample_info["Matrix"] = parts[0]  # First part is Matrix
                    sample_info["Comp/Grab"] = parts[1]  # Second part is Comp/Grab
            
            # Handle special case where Matrix and Grab/Comp are combined (e.g., "B2" should be Matrix="B", Comp/Grab="2")
            if sample_info["Matrix"] != "NIL" and sample_info["Comp/Grab"] == "NIL":
                matrix_value = sample_info["Matrix"]
                # Check if it's a combination like "B2", "C3", etc.
                if len(matrix_value) == 2 and matrix_value[0].isalpha() and matrix_value[1].isdigit():
                    sample_info["Matrix"] = matrix_value[0]  # First character is Matrix
                    sample_info["Comp/Grab"] = matrix_value[1]  # Second character is Comp/Grab
            
            # Handle special case where result and units are combined (e.g., "0.5 mg" should be result="0.5", units="mg")
            if sample_info["Residual Chloride Result"] != "NIL" and sample_info["Residual Chloride Units"] == "NIL":
                result_value = sample_info["Residual Chloride Result"]
                # Check if it contains both number and unit (e.g., "0.5 mg", "1.2 ug/L")
                import re
                match = re.match(r'^([\d.]+)\s*([a-zA-Z/]+)$', result_value.strip())
                if match:
                    sample_info["Residual Chloride Result"] = match.group(1)  # Number part
                    sample_info["Residual Chloride Units"] = match.group(2)  # Unit part
            
            # Handle special case where matrix_grab_code field contains both Matrix and Comp/Grab (e.g., "B2" should be Matrix="B", Comp/Grab="2")
            # This handles the specific case mentioned in user examples
            if sample_info["Matrix"] != "NIL" and sample_info["Comp/Grab"] == "NIL":
                matrix_value = sample_info["Matrix"]
                # Check if it's a combination like "B2", "C3", etc. (letter followed by number)
                if len(matrix_value) == 2 and matrix_value[0].isalpha() and matrix_value[1].isdigit():
                    sample_info["Matrix"] = matrix_value[0]  # First character is Matrix
                    sample_info["Comp/Grab"] = matrix_value[1]  # Second character is Comp/Grab
            
            # If we still have NIL values, try to fill them from the general field mapping
            # This handles cases where fields are extracted but not explicitly associated with sample IDs
            if sample_info["Matrix"] == "NIL":
                # Look for matrix fields with sample-specific naming
                for field_key in field_type_mapping:
                    if (field_key.startswith("matrix_") or field_key.endswith("_matrix") or (field_key.startswith("dw_") and field_key.endswith("_matrix"))) and field_type_mapping[field_key]:
                        for matrix_value in field_type_mapping[field_key]:
                            if matrix_value != "NIL":
                                sample_info["Matrix"] = matrix_value
                                break
                        if sample_info["Matrix"] != "NIL":
                            break
            
            if sample_info["Comp/Grab"] == "NIL":
                # Look for comp_grab fields with sample-specific naming
                for field_key in field_type_mapping:
                    if (field_key.startswith("comp_grab_") or field_key.endswith("_comp_grab") or (field_key.startswith("dw_") and field_key.endswith("_comp_grab"))) and field_type_mapping[field_key]:
                        for comp_grab_value in field_type_mapping[field_key]:
                            if comp_grab_value != "NIL":
                                sample_info["Comp/Grab"] = comp_grab_value
                                break
                        if sample_info["Comp/Grab"] != "NIL":
                            break
            
            if sample_info["Composite Start Date"] == "NIL":
                # Look for collected_date_start fields and composite_start_date fields
                for field_key in field_type_mapping:
                    if ((field_key.startswith("collected_date_start_") or field_key.endswith("_collected_date_start")) or
                        (field_key.startswith("composite_start_date_") or field_key.endswith("_composite_start_date"))) and field_type_mapping[field_key]:
                        for date_value in field_type_mapping[field_key]:
                            if date_value != "NIL":
                                sample_info["Composite Start Date"] = date_value
                                break
                        if sample_info["Composite Start Date"] != "NIL":
                            break
            
            if sample_info["Composite Start Time"] == "NIL":
                # Look for collected_time_start fields, composite_start_time fields, or time_collected_composite_start
                for field_key in field_type_mapping:
                    if ((field_key.startswith("collected_time_start_") or field_key.endswith("_collected_time_start")) or
                        (field_key.startswith("composite_start_time_") or field_key.endswith("_composite_start_time")) or
                        field_key == "time_collected_composite_start") and field_type_mapping[field_key]:
                        for time_value in field_type_mapping[field_key]:
                            if time_value != "NIL":
                                sample_info["Composite Start Time"] = time_value
                                break
                        if sample_info["Composite Start Time"] != "NIL":
                            break
            
            if sample_info["Composite or Collected End Date"] == "NIL":
                # Look for collected_date_end fields, collected_as_composite_end_date fields, collected_at_composite_end_date fields, or generic "date" fields
                for field_key in field_type_mapping:
                    if (((field_key.startswith("collected_date_end_") or field_key.endswith("_collected_date_end")) or
                         (field_key.startswith("collected_as_composite_end_date_") or field_key.endswith("_collected_as_composite_end_date")) or
                         (field_key.startswith("collected_at_composite_end_date_") or field_key.endswith("_collected_at_composite_end_date")) or
                         (field_key.startswith("composite_end_date_") or field_key.endswith("_composite_end_date")) or
                         field_key in ["date", "date_collected_composite_end", "collected_or_composite_end_date"] or 
                         field_key.startswith("date_") or field_key.startswith("collected_composite_end_date_") or 
                         (field_key.startswith("dw_") and field_key.endswith("_collected_or_composite_end_date"))) and field_type_mapping[field_key]):
                        for date_value in field_type_mapping[field_key]:
                            if date_value != "NIL":
                                sample_info["Composite or Collected End Date"] = date_value
                                break
                        if sample_info["Composite or Collected End Date"] != "NIL":
                            break
            
            if sample_info["Composite or Collected End Time"] == "NIL":
                # Look for collected_time_end fields, collected_as_composite_end_time fields, collected_at_composite_end_time fields, or time_collected_composite_end or generic "time" fields
                for field_key in field_type_mapping:
                    if (((field_key.startswith("collected_time_end_") or field_key.endswith("_collected_time_end")) or
                         (field_key.startswith("collected_as_composite_end_time_") or field_key.endswith("_collected_as_composite_end_time")) or
                         (field_key.startswith("collected_at_composite_end_time_") or field_key.endswith("_collected_at_composite_end_time")) or
                         (field_key.startswith("composite_end_time_") or field_key.endswith("_composite_end_time")) or
                         field_key == "time_collected_composite_end" or field_key in ["time", "collected_or_composite_end_time"] or 
                         field_key.startswith("time_") or field_key.startswith("collected_composite_end_time_") or 
                         (field_key.startswith("dw_") and field_key.endswith("_collected_or_composite_end_time"))) and field_type_mapping[field_key]):
                        for time_value in field_type_mapping[field_key]:
                            if time_value != "NIL":
                                sample_info["Composite or Collected End Time"] = time_value
                                break
                        if sample_info["Composite or Collected End Time"] != "NIL":
                            break
            
            if sample_info["# Cont"] == "NIL":
                # Look for container count fields with more comprehensive patterns
                for field_key in field_type_mapping:
                    if ((field_key.startswith("number_containers_") or field_key.endswith("_number_containers") or 
                         field_key.startswith("number_of_containers_") or field_key.endswith("_number_of_containers") or
                         field_key.startswith("num_containers_") or field_key.endswith("_num_containers") or
                         field_key.startswith("num_cont_") or field_key.endswith("_num_cont") or
                         field_key.startswith("container_count_") or field_key.endswith("_container_count") or
                         field_key in ["num_containers", "#_cont", "container_count", "number_of_containers", "num_cont", "# cont", "cont"] or 
                         (field_key.startswith("dw_") and field_key.endswith("_number_of_containers"))) and 
                        field_type_mapping[field_key]):
                        for cont_value in field_type_mapping[field_key]:
                            if cont_value != "NIL":
                                sample_info["# Cont"] = cont_value
                                break
                        if sample_info["# Cont"] != "NIL":
                            break
            
            if sample_info["Residual Chloride Result"] == "NIL":
                # Look for result fields with more comprehensive patterns
                for field_key in field_type_mapping:
                    if ((field_key.startswith("residual_chlorine_result_") or field_key.endswith("_residual_chlorine_result") or
                         field_key.startswith("residual_chloride_result_") or field_key.endswith("_residual_chloride_result") or
                         field_key.startswith("result_") or field_key.endswith("_result") or
                         field_key in ["result", "residual_chlorine_result", "residual_chloride_result", "residual chloride result"]) and 
                        field_type_mapping[field_key]):
                        for result_value in field_type_mapping[field_key]:
                            if result_value != "NIL":
                                sample_info["Residual Chloride Result"] = result_value
                                break
                        if sample_info["Residual Chloride Result"] != "NIL":
                            break
            
            if sample_info["Residual Chloride Units"] == "NIL":
                # Look for units fields with more comprehensive patterns
                for field_key in field_type_mapping:
                    if ((field_key.startswith("residual_chlorine_units_") or field_key.endswith("_residual_chlorine_units") or
                         field_key.startswith("residual_chloride_units_") or field_key.endswith("_residual_chloride_units") or
                         field_key.startswith("units_") or field_key.endswith("_units") or
                         field_key in ["units", "residual_chlorine_units", "residual_chloride_units", "residual chloride units"]) and 
                        field_type_mapping[field_key]):
                        for units_value in field_type_mapping[field_key]:
                            if units_value != "NIL":
                                sample_info["Residual Chloride Units"] = units_value
                                break
                        if sample_info["Residual Chloride Units"] != "NIL":
                            break
            
            # Create separate entries for each checked analysis request
            # First, find all analysis checkboxes for this sample
            checked_analyses = []
            
            for field in sample_data_fields:
                if (field.get('type') == 'analysis_checkbox' and 
                    field.get('sample_id') == sample_id and 
                    field.get('value') == 'checked'):
                    # Extract analysis name from the field
                    analysis_name = field.get('analysis_name', '')
                    if analysis_name:
                        checked_analyses.append(analysis_name)
            
            # Create separate entries for each checked analysis
            if checked_analyses:
                for analysis_name in checked_analyses:
                    # Create a copy of the sample info for each checked analysis
                    sample_entry = sample_info.copy()
                    sample_entry["analysis_request"] = analysis_name
                    restructured_data.append(sample_entry)
            else:
                # If no analyses are checked, add the sample with NIL analysis_request
                sample_info["analysis_request"] = "NIL"
                restructured_data.append(sample_info)
        
        return restructured_data
    
    def detect_rc_work_order_format(self, extracted_fields):
        """Detect if the document is in R & C Work Order format"""
        rc_indicators = [
            'r_and_c_work_order', 'yr_date', 'time', 'sample_description',
            'total_number_of_containers', 'filtered_yes_no', 'cooled_yes_no', 
            'container_type_plastic_glass', 'container_volume_ml', 
            'sample_type_grab_composite', 'sample_source_ww_gw_dw_sw_s_other'
        ]
        
        field_keys = [str(field.get('key', '')).lower().replace(' ', '_').replace('-', '_') for field in extracted_fields]
        
        # Check if we have R & C Work Order indicators
        rc_count = sum(1 for indicator in rc_indicators if any(indicator in key for key in field_keys))
        
        self.logger.info(f"R & C Work Order detection: found {rc_count} indicators out of {len(rc_indicators)}")
        self.logger.info(f"Field keys sample: {field_keys[:10]}")
        
        return rc_count >= 3  # If we find 3 or more indicators, it's likely R & C format
    
    def restructure_rc_work_order_data(self, sample_data_fields, sample_ids, analysis_request, sample_analysis_map):
        """Restructure data for R & C Work Order format with flat structure"""
        restructured_data = []
        
        # Group fields by sample ID
        sample_groups = {}
        
        # Initialize sample groups
        for sample_id in sample_ids:
            sample_groups[sample_id] = {
                "R & C Work Order": "NIL",
                "YR__ DATE": "NIL", 
                "TIME": "NIL",
                "SAMPLE DESCRIPTION": sample_id,
                "Total Number of Containers": "NIL",
                "Filtered (Y/N)": "NIL",
                "Cooled (Y/N)": "NIL",
                "Container Type (Plastic (P) / Glass (G))": "NIL",
                "Container Volume in mL": "NIL",
                "Sample Type (Grab (G) / Composite (C))": "NIL",
                "Sample Source (WW, GW, DW, SW, S, Others)": "NIL",
                "analysis_requests": []
            }
        
        # Process all fields to extract R & C Work Order data
        for field in sample_data_fields:
            field_type = field.get('type', '')
            key = str(field.get('key', '')).lower().replace(' ', '_').replace('-', '_')
            value = field.get('value', 'NIL')
            sample_id = field.get('sample_id')
            
            # Handle sample fields
            if field_type == 'sample_field' and sample_id in sample_groups:
                if 'r_and_c_work_order' in key:
                    sample_groups[sample_id]["R & C Work Order"] = value
                elif 'yr_date' in key:
                    sample_groups[sample_id]["YR__ DATE"] = value
                elif 'time' in key and 'date' not in key:
                    sample_groups[sample_id]["TIME"] = value
                elif 'sample_description' in key:
                    sample_groups[sample_id]["SAMPLE DESCRIPTION"] = value
                elif 'filtered_yes_no' in key:
                    sample_groups[sample_id]["Filtered (Y/N)"] = value
                elif 'cooled_yes_no' in key:
                    sample_groups[sample_id]["Cooled (Y/N)"] = value
                elif 'container_type_plastic_glass' in key:
                    sample_groups[sample_id]["Container Type (Plastic (P) / Glass (G))"] = value
                elif 'container_volume_ml' in key:
                    sample_groups[sample_id]["Container Volume in mL"] = value
                elif 'sample_type_grab_composite' in key:
                    sample_groups[sample_id]["Sample Type (Grab (G) / Composite (C))"] = value
                elif 'sample_source_ww_gw_dw_sw_s_other' in key:
                    sample_groups[sample_id]["Sample Source (WW, GW, DW, SW, S, Others)"] = value
            
            # Handle general fields that apply to all samples
            elif field_type == 'field':
                if 'total_number_of_containers' in key:
                    for sid in sample_groups:
                        sample_groups[sid]["Total Number of Containers"] = value
        
        # Collect analysis requests for each sample
        for field in sample_data_fields:
            if field.get('type') == 'analysis_checkbox':
                sample_id = field.get('sample_id')
                analysis_name = field.get('analysis_name')
                checkbox_value = field.get('value', 'unchecked')
                
                # Handle R&C format where analysis_name might be in the key
                if not analysis_name:
                    key = str(field.get('key', '')).lower()
                    if key.startswith('parameter_'):
                        analysis_name = key.replace('parameter_', '')
                
                # For R&C format, associate all checked analysis requests with all samples
                if checkbox_value == 'checked' and analysis_name:
                    for sample_id in sample_groups:
                        if analysis_name not in sample_groups[sample_id]["analysis_requests"]:
                            sample_groups[sample_id]["analysis_requests"].append(analysis_name)
        
        # Create flat structure - one entry per analysis request
        for sample_id, sample_data in sample_groups.items():
            if sample_data["analysis_requests"]:
                for analysis_name in sample_data["analysis_requests"]:
                    flat_entry = {
                        "R & C Work Order": sample_data["R & C Work Order"],
                        "YR__ DATE": sample_data["YR__ DATE"],
                        "TIME": sample_data["TIME"],
                        "SAMPLE DESCRIPTION": sample_data["SAMPLE DESCRIPTION"],
                        "Total Number of Containers": sample_data["Total Number of Containers"],
                        "Analysis Request": analysis_name,
                        "Filtered (Y/N)": sample_data["Filtered (Y/N)"],
                        "Cooled (Y/N)": sample_data["Cooled (Y/N)"],
                        "Container Type (Plastic (P) / Glass (G))": sample_data["Container Type (Plastic (P) / Glass (G))"],
                        "Container Volume in mL": sample_data["Container Volume in mL"],
                        "Sample Type (Grab (G) / Composite (C))": sample_data["Sample Type (Grab (G) / Composite (C))"],
                        "Sample Source (WW, GW, DW, SW, S, Others)": sample_data["Sample Source (WW, GW, DW, SW, S, Others)"]
                    }
                    restructured_data.append(flat_entry)
            else:
                # If no analysis requests, add a single entry with NIL analysis
                flat_entry = {
                    "R & C Work Order": sample_data["R & C Work Order"],
                    "YR__ DATE": sample_data["YR__ DATE"],
                    "TIME": sample_data["TIME"],
                    "SAMPLE DESCRIPTION": sample_data["SAMPLE DESCRIPTION"],
                    "Total Number of Containers": sample_data["Total Number of Containers"],
                    "Analysis Request": "NIL",
                    "Filtered (Y/N)": sample_data["Filtered (Y/N)"],
                    "Cooled (Y/N)": sample_data["Cooled (Y/N)"],
                    "Container Type (Plastic (P) / Glass (G))": sample_data["Container Type (Plastic (P) / Glass (G))"],
                    "Container Volume in mL": sample_data["Container Volume in mL"],
                    "Sample Type (Grab (G) / Composite (C))": sample_data["Sample Type (Grab (G) / Composite (C))"],
                    "Sample Source (WW, GW, DW, SW, S, Others)": sample_data["Sample Source (WW, GW, DW, SW, S, Others)"]
                }
                restructured_data.append(flat_entry)
        
        self.logger.info(f"R & C Work Order restructuring: created {len(restructured_data)} flat entries")
        
        return restructured_data
    
    def extract_comprehensive(self, pdf_path):
        """Main extraction method that combines text and vision analysis with fallbacks"""
        try:
            self.logger.info(f"Starting comprehensive extraction for: {pdf_path}")
            self.logger.info(f"Extraction start time: {datetime.now()}")
            
            # Get file information
            file_size_bytes = os.path.getsize(pdf_path)
            file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
            self.logger.info(f"File size: {file_size_bytes} bytes ({file_size_mb} MB)")
            
            # Extract text as fallback
            self.logger.info(f"Extracting text from PDF as fallback")
            text_content = self.extract_text_from_pdf(pdf_path)
            self.logger.info(f"Extracted {len(text_content)} characters of text")
            
            # Extract images for AI vision analysis
            self.logger.info(f"Extracting images from PDF")
            images = self.extract_images_from_pdf(pdf_path)
            self.logger.info(f"Extracted {len(images)} images")
            
            # Perform AI vision analysis
            self.logger.info(f"Starting AI vision analysis")
            ai_results = self.analyze_with_ai_vision(images, pdf_path)
            
            # If AI vision results are poor, try text analysis as fallback
            vision_field_count = len(ai_results.get('extracted_fields', []))
            if vision_field_count < 10:  # Threshold for poor extraction
                self.logger.warning(f"AI vision extracted only {vision_field_count} fields, trying text analysis fallback")
                text_results = self.analyze_text_with_ai(text_content, pdf_path)
                
                # Merge results, preferring vision results but filling gaps with text results
                if text_results.get('extracted_fields'):
                    self.logger.info(f"Text analysis extracted {len(text_results['extracted_fields'])} additional fields")
                    
                    # Add text-extracted fields that don't conflict with vision results
                    vision_keys = {field.get('key', '').lower() for field in ai_results.get('extracted_fields', [])}
                    for text_field in text_results.get('extracted_fields', []):
                        text_key = text_field.get('key', '').lower()
                        if text_key not in vision_keys:
                            ai_results['extracted_fields'].append(text_field)
                    
                    # Update sample IDs and analysis requests
                    ai_results['sample_ids'].extend(text_results.get('sample_ids', []))
                    ai_results['analysis_request'].extend(text_results.get('analysis_request', []))
                    
                    # Remove duplicates
                    ai_results['sample_ids'] = list(set(ai_results['sample_ids']))
                    ai_results['analysis_request'] = list(set(ai_results['analysis_request']))
            
            # Validate and enhance extracted fields (without adding confidence/validation_notes to output)
            self.logger.info(f"Validating and enhancing {len(ai_results.get('extracted_fields', []))} extracted fields")
            validated_fields = []
            for field in ai_results.get('extracted_fields', []):
                # Validate the field value
                validated_value, confidence, notes = self.validate_field_value(
                    field.get('key', ''), 
                    field.get('value', ''), 
                    field.get('type', '')
                )
                
                # Update field value but don't add confidence/validation_notes to output
                field['value'] = validated_value
                
                # Only include fields with reasonable confidence or non-NIL values
                if confidence >= 0.3 or validated_value != "NIL":
                    validated_fields.append(field)
                else:
                    self.logger.debug(f"Excluding low-confidence field: {field.get('key', '')} = {validated_value}")
            
            ai_results['extracted_fields'] = validated_fields
            self.logger.info(f"After validation: {len(validated_fields)} fields retained")
            
            # Calculate totals
            total_fields = len(ai_results['extracted_fields'])
            total_checkboxes = len(ai_results['all_checkboxes']['all_checkboxes_summary'])
            
            # Organize data into General Information and Sample Data Information
            general_information = []
            sample_data_information = []
            
            # Keywords to identify sample-related fields (more precise list)
            sample_keywords = [
                'sample_id', 'matrix_', 'comp_grab_', 'composite_start_', 'composite_end_',
                'collected_composite_', 'collected_at_', 'number_of_containers_', 'num_containers_', 'result_', 'units_',
                'sample_comment_', 'analysis_', 'laj_', 'yot_', 'customer_sample_', 'residual_chloride_',
                'container_count_', 'num_cont_', 'collected_date_', 'collected_time_'
            ]
            
            # Keywords to identify general information fields
            general_keywords = [
                'company', 'project', 'contact', 'phone', 'email', 'address', 'purchase',
                'order', 'quote', 'date', 'time', 'location', 'city', 'state', 'county',
                'origin', 'regulatory', 'program', 'permit', 'ow_pwsid', 'ww_permit',
                'lab_use', 'proj_mgr', 'account', 'profile', 'template', 'bottle', 'qc',
                'field_id', 'temp', 'corrected', 'comm', 'instructions',
                'hazards', 'relinquished', 'received', 'signature', 'printed', 'name',
                'tracking', 'delivered', 'hand', 'person', 'fedex', 'ups', 'labline',
                'page', 'env_frm', 'corq', 'header', 'title', 'scan', 'qr', 'code'
            ]
            
            # Separate fields into general and sample categories
            for field in ai_results['extracted_fields']:
                # Ensure field_key is a string to prevent .lower() errors
                field_key_raw = field.get('key', '')
                field_key = str(field_key_raw).lower() if field_key_raw else ''
                field_type = field.get('type', '')
                
                # Check if field is sample-related (more precise check)
                is_sample_related = (
                    field_type in ['sample_field', 'analysis_checkbox'] or
                    field.get('sample_id') is not None or
                    field.get('analysis_name') is not None or
                    # Check for specific sample field patterns (must start with or contain the keyword)
                    any(field_key.startswith(keyword) or keyword in field_key for keyword in sample_keywords)
                )
                
                # Check if field is general information (not sample-related)
                is_general_related = (
                    field_type in ['field', 'header'] and
                    (any(keyword in field_key for keyword in general_keywords) or
                     not is_sample_related)
                )
                
                if is_sample_related:
                    sample_data_information.append(field)
                elif is_general_related:
                    general_information.append(field)
                else:
                    # Default to general information for any unclassified fields
                    general_information.append(field)
            
            # Detect document format and restructure sample data accordingly
            is_rc_format = self.detect_rc_work_order_format(ai_results['extracted_fields'])
            
            if is_rc_format:
                self.logger.info("Detected R & C Work Order format")
                restructured_sample_data = self.restructure_rc_work_order_data(
                    sample_data_information,
                    ai_results['sample_ids'],
                    ai_results['analysis_request'],
                    ai_results['sample_analysis_mapping']['sample_analysis_map']
                )
            else:
                self.logger.info("Using standard format")
                restructured_sample_data = self.restructure_sample_data(
                    sample_data_information,
                    ai_results['sample_ids'],
                    ai_results['analysis_request'],
                    ai_results['sample_analysis_mapping']['sample_analysis_map']
                )
            
            self.logger.info(f"Data Organization:")
            self.logger.info(f"General Information: {len(general_information)} fields")
            self.logger.info(f"Sample Data Information: {len(restructured_sample_data)} samples")
            
            # Prepare final response with only 3 main sections
            response = {
                "extracted_fields": ai_results['extracted_fields'],
                "general_information": general_information,
                "sample_data_information": restructured_sample_data
            }
            
            self.logger.info(f"Comprehensive extraction completed successfully")
            self.logger.info(f"Extraction end time: {datetime.now()}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive extraction: {e}")
            print(f"Error in comprehensive extraction: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pdf_path": pdf_path
            }

def main():
    """PDF extraction with command line support"""
    import sys
    
    print("🔍 Restructured PDF Extraction System")
    print("=" * 50)
    print("This system extracts all fields, values, and checkboxes from PDF documents")
    print("using Google Gemini 2.5 Flash AI vision analysis.")
    print()
    
    # Initialize extractor
    extractor = RestructuredPDFExtractor()
    
    # Check if PDF path is provided as command line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"❌ File not found: {pdf_path}")
            return
        
        print(f"\n🚀 Starting extraction for: {pdf_path}")
        print("⏳ This may take a few moments...")
        
        try:
            result = extractor.extract_comprehensive(pdf_path)
            
            if result.get("status") != "error":
                print("\n✅ Extraction completed successfully!")
                print(f"📊 Total fields extracted: {len(result.get('extracted_fields', []))}")
                print(f"📋 General Information: {len(result.get('general_information', []))}")
                print(f"🔬 Sample Data Information: {len(result.get('sample_data_information', []))}")
                
                # Save results to file
                output_file = f"{os.path.basename(pdf_path).replace('.pdf', '')}_restructured_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"💾 Results saved to: {output_file}")
                
            else:
                print(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            import traceback
            traceback.print_exc()
        
        return
    
    # Interactive mode if no command line argument
    while True:
        print("\nOptions:")
        print("1. Extract from a PDF file")
        print("2. Use sample PDF (OCR 35.pdf)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            pdf_path = input("Enter the full path to the PDF file: ").strip()
            if not os.path.exists(pdf_path):
                print(f"❌ File not found: {pdf_path}")
                continue
        elif choice == "2":
            pdf_path = "Sample Documents/OCR 35.pdf"
            if not os.path.exists(pdf_path):
                print(f"❌ Sample file not found: {pdf_path}")
                continue
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
            continue
        
        print(f"\n🚀 Starting extraction for: {pdf_path}")
        print("⏳ This may take a few moments...")
        
        try:
            result = extractor.extract_comprehensive(pdf_path)
            
            if result.get("status") != "error":
                print("\n✅ Extraction completed successfully!")
                print(f"📊 Total fields extracted: {len(result.get('extracted_fields', []))}")
                print(f"📋 General Information: {len(result.get('general_information', []))}")
                print(f"🔬 Sample Data Information: {len(result.get('sample_data_information', []))}")
                
                # Save results to file
                output_file = f"{os.path.basename(pdf_path).replace('.pdf', '')}_restructured_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"💾 Results saved to: {output_file}")
                
            else:
                print(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
