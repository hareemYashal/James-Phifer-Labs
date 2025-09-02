# Restructured PDF Extraction Response Format

## Overview
The PDF extraction API has been restructured to provide a cleaner, more organized response format with only 3 main sections as requested.

## New Response Structure

The API now returns a JSON response with exactly 3 main sections:

```json
{
  "extracted_fields": [...],
  "general_information": [...],
  "sample_data_information": [...]
}
```

## Section Details

### 1. extracted_fields
Contains ALL extracted fields from the PDF document, including:
- Text fields
- Headers
- Sample fields
- Analysis checkboxes
- Regular checkboxes

**Example:**
```json
{
  "key": "Company Name",
  "value": "Arcadi",
  "type": "field",
  "page": 1,
  "method": "AI Vision"
}
```

### 2. general_information
Contains non-sample related fields such as:
- Company information
- Contact details
- Project information
- Administrative fields
- General checkboxes

**Example:**
```json
{
  "key": "Company Name",
  "value": "Arcadi",
  "type": "field",
  "page": 1,
  "method": "AI Vision"
}
```

### 3. sample_data_information
Contains structured sample data grouped by Customer Sample ID. Each sample includes:

#### Standard Format:
```json
{
  "Customer Sample ID": "DW-01",
  "Matrix": "DW",
  "Comp/Grab": "G",
  "Composite Start Date": "NIL",
  "Composite Start Time": "NIL",
  "Composite/Collected Date": "6-25-25",
  "Composite/Collected Time": "815",
  "# Cont": "1",
  "Residual Chloride Result": "-",
  "Residual Chloride Units": "-",
  "analysis_requests": {
    "8240": "unchecked",
    "TPH": "unchecked",
    "8080": "unchecked"
  }
}
```

#### R & C Work Order Format:
```json
{
  "R & C Work Order": "NIL",
  "YR__ DATE": "NIL",
  "TIME": "NIL",
  "SAMPLE DESCRIPTION": "DW-01",
  "Total Number of Containers": "NIL",
  "parameters": {
    "8240": {
      "checkbox_value": "unchecked",
      "Filtered (Y/N)": "NIL",
      "Cooled (Y/N)": "NIL",
      "Container Type (Plastic (P) / Glass (G))": "NIL",
      "Container Volume in mL": "NIL",
      "Sample Type (Grab (G) / Composite (C))": "NIL",
      "Sample Source (WW, GW, DW, SW, S, Others)": "NIL"
    }
  }
}
```

## Key Improvements

### 1. Checkbox Normalization
All checkbox values are now properly normalized to either:
- `"checked"` - for checked checkboxes
- `"unchecked"` - for unchecked checkboxes

No more `"-"` or `"NIL"` values for checkboxes.

### 2. Format Detection
The system automatically detects whether a document is in:
- **Standard format** - Regular chain-of-custody forms
- **R & C Work Order format** - Special format with parameter metadata

### 3. Structured Sample Data
Sample data is now organized by Customer Sample ID with all related information grouped together, making it easier to process and understand.

### 4. Clean Response Structure
Removed unnecessary sections like:
- `all_checkboxes`
- `sample_analysis_mapping`
- `sample_ids`
- `analysis_requests`
- `extraction_summary`
- `extraction_methods`

## Usage

The API endpoint remains the same:
```
POST /extract
```

Upload a PDF file and receive the restructured response with the 3 main sections as described above.

## Files Modified

1. **pdf_extractor_restructured.py** - New extractor with restructured output
2. **api.py** - Updated to use the new extractor
3. **test_restructured_api.py** - Test script for the new API

## Testing

Run the test script to verify the new structure:
```bash
python test_restructured_api.py
```

Or test the extractor directly:
```bash
python pdf_extractor_restructured.py
```
