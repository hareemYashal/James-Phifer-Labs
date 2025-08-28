import os
import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
import io
import base64
import json
import re
from typing import Dict, List, Tuple, Optional
import logging
from config import GEMINI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedPDFExtractor:
    def __init__(self, api_key: str = None):
        """Initialize the Advanced PDF Extractor with Gemini API."""
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key or self.api_key == 'your_gemini_api_key_here':
            raise ValueError("Please set your Gemini API key in config.py or pass it as parameter")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Common form field patterns
        self.field_patterns = [
            r'([A-Z][a-z\s]+):\s*([^\n\r]*)',  # Title: Value
            r'([A-Z][A-Z\s]+):\s*([^\n\r]*)',  # TITLE: Value
            r'([A-Z][a-z\s]+)\s*=\s*([^\n\r]*)',  # Title = Value
            r'([A-Z][a-z\s]+)\s*:\s*([^\n\r]*)',  # Title : Value
        ]
    
    def extract_form_fields(self, pdf_path: str) -> Dict:
        """
        Extract form fields using multiple methods for better accuracy.
        """
        try:
            logger.info(f"Extracting form fields from: {pdf_path}")
            
            doc = fitz.open(pdf_path)
            
            # Method 1: Extract form fields directly
            form_fields = self._extract_pdf_form_fields(doc)
            
            # Method 2: Extract text and analyze
            text_fields = self._extract_text_fields(doc)
            
            # Method 3: Extract images and use vision
            image_fields = self._extract_image_fields(doc)
            
            # Combine all methods
            combined_fields = self._combine_extraction_methods(
                form_fields, text_fields, image_fields
            )
            
            doc.close()
            
            return {
                "pdf_path": pdf_path,
                "extraction_methods": {
                    "form_fields": len(form_fields),
                    "text_fields": len(text_fields),
                    "image_fields": len(image_fields)
                },
                "combined_fields": combined_fields,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error extracting fields from {pdf_path}: {str(e)}")
            return {
                "pdf_path": pdf_path,
                "status": "error",
                "error": str(e)
            }
    
    def _extract_pdf_form_fields(self, doc) -> List[Dict]:
        """Extract native PDF form fields."""
        fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get form fields on this page
            widget_list = page.widgets()
            
            for widget in widget_list:
                field_info = {
                    "key": widget.field_name or f"field_{len(fields)}",
                    "value": widget.field_value or "",
                    "type": widget.field_type,
                    "page": page_num + 1,
                    "method": "native_form"
                }
                fields.append(field_info)
        
        return fields
    
    def _extract_text_fields(self, doc) -> List[Dict]:
        """Extract fields from text content using pattern matching and AI."""
        fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_content = page.get_text()
            
            # Pattern-based extraction
            pattern_fields = self._extract_with_patterns(text_content, page_num)
            fields.extend(pattern_fields)
            
            # AI-based extraction for complex text
            if len(text_content) > 100:
                ai_fields = self._extract_with_ai_text(text_content, page_num)
                fields.extend(ai_fields)
        
        return fields
    
    def _extract_with_patterns(self, text: str, page_num: int) -> List[Dict]:
        """Extract fields using regex patterns."""
        fields = []
        
        for pattern in self.field_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                key, value = match
                key = key.strip()
                value = value.strip()
                
                if key and len(key) > 2:  # Filter out very short keys
                    fields.append({
                        "key": key,
                        "value": value,
                        "type": "text",
                        "page": page_num + 1,
                        "method": "pattern_matching"
                    })
        
        return fields
    
    def _extract_with_ai_text(self, text: str, page_num: int) -> List[Dict]:
        """Extract fields using Gemini AI text analysis."""
        try:
            prompt = f"""
            Analyze this document text and extract all form fields, keys, and values.
            Focus on identifying:
            1. Field names/labels (e.g., "Name:", "Date:", "Address:")
            2. Values associated with those fields
            3. Empty fields that need to be filled
            4. Field types (text, date, number, etc.)
            
            Return ONLY a valid JSON array like this:
            [
                {{
                    "key": "field_name",
                    "value": "field_value",
                    "type": "field_type"
                }}
            ]
            
            Document text:
            {text[:6000]}
            """
            
            response = self.model.generate_content(prompt)
            
            try:
                result = json.loads(response.text)
                if isinstance(result, list):
                    for field in result:
                        field["page"] = page_num + 1
                        field["method"] = "ai_text"
                    return result
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI response as JSON on page {page_num + 1}")
        
        except Exception as e:
            logger.error(f"AI text extraction error on page {page_num + 1}: {str(e)}")
        
        return []
    
    def _extract_image_fields(self, doc) -> List[Dict]:
        """Extract fields from images using Gemini Vision."""
        fields = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Convert page to image
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Use AI vision to extract fields
            vision_fields = self._extract_with_ai_vision(img, page_num)
            fields.extend(vision_fields)
        
        return fields
    
    def _extract_with_ai_vision(self, img: Image.Image, page_num: int) -> List[Dict]:
        """Extract fields using Gemini Vision API."""
        try:
            # Convert image to base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            prompt = f"""
            Analyze this document image and extract all form fields, keys, and values.
            
            Look for:
            1. Form field labels (e.g., "Name:", "Date:", "Address:")
            2. Values filled in those fields
            3. Empty fields that need to be filled
            4. Field types (text, checkbox, date, etc.)
            
            Return ONLY a valid JSON array like this:
            [
                {{
                    "key": "field_name",
                    "value": "field_value",
                    "type": "field_type"
                }}
            ]
            
            This is page {page_num + 1} of the document.
            """
            
            response = self.model.generate_content([
                prompt, 
                {"mime_type": "image/png", "data": img_base64}
            ])
            
            try:
                result = json.loads(response.text)
                if isinstance(result, list):
                    for field in result:
                        field["page"] = page_num + 1
                        field["method"] = "ai_vision"
                    return result
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI vision response as JSON on page {page_num + 1}")
        
        except Exception as e:
            logger.error(f"AI vision extraction error on page {page_num + 1}: {str(e)}")
        
        return []
    
    def _combine_extraction_methods(self, form_fields: List, text_fields: List, image_fields: List) -> List[Dict]:
        """Combine and deduplicate fields from different extraction methods."""
        all_fields = []
        seen_keys = set()
        
        # Priority: native form fields > AI vision > AI text > pattern matching
        priority_order = [form_fields, image_fields, text_fields]
        
        for method_fields in priority_order:
            for field in method_fields:
                key = field.get("key", "").lower().strip()
                
                # Skip if we've already seen this key
                if key in seen_keys:
                    continue
                
                seen_keys.add(key)
                all_fields.append(field)
        
        # Sort by page number and then by key
        all_fields.sort(key=lambda x: (x.get("page", 0), x.get("key", "")))
        
        return all_fields
    
    def compare_documents_advanced(self, template_pdf: str, filled_pdf: str) -> Dict:
        """Advanced document comparison with field mapping."""
        logger.info("Performing advanced document comparison...")
        
        # Extract fields from both documents
        template_result = self.extract_form_fields(template_pdf)
        filled_result = self.extract_form_fields(filled_pdf)
        
        if template_result["status"] == "error" or filled_result["status"] == "error":
            return {
                "status": "error",
                "template_error": template_result.get("error"),
                "filled_error": filled_result.get("error")
            }
        
        template_fields = template_result.get("combined_fields", [])
        filled_fields = filled_result.get("combined_fields", [])
        
        # Create intelligent field mapping
        field_mapping = self._create_field_mapping(template_fields, filled_fields)
        
        return {
            "template_pdf": template_pdf,
            "filled_pdf": filled_pdf,
            "template_fields_count": len(template_fields),
            "filled_fields_count": len(filled_fields),
            "mapped_fields_count": len(field_mapping),
            "field_mapping": field_mapping,
            "status": "success"
        }
    
    def _create_field_mapping(self, template_fields: List, filled_fields: List) -> List[Dict]:
        """Create intelligent field mapping between template and filled documents."""
        mapping = []
        
        for template_field in template_fields:
            template_key = template_field.get("key", "").lower().strip()
            
            # Find best matching field in filled PDF
            best_match = None
            best_score = 0
            
            for filled_field in filled_fields:
                filled_key = filled_field.get("key", "").lower().strip()
                
                # Calculate similarity score
                score = self._calculate_similarity(template_key, filled_key)
                
                if score > best_score and score > 0.7:  # Threshold for matching
                    best_score = score
                    best_match = filled_field
            
            mapping.append({
                "template_field": template_field,
                "filled_field": best_match,
                "similarity_score": best_score,
                "is_matched": best_match is not None,
                "key": template_field.get("key", ""),
                "template_value": template_field.get("value", ""),
                "filled_value": best_match.get("value", "") if best_match else "Not found",
                "field_type": template_field.get("type", "unknown"),
                "extraction_method": template_field.get("method", "unknown")
            })
        
        return mapping
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        if not str1 or not str2:
            return 0.0
        
        # Simple similarity based on common words
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0 