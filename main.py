from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from PIL import Image
import shutil
import uuid

app = FastAPI(title="MediScan AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
CONVERTED_DIR = Path("converted")
UPLOAD_DIR.mkdir(exist_ok=True)
CONVERTED_DIR.mkdir(exist_ok=True)

# Website aur CSS/JS serve karne ke liye
app.mount("/", StaticFiles(directory=".", html=True), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("index.html")

@app.get("/ai-results.html", response_class=HTMLResponse)
async def read_results():
    return FileResponse("ai-results.html")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".dcm"}
MAX_FILE_SIZE = 50 * 1024 * 1024

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    unique_id = uuid.uuid4().hex
    original_filename = Path(file.filename).name
    saved_filename = f"{unique_id}{file_extension}"
    upload_path = UPLOAD_DIR / saved_filename
    
    try:
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    file_size = upload_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="File too large.")
    
    jpeg_filename = f"{unique_id}.jpg"
    jpeg_path = CONVERTED_DIR / jpeg_filename
    
    try:
        if file_extension in [".pdf", ".dcm"]:
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=501, detail="PDF/DICOM conversion not implemented yet.")
        else:
            image = Image.open(upload_path)
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(jpeg_path, format="JPEG", quality=95)
    except HTTPException:
        raise
    except Exception as e:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")
    
    return {
        "success": True, "message": "File uploaded and converted",
        "original_filename": original_filename, "ml_ready": True
    }
