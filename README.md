# Comprehensive PDF Extraction System

A powerful PDF extraction system that uses Google Gemini 2.5 Flash to extract all fields, values, and checkboxes from Chain-of-Custody Analytical Request Documents. This system provides both a web API and command-line interface for comprehensive PDF data extraction with intelligent field mapping and sample comment support.

## Features

- **Comprehensive Field Extraction**: Extracts every single field, value, and detail from PDF documents
- **Intelligent Field Mapping**: Automatically maps extracted fields to standardized output categories
- **Sample Comment Support**: Extracts and includes sample comments for each sample
- **Checkbox Detection**: Identifies all checkboxes (both box-style and bracket-style `[ ]`) and their states
- **Sample ID Mapping**: Maps which Sample IDs are checked for which Analysis Requests
- **Data Deliverables Checkboxes**: Extracts Level II, III, IV, Equis, and Others options
- **Rush Options**: Extracts Same Day, 1 Day, 2 Day, 3 Day, and Others options
- **Time Zone Collection**: Extracts AM, PT, MT, CT, ET timezone checkboxes
- **Container Information**: Extracts Container Size and Preservative Type values
- **Reportable Checkboxes**: Extracts Yes/No reportable options
- **Flexible Field Patterns**: Handles various field naming conventions (underscores, hyphens, prefixes)
- **AI-Powered Analysis**: Uses Google Gemini 2.5 Flash for accurate and detailed extraction
- **Single API Endpoint**: One endpoint to upload PDF and get all extracted information
- **Interactive Command Line**: User-friendly interface for direct PDF processing
- **Structured JSON Response**: Returns well-organized JSON with all extracted data

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pdf-extraction-system.git
   cd pdf-extraction-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get your Gemini API key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Create a new API key
   - Copy the API key

4. **Configure API Key**
   
   Create a `.env` file in the project root:
   ```bash
   cp env.example .env
   ```
   
   Edit the `.env` file and add your actual API key:
   ```
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
   
   **Important**: Replace `your_actual_gemini_api_key_here` with your real API key.

### Alternative Installation (if you encounter issues)

If you have problems with the standard installation, try:

```bash
# Install packages individually
pip install google-generativeai
pip install PyMuPDF
pip install Pillow
pip install python-dotenv
pip install fastapi
pip install uvicorn
pip install python-multipart
pip install pydantic
pip install numpy
```

## Usage

### 1. Direct Python Usage

Use the main extraction module directly:

```python
from pdf_extractor_restructured import RestructuredPDFExtractor

extractor = RestructuredPDFExtractor()
result = extractor.extract_comprehensive('path/to/your/file.pdf')
print(result)
```

This will:
- Extract all fields and checkboxes
- Return structured JSON data
- Handle all field mapping automatically
- Process multiple pages if needed

### 2. Web API Usage

Start the FastAPI server:

```bash
python api.py
```

The server will start on `http://localhost:8000`

#### API Endpoints

- **POST `/extract`**: Extract all fields, values, and checkboxes from a PDF
- **GET `/health`**: Check API health status
- **GET `/`**: API information and usage

#### API Documentation

Once the server is running, visit:
- `http://localhost:8000/docs` - Interactive API documentation
- `http://localhost:8000/redoc` - Alternative API documentation

### 3. Testing

Test the extraction with sample documents:

```python
from pdf_extractor_restructured import RestructuredPDFExtractor

extractor = RestructuredPDFExtractor()
result = extractor.extract_comprehensive('Sample Documents/COC_2036_001 (3).pdf')
print("Extraction successful!")
print(f"Found {len(result.get('sample_data_information', []))} samples")
```

## Response Format

The system returns a clean, structured JSON response with three main sections:

```json
{
  "extracted_fields": [
    {
      "key": "company_name",
      "value": "Jacqueline Ventures",
      "type": "field",
      "page": 1,
      "method": "AI Vision"
    },
    {
      "key": "sample_comment_laj_410",
      "value": "Okay",
      "type": "sample_field",
      "sample_id": "LAJ-410",
      "page": 1,
      "method": "AI Vision"
    }
  ],
  "general_information": [
    {
      "key": "company_name",
      "value": "Jacqueline Ventures",
      "type": "field",
      "page": 1,
      "method": "AI Vision"
    },
    {
      "key": "contact_person_report_to",
      "value": "Jacqueline Kingsbury",
      "type": "field",
      "page": 1,
      "method": "AI Vision"
    }
  ],
  "sample_data_information": [
    {
      "Customer Sample ID": "LAJ-410",
      "Matrix": "N",
      "Comp/Grab": "4",
      "Composite Start Date": "3/10/27",
      "Composite Start Time": "5pm",
      "Composite or Collected End Date": "3/10/27",
      "Composite or Collected End Time": "5:01",
      "# Cont": "2",
      "Residual Chloride Result": "0.1",
      "Residual Chloride Units": "mg",
      "Sample Comment": "Okay",
      "analysis_request": "Blizzard"
    }
  ]
}
```

## Field Types

The system extracts and categorizes fields into different types:

- **`header`**: Document titles and headers
- **`field`**: Regular form fields and text inputs
- **`sample_field`**: Sample-related information (ID, matrix, dates, comments, etc.)
- **`analysis_checkbox`**: Checkboxes that map Sample IDs to Analysis Requests
- **`checkbox`**: Other checkboxes (technical, administrative, etc.)

## Sample Data Structure

Each sample in `sample_data_information` includes:

- **Customer Sample ID**: Unique identifier for the sample
- **Matrix**: Sample matrix code (e.g., "N", "B", "DW")
- **Comp/Grab**: Composite or grab sample indicator
- **Composite Start Date/Time**: Collection start information
- **Composite or Collected End Date/Time**: Collection end information
- **# Cont**: Number of containers
- **Residual Chloride Result/Units**: Test results and units
- **Sample Comment**: Comments or notes for the sample
- **analysis_request**: Requested analysis type

## Checkbox Categories

The system detects and processes multiple checkbox categories:

### 1. **Data Deliverables Checkboxes**
- Level II
- Level III
- Level IV
- Equis
- Others

### 2. **Rush Options**
- Same Day
- 1 Day
- 2 Day
- 3 Day
- Others

### 3. **Time Zone Collected**
- AM
- PT (Pacific Time)
- MT (Mountain Time)
- CT (Central Time)
- ET (Eastern Time)

### 4. **Reportable Checkboxes**
- Yes
- No

### 5. **Analysis Request Checkboxes**
- Maps Sample IDs to specific Analysis Requests
- Shows which Analysis Requests are checked for each Sample ID

### 6. **Technical Checkboxes**
- Field Filtered if applicable
- Other technical parameters

### 7. **Administrative Checkboxes**
- Delivery method options
- Administrative settings

### 8. **Other Checkboxes**
- Any additional checkbox options found in the document

## Container Information

The system extracts:
- **Container Size**: Numbers/values written in boxes below container size labels
- **Container Preservative Type**: Values written in boxes below preservative type labels

## Sample ID to Analysis Request Mapping

The system creates a comprehensive mapping showing:
- Which Sample IDs exist in the document
- Which Analysis Requests are available
- Which Analysis Requests are checked for each Sample ID

## Configuration

### Environment Variables

Create a `.env` file with:

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### API Configuration

- **Model**: Gemini 2.5 Flash
- **Max file size**: 1MB per API call
- **Supported formats**: PDF only
- **Image resolution**: 2x scaling for better accuracy
- **Server binding**: localhost (127.0.0.1) for better compatibility
- **Field Mapping**: Intelligent mapping with support for various naming patterns

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your `.env` file contains the correct API key
2. **Installation Issues**: Try installing packages individually
3. **PDF Not Found**: Ensure the PDF file exists in the correct path
4. **Memory Issues**: For large PDFs, the system processes pages in batches
5. **API Connection Error**: The server now binds to localhost (127.0.0.1) instead of 0.0.0.0

### Error Handling

The system includes comprehensive error handling:
- Invalid PDFs
- API connection issues
- File processing errors
- JSON parsing errors
- User input validation

## File Structure

```
project/
├── config.py                      # Configuration and API key setup
├── pdf_extractor_restructured.py  # Main extraction logic with comprehensive field mapping
├── api.py                         # FastAPI web service
├── requirements.txt               # Python dependencies
├── README.md                     # This file
├── DEPLOYMENT.md                 # Deployment instructions
├── RESTRUCTURED_RESPONSE_FORMAT.md # Response format documentation
├── LICENSE                       # MIT License
├── .env                          # API key configuration (create this)
├── env.example                   # Example environment file
├── .gitignore                    # Git ignore rules
└── Sample Documents/             # Sample PDF files
    ├── COC_2036_001 (3).pdf     # Main test PDF
    ├── 2097_001.pdf             # Additional test PDF
    ├── COC_2014r (1).pdf        # Additional test PDF
    ├── OCR 35.pdf               # Additional test PDF
    └── OCR 37.pdf               # Additional test PDF
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Run the test suite
3. Verify your API key configuration
4. Check the API documentation at `/docs` when running the server
5. Open an issue on GitHub

## Disclaimer

This project uses the Google Gemini API. Please ensure you have proper API access and follow Google's terms of service. The API key should be kept secure and never committed to version control. 