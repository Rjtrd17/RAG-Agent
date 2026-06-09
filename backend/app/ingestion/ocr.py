"""
OCR module — extracts text from PDFs using a hybrid pdfplumber + Tesseract approach.
Implements OpenCV pre-processing for scanned images and sequential memory-safe OCR.
Provides file hashing for dedup and scanned-PDF detection.

Output: docs/ocr_output/<title>.txt
"""
import hashlib
import io
import gc  # Added for explicit garbage collection
import concurrent.futures
from pathlib import Path
from typing import Optional

import pdfplumber
import pdf2image
import pytesseract
import cv2
import numpy as np
import shutil
import uuid
import click
from rich.logging import RichHandler
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn


# ── Thresholds ──
_MIN_TEXT_CHARS = 50
_OCR_NATIVE_RATIO_THRESHOLD = 1.2


def extract_text_from_pdf(filepath: str) -> list[dict]:
    try: 
        """
        Hybrid extraction strategy based on: pdfplumber -> OpenCV -> Tesseract
        Returns: List of dicts: [{page_no: int, text: str}, ...]
        """
        native_pages = []
        total_chars = 0

        # 1. Native text extraction & assessment
        with pdfplumber.open(filepath) as pdf:
            num_pages = len(pdf.pages)
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text = text.strip()
                total_chars += len(text)
                native_pages.append({"page_no": page_idx + 1, "text": text})

        if num_pages == 0:
            return []

        avg_chars_per_page = total_chars / num_pages
        trigger_full_ocr = False

        # 2. Decision Logic
        if avg_chars_per_page < _MIN_TEXT_CHARS:
            # SCANNED → Full OCR
            trigger_full_ocr = True
        else:
            # TEXT-BASED → Check quality on 3 sample pages
            sample_indices = _get_sample_indices(num_pages)
            native_sample_text = "".join(native_pages[idx]["text"] for idx in sample_indices)

            # Convert each sample page individually to avoid loading intermediate pages
            ocr_sample_text = _run_ocr_on_pages_individual(filepath, sample_indices)

            if len(native_sample_text) == 0 or (
                len(ocr_sample_text) > _OCR_NATIVE_RATIO_THRESHOLD * len(native_sample_text)
            ):
                # OCR yields > 120% more text → Full OCR
                trigger_full_ocr = True

        # 3. Execution
        if trigger_full_ocr:
            all_indices = list(range(num_pages))
            ocr_text_by_page = _run_ocr_on_pages(filepath, all_indices, return_list=True)
            final_pages = [
                {"page_no": idx + 1, "text": text}
                for idx, text in zip(all_indices, ocr_text_by_page)
            ]
        else:
            # Keep pdfplumber native text
            final_pages = native_pages

        # 4. Save to docs/ocr_output/<title>.txt
        _save_ocr_output(filepath, final_pages)

        # 5. PDF done → move to processed/
        _move_pdf_to_processed(filepath)
        
        return final_pages

    except Exception as e:
        # OCR failed → move PDF to failed/
        _move_pdf_to_failed(filepath)
        raise e   # FIXED: Indented properly inside the exception block to prevent reraise failures


def _get_sample_indices(num_pages: int) -> list[int]:
    if num_pages <= 3:
        return list(range(num_pages))
    return [0, num_pages // 2, num_pages - 1]


def _run_ocr_on_pages(filepath: str, page_indices: list[int], return_list: bool = False):
    """
    FIXED: Processes pages sequentially one-by-one and frees memory immediately.
    This guarantees that the container memory consumption remains flat regardless
    of how many pages the PDF document contains.
    """
    results = []

    for idx in page_indices:
        page_num = idx + 1
        
        # Stream exactly ONE page into memory at a time
        images = pdf2image.convert_from_path(
            filepath, dpi=300, first_page=page_num, last_page=page_num
        )

        if images:
            # Run layout processing and OCR text isolation
            page_text = _preprocess_and_ocr(images[0])
            results.append(page_text)
            
            # Explicitly clear image objects from local scope
            del images
        else:
            results.append("")

        # Force garbage collection to purge memory before moving to the next page
        gc.collect()

    if return_list:
        return results
    return "\n".join(results)


def _run_ocr_on_pages_individual(filepath: str, page_indices: list[int]) -> str:
    """
    Converts and processes sample check pages individually.
    """
    results = []
    for idx in page_indices:
        page_num = idx + 1
        imgs = pdf2image.convert_from_path(
            filepath, dpi=300, first_page=page_num, last_page=page_num
        )
        if imgs:
            page_text = _preprocess_and_ocr(imgs[0])
            results.append(page_text)
            del imgs
        gc.collect()

    return "\n".join(results)


def _preprocess_and_ocr(image) -> str:
    # Convert PIL Image to OpenCV format
    img_np = np.array(image)

    # 1. Grayscale
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # 2. Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # 3. Adaptive Thresh (Inverted so text is white on black background)
    thresh_inv = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    # 4. Deskew
    raw_coords = np.column_stack(np.where(thresh_inv > 0))
    coords = raw_coords[:, ::-1]  # (row, col) → (col, row) = (x, y)

    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle > 45:
            angle = angle - 90
        elif angle < -45:
            angle = angle + 90

        # Clamp to realistic slight skews to prevent vertical text flipping
        if -10 <= angle <= 10 and angle != 0.0:
            (h, w) = thresh_inv.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed_inv = cv2.warpAffine(
                thresh_inv, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
        else:
            deskewed_inv = thresh_inv
    else:
        deskewed_inv = thresh_inv

    # 5. Morph close
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morphed_inv = cv2.morphologyEx(deskewed_inv, cv2.MORPH_CLOSE, kernel)

    # Invert back to black text on white background for Tesseract
    final_img = cv2.bitwise_not(morphed_inv)

    text = pytesseract.image_to_string(final_img, lang="eng")
    
    # Explicitly release heavy local numpy arrays from reference memory
    del img_np, gray, denoised, thresh_inv, deskewed_inv, morphed_inv, final_img

    return text.strip()


def _save_ocr_output(filepath: str, pages: list[dict]):
    path = Path(filepath)
    ocr_dir = Path("docs") / "ocr_output"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    out_file = ocr_dir / f"{path.stem}.txt"

    full_text = "\n\n".join(
        [f"--- Page {p['page_no']} ---\n{p['text']}" for p in pages]
    )
    out_file.write_text(full_text, encoding="utf-8")


def extract_text_from_txt(filepath: str) -> list[dict]:
    path = Path(filepath)
    content = path.read_text(encoding="utf-8", errors="replace")
    return [{"page_no": 1, "text": content.strip()}]


def compute_file_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):  # 64 KB blocks
            sha256.update(block)
    return sha256.hexdigest()


def is_scanned_pdf(filepath: str) -> bool:
    scanned_count = 0
    with pdfplumber.open(filepath) as pdf:
        if len(pdf.pages) == 0:
            return False
        for page in pdf.pages:
            text = page.extract_text() or ""
            if len(text.strip()) < _MIN_TEXT_CHARS:
                scanned_count += 1
        return (scanned_count / len(pdf.pages)) > 0.5

def _move_pdf_to_processed(filepath: str) -> None:
    path = Path(filepath)
    dest_dir = path.parent.parent / "processed"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    if dest.exists():
        dest = dest_dir / f"{path.stem}_{uuid.uuid4().hex[:8]}{path.suffix}"
    shutil.move(str(path), str(dest))

def _move_pdf_to_failed(filepath: str) -> None:
    path = Path(filepath)
    dest_dir = path.parent.parent / "failed"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    if dest.exists():
        dest = dest_dir / f"{path.stem}_{uuid.uuid4().hex[:8]}{path.suffix}"
    shutil.move(str(path), str(dest))

@click.command()
@click.option(
    "--dir", "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="docs/incoming",
    show_default=True,
    help="Directory of PDFs to OCR.",
)
@click.option(
    "--file", "single_file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Single PDF to OCR.",
)
def main(directory: Optional[Path], single_file: Optional[Path]) -> None:

    console = Console()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s", # RichHandler adds its own timestamps/tags automatically
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    
    files = []
    if single_file:
        files.append(single_file)
    if directory:
        files.extend(Path(directory).glob("*.pdf"))
        files.extend(Path(directory).glob("*.PDF"))

    files = sorted(set(files))

    if not files:
        console.print("[yellow]No PDFs found in incoming/.[/yellow]")
        return

    console.print(f"\n[bold green]Found {len(files)} PDF(s) to OCR.[/bold green]\n")

    success, failed = 0, 0

    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  BarColumn(), TimeRemainingColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Running OCR...", total=len(files))

        for pdf in files:
            try:
                progress.update(task, description=f"[cyan]OCR: {pdf.name}")
                extract_text_from_pdf(str(pdf))   # moves pdf internally
                success += 1
            except Exception as e:
                logging.error("Failed: %s — %s", pdf.name, e)
                failed += 1
            finally:
                # Top-level script loop garbage collection sweep
                gc.collect()
            progress.advance(task)

    console.print(f"\n[green]✓ Done:[/green] {success}   [red]✗ Failed:[/red] {failed}\n")


if __name__ == "__main__":
    main()