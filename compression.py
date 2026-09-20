"""Compresses a file or directory into a single .zip archive."""
import os
import zipfile


def compress_path(source_path: str, output_zip: str) -> str:
    source_path = os.path.abspath(source_path)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(source_path):
            for root, _, files in os.walk(source_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, start=os.path.dirname(source_path))
                    zf.write(full_path, arcname)
        else:
            zf.write(source_path, os.path.basename(source_path))
    return output_zip


def decompress_zip(zip_path: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    return dest_dir
