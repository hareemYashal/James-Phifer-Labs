# PDF Key-Value Extractor using Gemini 2.5 API

This project provides an intelligent PDF analysis system that can extract form fields, keys, and values from both text-based and image-based PDFs using Google's Gemini 2.5 API.

## Features

- **Multi-format PDF Support**: Handles both text-based and image-based PDFs
- **Intelligent Field Extraction**: Uses multiple extraction methods for maximum accuracy
- **AI-Powered Analysis**: Leverages Gemini 2.5 for text and vision analysis
- **Document Comparison**: Compares template PDFs with filled PDFs
- **Field Mapping**: Intelligently maps fields between documents
- **Multiple Extraction Methods**:
  - Native PDF form field extraction
  - AI-powered text analysis
  - AI-powered image analysis (vision)
  - Pattern-based field detection

## Project Structure

```
├── config.py                 # Configuration and API key settings
├── pdf_analyzer.py          # Basic PDF analyzer
├── advanced_pdf_extractor.py # Advanced extraction with multiple methods
├── comprehensive_lab_extractor.py # Comprehensive lab document extractor
├── robust_lab_extractor.py  # Robust lab document extractor
├── enhanced_extractor.py    # Enhanced extraction capabilities
├── pdf_extractor_lightweight.py # Lightweight extraction version
├── requirements.txt         # Python dependencies
├── requirements_lightweight.txt # Lightweight dependencies
├── README.md               # This file
├── env.example             # Example environment file
└── Sample Documents/       # PDF files for analysis
    ├── COC_2014r (1).pdf  # Template PDF (unfilled)
    └── 2097_001.pdf       # Filled PDF with values
```

## Setup Instructions

### 1. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you encounter issues with `fitz` (PyMuPDF), you may need to install it separately:

```bash
pip install PyMuPDF
```

### 3. Configure API Key

Create a `.env` file in the project root and add your API key:

```bash
# Copy the example file
cp env.example .env

# Edit .env and add your actual API key
GEMINI_API_KEY=your_actual_api_key_here
```

## Usage

### Basic Usage

Run any of the available extractors:

```bash
# Basic PDF analyzer
python pdf_analyzer.py

# Advanced PDF extractor
python advanced_pdf_extractor.py

# Comprehensive lab extractor
python comprehensive_lab_extractor.py

# Robust lab extractor
python robust_lab_extractor.py
```

### Lightweight Setup

For a minimal installation, use the lightweight version:

```bash
pip install -r requirements_lightweight.txt
python pdf_extractor_lightweight.py
```

### Programmatic Usage

```python
from advanced_pdf_extractor import AdvancedPDFExtractor

# Initialize extractor
extractor = AdvancedPDFExtractor(api_key="your_api_key")

# Extract fields from a PDF
result = extractor.extract_form_fields("path/to/your.pdf")

# Compare two documents
comparison = extractor.compare_documents_advanced("template.pdf", "filled.pdf")
```

## How It Works

### 1. PDF Type Detection
The system automatically detects whether a PDF is:
- **Text-based**: Contains extractable text content
- **Image-based**: Contains only images (scanned documents)

### 2. Multi-Method Extraction

#### Method 1: Native Form Fields
- Extracts built-in PDF form fields
- Most accurate for fillable PDFs

#### Method 2: AI Text Analysis
- Analyzes text content using Gemini 2.5
- Identifies field names and values
- Handles complex document structures

#### Method 3: AI Vision Analysis
- Converts PDF pages to images
- Uses Gemini Vision to analyze document layout
- Extracts fields from scanned documents

#### Method 4: Pattern Matching
- Uses regex patterns to identify common field formats
- Fast and lightweight

### 3. Intelligent Field Mapping
- Matches fields between template and filled documents
- Calculates similarity scores
- Handles variations in field naming

## Output Format

The system generates structured JSON output with:

```json
{
  "template_analysis": {
    "pdf_path": "path/to/template.pdf",
    "pdf_type": "text|image",
    "extracted_data": {
      "fields": [
        {
          "key": "field_name",
          "value": "field_value",
          "type": "field_type",
          "page": 1,
          "method": "extraction_method"
        }
      ]
    }
  },
  "filled_analysis": { ... },
  "comparison": {
    "field_mapping": [
      {
        "key": "field_name",
        "template_value": "template_value",
        "filled_value": "filled_value",
        "similarity_score": 0.95,
        "is_matched": true
      }
    ]
  }
}
```

## Supported PDF Types

- **Text-based PDFs**: Modern PDFs with embedded text
- **Image-based PDFs**: Scanned documents, photos
- **Form PDFs**: Fillable forms with native form fields
- **Mixed PDFs**: Documents with both text and images

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure your Gemini API key is correctly set in `config.py`
   - Verify the API key is valid and has sufficient quota

2. **Installation Issues**
   - Use Python 3.8 or higher
   - Install dependencies in a virtual environment
   - For Windows users, some packages may require Visual C++ build tools

3. **PDF Processing Errors**
   - Ensure PDFs are not password-protected
   - Check if PDFs are corrupted
   - Large PDFs may take longer to process

### Performance Tips

- **Large PDFs**: Process page by page for better memory management
- **Batch Processing**: Use the advanced extractor for multiple documents
- **API Quota**: Monitor your Gemini API usage

## API Limits

- **Gemini 2.5**: Check [Google AI Studio](https://makersuite.google.com/app/apikey) for current limits
- **Image Processing**: Large images may be resized for API compatibility
- **Text Processing**: Very long documents are truncated to fit API limits

## Contributing

Feel free to contribute improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the code comments
3. Open an issue on the repository

---

**Note**: This system requires an active internet connection and valid Gemini API key to function. 