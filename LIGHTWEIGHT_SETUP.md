# 🚀 Lightweight PDF Analysis Setup

## 💾 **Disk Space Solution**

Since you encountered a disk space issue, I've created a **lightweight version** that requires minimal dependencies and disk space.

## 📦 **Lightweight Dependencies**

Install only the essential packages:

```bash
pip install -r requirements_lightweight.txt
```

**This installs only:**
- `google-generativeai` (Gemini API) - ~6 MB
- `PyPDF2` (PDF processing) - ~2 MB  
- `python-dotenv` (Configuration) - ~1 MB

**Total: ~9 MB** (vs. ~50+ MB for full version)

## 🗂️ **Lightweight Files**

- `pdf_extractor_lightweight.py` - Core extractor (minimal dependencies)
- `main_lightweight.py` - Main execution script
- `test_lightweight.py` - Setup verification
- `requirements_lightweight.txt` - Minimal dependencies

## 🚀 **Quick Start (Lightweight)**

### 1. Install Minimal Dependencies
```bash
pip install -r requirements_lightweight.txt
```

### 2. Test Your Setup
```bash
python test_lightweight.py
```

### 3. Run Analysis
```bash
python main_lightweight.py
```

## 🔧 **What the Lightweight Version Does**

✅ **Basic PDF Analysis**
- File size and metadata
- Text extraction (if PyPDF2 works)
- Basic field detection

✅ **AI Analysis** (if API key provided)
- Field extraction using Gemini
- Key-value identification
- Document comparison

✅ **Fallback Support**
- Works even without all dependencies
- Graceful degradation
- Error handling

## 📊 **Comparison: Full vs Lightweight**

| Feature | Full Version | Lightweight |
|---------|-------------|-------------|
| Dependencies | ~50 MB | ~9 MB |
| PDF Types | Text + Image | Text (basic) |
| AI Vision | ✅ | ❌ |
| OCR Support | ✅ | ❌ |
| Field Mapping | Advanced | Basic |
| Disk Usage | High | Low |

## 🎯 **Recommended for You**

**Use Lightweight Version** because:
- ✅ Solves your disk space issue
- ✅ Still provides AI-powered analysis
- ✅ Works with your existing PDFs
- ✅ Easy to upgrade later

## 🔄 **Upgrade Path**

Once you have more disk space, you can:
1. Install full dependencies: `pip install -r requirements.txt`
2. Use the advanced scripts: `python demo.py`
3. Get full image/vision support

## 🚨 **Troubleshooting**

### Still Getting Disk Space Errors?
1. **Clear pip cache**: `pip cache purge`
2. **Use virtual environment**: `python -m venv venv`
3. **Install one by one**:
   ```bash
   pip install google-generativeai
   pip install PyPDF2
   pip install python-dotenv
   ```

### PyPDF2 Issues?
- The lightweight version will still work
- It will use basic file analysis instead
- You'll still get file metadata and basic info

---

**Ready to try?** Start with:
```bash
pip install -r requirements_lightweight.txt
python test_lightweight.py
``` 