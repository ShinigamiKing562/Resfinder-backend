import os
import shutil
import docker
from docker.errors import ContainerError
from pathlib import Path
from app.utils.cleanup import clean_output_dir
from app.utils.resfinder_to_excel import generate_resfinder_excel
from fastapi import Query
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse


router = APIRouter()

client = docker.from_env()

# Set universal base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # points to Bacteriophage-backend/
TMP_DIR = BASE_DIR / "tmp"
INPUT_DIR = TMP_DIR / "input"
OUTPUT_DIR = TMP_DIR / "output"

# Create tmp/input and tmp/output if not present
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/run/resfinder")
async def run_resfinder(
    files: list[UploadFile] = File(...)
):
    species = "Other"
    results = []

    for file in files:
        if not file.filename:
            results.append({"filename": None, "status": "skipped", "reason": "No filename"})
            continue

        safe_filename = file.filename.split("/")[-1]
        input_path = INPUT_DIR / safe_filename

        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            container = client.containers.run(
                image="genomicepidemiology/resfinder",
                command=[
                    "-ifa", f"/app/input/{safe_filename}",
                    "-o", "/app/output",
                    "-s", species,
                    "--acquired"
                ],
                volumes={
                    str(INPUT_DIR): {"bind": "/app/input", "mode": "rw"},
                    str(OUTPUT_DIR): {"bind": "/app/output", "mode": "rw"}
                },
                working_dir="/app",
                remove=True
            )
            results.append({"filename": safe_filename, "status": "success"})
        except ContainerError as e:
            results.append({"filename": safe_filename, "status": "error", "reason": str(e)})

    return {
        "message": f"Processed {len(results)} file(s)",
        "results": results,
        "output_dir": str(OUTPUT_DIR)
    }


@router.get("/download_excel")
async def download_excel(json_folder: str = Query(default=str(OUTPUT_DIR))):
    excel_file = generate_resfinder_excel(json_folder)
    if not excel_file:
        return JSONResponse(
            status_code=404,
            content={"error": f"No JSON files found in {json_folder} or nothing written."}
        )

    def file_streamer(path):
        with open(path, "rb") as f:
            yield from f
        # After file is streamed, clean up JSONs (keep only .xlsx)
        clean_output_dir(json_folder, keep_exts={".xlsx"})

    return StreamingResponse(
        file_streamer(excel_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(excel_file)}"'}
    )
