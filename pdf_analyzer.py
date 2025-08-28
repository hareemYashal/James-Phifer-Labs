import os
import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
import io
import base64
import json
from typing import Dict, List, Tuple, Optional
import logging
from config import GEMINI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFAnalyzer:
    def __init__(self, api_key: str = None):
        """Initialize the PDF Analyzer with Gemini API."""
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key or self.api_key == 'your_gemini_api_key_here':
            raise ValueError("Please set your Gemini API key in config.py or pass it as parameter")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def analyze_pdf(self, pdf_path: str) -> Dict:
        """
        Analyze a PDF file and extract keys and values.
        Returns a dictionary with extracted information.
        """
        try:
            logger.info(f"Analyzing PDF: {pdf_path}")
            
            # Open PDF
            doc = fitz.open(pdf_path)
            
            # Determine PDF type and extract content
            pdf_type = self._determine_pdf_type(doc)
            logger.info(f"PDF Type: {pdf_type}")
            
            if pdf_type == "text":
                content = self._extract_text_content(doc)
                extracted_data = self._extract_keys_with_gemini_text(content)
            else:
                content = self._extract_image_content(doc)
                extracted_data = self._extract_keys_with_gemini_vision(content)
            
            doc.close()
            
            return {
                "pdf_path": pdf_path,
                "pdf_type": pdf_type,
                "extracted_data": extracted_data,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing PDF {pdf_path}: {str(e)}")
            return {
                "pdf_path": pdf_path,
                "status": "error",
                "error": str(e)
            }
    
    def _determine_pdf_type(self, doc) -> str:
        """Determine if PDF is text-based or image-based."""
        text_content = ""
        for page in doc:
            text_content += page.get_text()
        
        # If text content is substantial, it's text-based
        if len(text_content.strip()) > 100:
            return "text"
        return "image"
    
    def _extract_text_content(self, doc) -> str:
        """Extract text content from text-based PDF."""
        text_content = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_content += f"\n--- Page {page_num + 1} ---\n"
            text_content += page.get_text()
        return text_content
    
    def _extract_image_content(self, doc) -> List[Image.Image]:
        """Extract images from image-based PDF."""
        images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        return images
    
    def _extract_keys_with_gemini_text(self, text_content: str) -> Dict:
        """Extract keys and values from text content using Gemini."""
        prompt = f"""
        Analyze the following document content and extract all form fields, keys, and their corresponding values.
        
        Please identify:
        1. Form field names/labels
        2. Values filled in those fields
        3. Any empty fields
        4. Field types (text, checkbox, date, etc.)
        
        Return the results in a structured JSON format like this:
        {{
            "fields": [
                {{
                    "key": "field_name",
                    "value": "field_value",
                    "type": "field_type",
                    "is_filled": true/false
                }}
            ]
        }}
        
        Document content:
        {text_content[:8000]}  # Limit content for API
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Try to parse JSON response
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, return structured text
                return {
                    "fields": [{"key": "raw_text", "value": response.text, "type": "text", "is_filled": True}],
                    "raw_response": response.text
                }
        except Exception as e:
            logger.error(f"Error with Gemini API: {str(e)}")
            return {"error": str(e)}
    
    def _extract_keys_with_gemini_vision(self, images: List[Image.Image]) -> Dict:
        """Extract keys and values from images using Gemini Vision."""
        all_fields = []
        
        for i, img in enumerate(images):
            try:
                # Convert image to base64 for API
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                prompt = f"""
                Analyze this document image and extract all form fields, keys, and their corresponding values.
                
                Please identify:
                1. Form field names/labels
                2. Values filled in those fields
                3. Any empty fields
                4. Field types (text, checkbox, date, etc.)
                
                Return the results in a structured JSON format like this:
                {{
                    "fields": [
                        {{
                            "key": "field_name",
                            "value": "field_value",
                            "type": "field_type",
                            "is_filled": true/false
                        }}
                    ]
                }}
                
                This is page {i + 1} of the document.
                """
                
                response = self.model.generate_content([prompt, {"mime_type": "image/png", "data": img_base64}])
                
                try:
                    result = json.loads(response.text)
                    if "fields" in result:
                        all_fields.extend(result["fields"])
                except json.JSONDecodeError:
                    # If JSON parsing fails, add raw response
                    all_fields.append({
                        "key": f"page_{i+1}_raw",
                        "value": response.text,
                        "type": "text",
                        "is_filled": True
                    })
                    
            except Exception as e:
                logger.error(f"Error processing image {i}: {str(e)}")
                all_fields.append({
                    "key": f"page_{i+1}_error",
                    "value": str(e),
                    "type": "error",
                    "is_filled": False
                })
        
        return {"fields": all_fields}
    
    def compare_documents(self, template_pdf: str, filled_pdf: str) -> Dict:
        """
        Compare a template PDF with a filled PDF to show key-value mappings.
        """
        logger.info("Comparing documents...")
        
        # Analyze both PDFs
        template_data = self.analyze_pdf(template_pdf)
        filled_data = self.analyze_pdf(filled_pdf)
        
        if template_data["status"] == "error" or filled_data["status"] == "error":
            return {
                "status": "error",
                "template_error": template_data.get("error"),
                "filled_error": filled_data.get("error")
            }
        
        # Extract fields from both
        template_fields = template_data.get("extracted_data", {}).get("fields", [])
        filled_fields = filled_data.get("extracted_data", {}).get("fields", [])
        
        # Create comparison mapping
        comparison = {
            "template_pdf": template_pdf,
            "filled_pdf": filled_pdf,
            "comparison": []
        }
        
        # Match fields and show values
        for template_field in template_fields:
            template_key = template_field.get("key", "")
            
            # Find matching field in filled PDF
            matching_field = None
            for filled_field in filled_fields:
                if filled_field.get("key", "") == template_key:
                    matching_field = filled_field
                    break
            
            comparison["comparison"].append({
                "key": template_key,
                "template_value": template_field.get("value", ""),
                "filled_value": matching_field.get("value", "") if matching_field else "Not found",
                "is_filled": bool(matching_field and matching_field.get("value")),
                "field_type": template_field.get("type", "unknown")
            })
        
        return comparison 