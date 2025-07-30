from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import shutil
import docker
from docker.errors import ContainerError

router = APIRouter()
client = docker.from_env()

# Set up input/output directories (absolute paths)
PHASTEST_INPUT_DIR = os.path.abspath("tmp/input")
PHASTEST_OUTPUT_DIR = os.path.abspath("tmp/output")

os.makedirs(PHASTEST_INPUT_DIR, exist_ok=True)
os.makedirs(PHASTEST_OUTPUT_DIR, exist_ok=True)

@router.post("/run/phastest")
async def run_phastest(
    file: UploadFile = File(...),
    mode: str = Form("lite")  # lite or deep
):
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "No filename provided"})

    # Save uploaded file
    safe_filename = os.path.basename(file.filename)
    input_path = os.path.join(PHASTEST_INPUT_DIR, safe_filename)

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Launch PHASTEST container
        container_output = client.containers.run(
            image="wishartlab/phastest-docker",
            command=[
                "phastest",
                "-i", "fasta",
                "-s", f"/inputs/{safe_filename}",
                "-m", mode,
                "--yes"
            ],
            volumes={
                PHASTEST_INPUT_DIR: {"bind": "/inputs", "mode": "rw"},
                PHASTEST_OUTPUT_DIR: {"bind": "/outputs", "mode": "rw"},
            },
            working_dir="/app",
            remove=True
        )
    except ContainerError as e:
        return JSONResponse(status_code=500, content={
            "error": f"{str(e)}",
            "stderr": e.stderr if e.stderr else "No stderr"
        })

    return {
        "message": "PHASTEST completed successfully",
        "input_file": input_path,
        "mode": mode,
        "container_output": container_output.decode() if container_output else ""
    }
