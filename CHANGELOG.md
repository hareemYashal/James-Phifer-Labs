# Changelog

## [Latest] - 2025-01-04

### Added
- **Sample Comment Support**: Added extraction and mapping of sample comments for each sample
- **Intelligent Field Mapping**: Enhanced field mapping to handle various naming patterns (underscores, hyphens, prefixes)
- **Flexible Field Patterns**: Support for different field naming conventions across documents
- **Comprehensive Field Coverage**: Improved mapping for all sample data fields including dates, times, and container counts

### Enhanced
- **Field Mapping Logic**: Updated to handle patterns like `sample_comment_laj_430`, `collected_start_date_yot-810`, etc.
- **Sample Data Structure**: Added "Sample Comment" field to sample data information
- **Documentation**: Updated README.md, DEPLOYMENT.md, and response format documentation
- **Error Handling**: Improved field mapping with better pattern matching

### Fixed
- **NIL Value Issues**: Resolved cases where fields showed "NIL" despite being present in extracted_fields
- **Field Pattern Matching**: Fixed mapping for fields with different naming conventions
- **Sample Data Completeness**: Ensured all sample fields are properly mapped to output structure

### Technical Improvements
- **Pattern Recognition**: Added support for multiple field naming patterns
- **Field Classification**: Improved separation of general vs sample-specific fields
- **Response Structure**: Maintained clean 3-section response format (extracted_fields, general_information, sample_data_information)

## Previous Versions

### [v1.0] - Initial Release
- Basic PDF extraction using Google Gemini 2.5 Flash
- Chain-of-Custody document processing
- Web API and command-line interface
- Basic field extraction and checkbox detection
