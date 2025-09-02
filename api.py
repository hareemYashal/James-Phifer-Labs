from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import json
import tempfile
from pdf_extractor_restructured import RestructuredPDFExtractor

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="PDF Extraction API", version="1.0.0", description="Single endpoint to extract all fields and checkboxes from PDF documents")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {
        "message": "PDF Extraction API - Single endpoint for comprehensive extraction",
        "usage": "Upload a PDF to /extract to get all extracted information",
        "endpoints": {
            "/extract": "Main endpoint - upload PDF and get complete extraction results"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/extract")
async def extract_pdf(file: UploadFile = File(...)):
    """
    Single endpoint to extract ALL fields, values, and checkboxes from a PDF document.
    
    This endpoint works exactly like pdf_extractor.py and extracts:
    - Every single field and value from the PDF
    - All checkboxes (both box-style and bracket-style [ ])
    - Sample ID to Analysis Request mappings
    - Data Deliverables checkboxes (Level II, III, IV, Equis, Others)
    - Rush options (Same Day, 1 Day, 2 Day, 3 Day, Others)
    - Time Zone checkboxes (AM, PT, MT, CT, ET)
    - Container Size and Preservative Type values
    - Reportable checkboxes (Yes, No)
    - All other checkboxes and fields
    
    Returns the complete extraction result in the same format as pdf_extractor.py
    """
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Extract from PDF using the restructured extractor
        extractor = RestructuredPDFExtractor()
        result = extractor.extract_comprehensive(temp_file_path)
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        # Validate result
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=f"Extraction failed: {result.get('error', 'Unknown error')}")
        
        # Return the restructured result
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
