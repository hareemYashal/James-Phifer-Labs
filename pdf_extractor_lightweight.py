#!/usr/bin/env python3
"""
Lightweight PDF Key-Value Extractor using Gemini 2.5 API
Minimal dependencies for systems with limited disk space.
"""

import os
import json
import base64
import io
from typing import Dict, List, Optional
import logging
from config import GEMINI_API_KEY

# Try to import PyPDF2, fallback to basic text extraction if not available
try:
    import PyPDF2
    PDF2_AVAILABLE = True
except ImportError:
    PDF2_AVAILABLE = False
    print("⚠️  PyPDF2 not available - using basic text extraction")

# Try to import Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Gemini API not available - using basic extraction only")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightweightPDFExtractor:
    def __init__(self, api_key: str = None):
        """Initialize the Lightweight PDF Extractor."""
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
                logger.warning("⚠️  No Gemini API key provided - using basic extraction only")
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extract text and basic information from PDF.
        """
        try:
            logger.info(f"Extracting from PDF: {pdf_path}")
            
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
                "extraction_methods": []
            }
            
            # Method 1: Try PyPDF2 extraction
            if PDF2_AVAILABLE:
                text_content = self._extract_with_pypdf2(pdf_path)
                if text_content:
                    file_info["extraction_methods"].append("PyPDF2")
                    file_info["text_content"] = text_content
                    file_info["text_length"] = len(text_content)
                    
                    # Try to extract fields using AI if available
                    if self.gemini_ready:
                        fields = self._extract_fields_with_ai(text_content)
                        file_info["extracted_fields"] = fields
                        file_info["extraction_methods"].append("Gemini AI")
            
            # Method 2: Basic file analysis
            if not file_info.get("text_content"):
                file_info["extraction_methods"].append("File Analysis")
                file_info["status"] = "success"
                file_info["message"] = "PDF processed (text extraction not available)"
            else:
                file_info["status"] = "success"
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return {
                "pdf_path": pdf_path,
                "status": "error",
                "error": str(e)
            }
    
    def _extract_with_pypdf2(self, pdf_path: str) -> Optional[str]:
        """Extract text using PyPDF2."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                text_content = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n--- Page {page_num + 1} ---\n"
                            text_content += page_text
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {e}")
                        continue
                
                return text_content if text_content.strip() else None
                
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {e}")
            return None
    
    def _extract_fields_with_ai(self, text_content: str) -> List[Dict]:
        """Extract fields using Gemini AI."""
        try:
            # Limit content for API
            limited_text = text_content[:4000] if len(text_content) > 4000 else text_content
            
            prompt = f"""
            Analyze this document text and extract form fields, keys, and values.
            
            Look for:
            1. Field names/labels (e.g., "Name:", "Date:", "Address:")
            2. Values associated with those fields
            3. Empty fields that need to be filled
            
            Return ONLY a valid JSON array like this:
            [
                {{
                    "key": "field_name",
                    "value": "field_value",
                    "type": "field_type"
                }}
            ]
            
            Document text:
            {limited_text}
            """
            
            response = self.model.generate_content(prompt)
            
            try:
                result = json.loads(response.text)
                if isinstance(result, list):
                    return result
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON")
                return []
                
        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return []
    
    def compare_documents(self, template_pdf: str, filled_pdf: str) -> Dict:
        """
        Compare two PDF documents and identify differences.
        """
        logger.info("Comparing documents...")
        
        # Extract from both PDFs
        template_result = self.extract_from_pdf(template_pdf)
        filled_result = self.extract_from_pdf(filled_pdf)
        
        if template_result["status"] == "error" or filled_result["status"] == "error":
            return {
                "status": "error",
                "template_error": template_result.get("error"),
                "filled_error": filled_result.get("error")
            }
        
        # Basic comparison
        comparison = {
            "template_pdf": template_pdf,
            "filled_pdf": filled_pdf,
            "template_info": template_result,
            "filled_info": filled_result,
            "comparison_summary": {}
        }
        
        # Compare file sizes
        template_size = template_result.get("file_size_mb", 0)
        filled_size = filled_result.get("file_size_mb", 0)
        comparison["comparison_summary"]["file_sizes"] = {
            "template_mb": template_size,
            "filled_mb": filled_size,
            "size_difference_mb": round(filled_size - template_size, 2)
        }
        
        # Compare text content if available
        if template_result.get("text_content") and filled_result.get("text_content"):
            template_text = template_result["text_content"]
            filled_text = filled_result["text_content"]
            
            comparison["comparison_summary"]["text_analysis"] = {
                "template_text_length": len(template_text),
                "filled_text_length": len(filled_text),
                "text_difference": len(filled_text) - len(template_text)
            }
        
        # Compare extracted fields if available
        template_fields = template_result.get("extracted_fields", [])
        filled_fields = filled_result.get("extracted_fields", [])
        
        if template_fields and filled_fields:
            comparison["comparison_summary"]["fields_analysis"] = {
                "template_fields_count": len(template_fields),
                "filled_fields_count": len(filled_fields),
                "fields_difference": len(filled_fields) - len(template_fields)
            }
        
        comparison["status"] = "success"
        return comparison
    
    def generate_report(self, analysis_results: Dict) -> str:
        """Generate a human-readable report."""
        report = []
        report.append("=" * 60)
        report.append("PDF ANALYSIS REPORT")
        report.append("=" * 60)
        
        if "template_info" in analysis_results:
            template = analysis_results["template_info"]
            report.append(f"\n📄 TEMPLATE PDF: {template['pdf_path']}")
            report.append(f"   File Size: {template.get('file_size_mb', 'Unknown')} MB")
            report.append(f"   Extraction Methods: {', '.join(template.get('extraction_methods', []))}")
            
            if template.get("extracted_fields"):
                report.append(f"   Fields Extracted: {len(template['extracted_fields'])}")
        
        if "filled_info" in analysis_results:
            filled = analysis_results["filled_info"]
            report.append(f"\n📄 FILLED PDF: {filled['pdf_path']}")
            report.append(f"   File Size: {filled.get('file_size_mb', 'Unknown')} MB")
            report.append(f"   Extraction Methods: {', '.join(filled.get('extraction_methods', []))}")
            
            if filled.get("extracted_fields"):
                report.append(f"   Fields Extracted: {len(filled['extracted_fields'])}")
        
        if "comparison_summary" in analysis_results:
            summary = analysis_results["comparison_summary"]
            report.append(f"\n📊 COMPARISON SUMMARY:")
            
            if "file_sizes" in summary:
                sizes = summary["file_sizes"]
                report.append(f"   File Size Difference: {sizes['size_difference_mb']} MB")
            
            if "text_analysis" in summary:
                text = summary["text_analysis"]
                report.append(f"   Text Length Difference: {text['text_difference']} characters")
            
            if "fields_analysis" in summary:
                fields = summary["fields_analysis"]
                report.append(f"   Fields Count Difference: {fields['fields_difference']}")
        
        report.append("\n" + "=" * 60)
        return "\n".join(report) 