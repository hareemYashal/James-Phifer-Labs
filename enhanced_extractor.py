#!/usr/bin/env python3
"""
Enhanced PDF Extractor with Better Field Mapping
Handles both text and image-based PDFs for comprehensive analysis.
"""

import os
import json
import base64
import io
from typing import Dict, List, Optional
import logging
from config import GEMINI_API_KEY

# Try to import required packages
try:
    import PyPDF2
    PDF2_AVAILABLE = True
except ImportError:
    PDF2_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import fitz  # PyMuPDF for better PDF handling
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedPDFExtractor:
    def __init__(self, api_key: str = None):
        """Initialize the Enhanced PDF Extractor."""
        self.api_key = api_key or GEMINI_API_KEY
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE and self.api_key and self.api_key != 'your_gemini_api_key_here':
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.gemini_ready = True
                logger.info("✅ Gemini API initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️  Gemini API initialization failed: {e}")
                self.gemini_ready = False
        else:
            self.gemini_ready = False
            if not self.api_key or self.api_key == 'your_gemini_api_key_here':
                logger.warning("⚠️  No Gemini API key provided - AI analysis disabled")
    
    def extract_form_fields(self, pdf_path: str) -> Dict:
        """
        Extract form fields with enhanced capabilities.
        """
        try:
            logger.info(f"Extracting form fields from: {pdf_path}")
            
            if not os.path.exists(pdf_path):
                return {
                    "pdf_path": pdf_path,
                    "status": "error",
                    "error": "File not found"
                }
            
            # Basic file info
            file_size = os.path.getsize(pdf_path)
            file_info = {
                "pdf_path": pdf_path,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "extraction_methods": [],
                "extracted_fields": []
            }
            
            # Method 1: Try PyMuPDF (best for complex PDFs)
            if FITZ_AVAILABLE:
                fields = self._extract_with_fitz(pdf_path)
                if fields:
                    file_info["extracted_fields"] = fields
                    file_info["extraction_methods"].append("PyMuPDF")
                    file_info["pdf_type"] = "enhanced"
            
            # Method 2: Try PyPDF2
            elif PDF2_AVAILABLE and not file_info["extracted_fields"]:
                fields = self._extract_with_pypdf2(pdf_path)
                if fields:
                    file_info["extracted_fields"] = fields
                    file_info["extraction_methods"].append("PyPDF2")
                    file_info["pdf_type"] = "text"
            
            # Method 3: AI Analysis if available
            if self.gemini_ready and not file_info["extracted_fields"]:
                fields = self._extract_with_ai_vision(pdf_path)
                if fields:
                    file_info["extracted_fields"] = fields
                    file_info["extraction_methods"].append("Gemini Vision")
                    file_info["pdf_type"] = "image"
            
            # Method 4: Basic file analysis
            if not file_info["extracted_fields"]:
                file_info["extraction_methods"].append("File Analysis")
                file_info["pdf_type"] = "unknown"
                file_info["message"] = "No fields could be extracted"
            
            file_info["status"] = "success"
            return file_info
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return {
                "pdf_path": pdf_path,
                "status": "error",
                "error": str(e)
            }
    
    def _extract_with_fitz(self, pdf_path: str) -> List[Dict]:
        """Extract using PyMuPDF (best method)."""
        try:
            doc = fitz.open(pdf_path)
            fields = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get form fields
                widget_list = page.widgets()
                for widget in widget_list:
                    field_info = {
                        "key": widget.field_name or f"field_{len(fields)}",
                        "value": widget.field_value or "",
                        "type": widget.field_type,
                        "page": page_num + 1,
                        "method": "PyMuPDF"
                    }
                    fields.append(field_info)
                
                # Get text content for field detection
                text_content = page.get_text()
                if text_content:
                    # Look for common form field patterns
                    text_fields = self._extract_fields_from_text(text_content, page_num + 1)
                    fields.extend(text_fields)
            
            doc.close()
            return fields
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction error: {e}")
            return []
    
    def _extract_with_pypdf2(self, pdf_path: str) -> List[Dict]:
        """Extract using PyPDF2."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                fields = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_fields = self._extract_fields_from_text(page_text, page_num + 1)
                            fields.extend(text_fields)
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {e}")
                        continue
                
                return fields
                
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {e}")
            return []
    
    def _extract_fields_from_text(self, text: str, page_num: int) -> List[Dict]:
        """Extract form fields from text content."""
        fields = []
        
        # Common form field patterns
        patterns = [
            r'([A-Z][a-zA-Z\s]+):\s*([^\n\r]*)',  # Title: Value
            r'([A-Z][a-zA-Z\s]+)\s*=\s*([^\n\r]*)',  # Title = Value
            r'([A-Z][a-zA-Z\s]+)\s*:\s*([^\n\r]*)',  # Title : Value
            r'([A-Z][a-zA-Z\s]+)\s*_+\s*([^\n\r]*)',  # Title _____ Value
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                key, value = match
                key = key.strip()
                value = value.strip()
                
                # Filter out very short or empty keys
                if key and len(key) > 2 and value:
                    fields.append({
                        "key": key,
                        "value": value,
                        "type": "text",
                        "page": page_num,
                        "method": "pattern_matching"
                    })
        
        return fields
    
    def _extract_with_ai_vision(self, pdf_path: str) -> List[Dict]:
        """Extract fields using Gemini Vision API."""
        try:
            if not FITZ_AVAILABLE:
                logger.warning("PyMuPDF not available for image conversion")
                return []
            
            doc = fitz.open(pdf_path)
            all_fields = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # Use AI vision to analyze
                fields = self._analyze_image_with_ai(img_data, page_num + 1)
                all_fields.extend(fields)
            
            doc.close()
            return all_fields
            
        except Exception as e:
            logger.error(f"AI vision extraction error: {e}")
            return []
    
    def _analyze_image_with_ai(self, img_data: bytes, page_num: int) -> List[Dict]:
        """Analyze image using Gemini Vision."""
        try:
            # Convert to base64
            img_base64 = base64.b64encode(img_data).decode()
            
            prompt = f"""
            Analyze this document image and extract all form fields, keys, and their corresponding values.
            
            Look for:
            1. Form field names/labels (e.g., "Name:", "Date:", "Address:")
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
            
            This is page {page_num} of the document.
            """
            
            response = self.model.generate_content([
                prompt, 
                {"mime_type": "image/png", "data": img_base64}
            ])
            
            try:
                result = json.loads(response.text)
                if isinstance(result, list):
                    for field in result:
                        field["page"] = page_num
                        field["method"] = "Gemini Vision"
                    return result
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI response as JSON on page {page_num}")
        
        except Exception as e:
            logger.error(f"AI image analysis error on page {page_num}: {e}")
        
        return []
    
    def compare_documents_enhanced(self, template_pdf: str, filled_pdf: str) -> Dict:
        """
        Enhanced document comparison with detailed field mapping.
        """
        logger.info("Performing enhanced document comparison...")
        
        # Extract fields from both documents
        template_result = self.extract_form_fields(template_pdf)
        filled_result = self.extract_form_fields(filled_pdf)
        
        if template_result["status"] == "error" or filled_result["status"] == "error":
            return {
                "status": "error",
                "template_error": template_result.get("error"),
                "filled_error": filled_result.get("error")
            }
        
        template_fields = template_result.get("extracted_fields", [])
        filled_fields = filled_result.get("extracted_fields", [])
        
        # Create detailed field mapping
        field_mapping = self._create_detailed_mapping(template_fields, filled_fields)
        
        return {
            "template_pdf": template_pdf,
            "filled_pdf": filled_pdf,
            "template_info": template_result,
            "filled_info": filled_result,
            "field_mapping": field_mapping,
            "comparison_summary": {
                "template_fields_count": len(template_fields),
                "filled_fields_count": len(filled_fields),
                "mapped_fields_count": len(field_mapping),
                "successfully_mapped": len([f for f in field_mapping if f["is_matched"]])
            },
            "status": "success"
        }
    
    def _create_detailed_mapping(self, template_fields: List, filled_fields: List) -> List[Dict]:
        """Create detailed field mapping between documents."""
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
                
                if score > best_score and score > 0.6:  # Lower threshold for better matching
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
                "extraction_method": template_field.get("method", "unknown"),
                "page": template_field.get("page", 1)
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
    
    def generate_detailed_report(self, analysis_results: Dict) -> str:
        """Generate a detailed human-readable report."""
        report = []
        report.append("=" * 80)
        report.append("ENHANCED PDF ANALYSIS REPORT")
        report.append("=" * 80)
        
        # Template PDF info
        if "template_info" in analysis_results:
            template = analysis_results["template_info"]
            report.append(f"\n📄 TEMPLATE PDF: {template['pdf_path']}")
            report.append(f"   File Size: {template.get('file_size_mb', 'Unknown')} MB")
            report.append(f"   PDF Type: {template.get('pdf_type', 'Unknown')}")
            report.append(f"   Extraction Methods: {', '.join(template.get('extraction_methods', []))}")
            
            if template.get("extracted_fields"):
                report.append(f"   Fields Extracted: {len(template['extracted_fields'])}")
        
        # Filled PDF info
        if "filled_info" in analysis_results:
            filled = analysis_results["filled_info"]
            report.append(f"\n📄 FILLED PDF: {filled['pdf_path']}")
            report.append(f"   File Size: {filled.get('file_size_mb', 'Unknown')} MB")
            report.append(f"   PDF Type: {filled.get('pdf_type', 'Unknown')}")
            report.append(f"   Extraction Methods: {', '.join(filled.get('extraction_methods', []))}")
            
            if filled.get("extracted_fields"):
                report.append(f"   Fields Extracted: {len(filled['extracted_fields'])}")
        
        # Field mapping results
        if "field_mapping" in analysis_results:
            mapping = analysis_results["field_mapping"]
            report.append(f"\n🔗 FIELD MAPPING RESULTS:")
            report.append("-" * 80)
            report.append(f"{'Key':<30} {'Template Value':<25} {'Filled Value':<25} {'Status':<10}")
            report.append("-" * 80)
            
            for item in mapping:
                key = item['key'][:29] if len(item['key']) > 29 else item['key']
                template_val = str(item['template_value'])[:24] if len(str(item['template_value'])) > 24 else str(item['template_value'])
                filled_val = str(item['filled_value'])[:24] if len(str(item['filled_value'])) > 24 else str(item['filled_value'])
                
                status = "✅" if item['is_matched'] else "❌"
                report.append(f"{key:<30} {template_val:<25} {filled_val:<25} {status:<10}")
        
        # Summary
        if "comparison_summary" in analysis_results:
            summary = analysis_results["comparison_summary"]
            report.append(f"\n📊 COMPARISON SUMMARY:")
            report.append(f"   Template Fields: {summary.get('template_fields_count', 0)}")
            report.append(f"   Filled Fields: {summary.get('filled_fields_count', 0)}")
            report.append(f"   Successfully Mapped: {summary.get('successfully_mapped', 0)}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report) 