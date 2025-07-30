import shutil
from pathlib import Path

def clean_output_dir(directory: str, keep_exts: set = {".xlsx"}):
    for item in Path(directory).glob("*"):
        if item.is_file():
            if item.suffix.lower() not in keep_exts:
                item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
