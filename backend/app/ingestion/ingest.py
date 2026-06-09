"""
CLI ingestion entry-point — processes PDFs and TXT files into the RAG database.

Usage:
    python -m app.ingestion.ingest --dir ./docs/incoming
    python -m app.ingestion.ingest --file ./docs/incoming/some_policy.pdf
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

# ── Project imports ──────────────────────────────────────────────
from app.core.config import get_settings
from app.db.models import Chunk, Document, Page
from app.db.models import Base
from app.db.session import sync_engine
from app.ingestion.chunker import chunk_pages
from app.ingestion.embedder import embed_texts
from app.ingestion.ocr import (
    compute_file_hash,
    extract_text_from_txt,       # extract_text_from_pdf no longer called here
)

logger = logging.getLogger(__name__)
console = Console()

# ── Supported file extensions ───────────────────────────────────
# _SUPPORTED_EXTENSIONS = {".pdf", ".txt"}
_SUPPORTED_EXTENSIONS = {".txt"}


# ── Helpers ─────────────────────────────────────────────────────


def _file_already_ingested(session: Session, file_hash: str) -> bool:
    """Check if a file with the same SHA-256 hash already exists in the DB."""
    result = session.execute(
        sa_text("SELECT 1 FROM documents WHERE file_hash = :h LIMIT 1"),
        {"h": file_hash},
    )
    return result.scalar() is not None


def _move_to_processed(filepath: Path) -> None:
    """Move a successfully ingested file from incoming/ to processed/."""
    processed_dir = filepath.parent.parent / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / filepath.name

    # Avoid overwrite collisions
    if dest.exists():
        stem = filepath.stem
        suffix = filepath.suffix
        dest = processed_dir / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"

    shutil.move(str(filepath), str(dest))
    logger.info("Moved %s → %s", filepath.name, dest)


def _move_to_failed(filepath: Path) -> None:
    """Move an unopenable or corrupted file to a failed/ directory."""
    failed_dir = filepath.parent.parent / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    dest = failed_dir / filepath.name

    if dest.exists():
        stem = filepath.stem
        suffix = filepath.suffix
        dest = failed_dir / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"

    shutil.move(str(filepath), str(dest))
    logger.warning("Moved corrupted/failed file %s → %s", filepath.name, dest)


def _update_search_vector(session: Session, page_id: str) -> None:
    """Update the tsvector search_vector column for a given page."""
    session.execute(
        sa_text(
            "UPDATE pages SET search_vector = to_tsvector('english', raw_text) "
            "WHERE id = :pid"
        ),
        {"pid": str(page_id)},
    )


# ── Single-file ingestion ──────────────────────────────────────


def ingest_file(filepath: Path, settings, progress=None, task_id=None) -> str:
    """
    Ingest a single PDF or TXT file.

    Returns:
        'ingested' | 'skipped' | 'error'
    """
    try:
        ext = filepath.suffix.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            logger.warning("Unsupported extension: %s", filepath.name)
            return "error"

        # ① Compute hash and check for duplicates
        file_hash = compute_file_hash(str(filepath))
        with Session(sync_engine) as session:
            if _file_already_ingested(session, file_hash):
                logger.info("Skipping duplicate: %s", filepath.name)
                return "skipped"

        # ② Extract text
        if progress and task_id is not None:
            progress.update(task_id, description=f"[cyan]Extracting text: {filepath.name}")

        pages = extract_text_from_txt(str(filepath))

        if not pages:
            logger.warning("No text extracted from %s", filepath.name)
            return "error"

        # ③ Chunk text
        if progress and task_id is not None:
            progress.update(task_id, description=f"[cyan]Chunking: {filepath.name}")

        chunks_data = chunk_pages(pages)

        if not chunks_data:
            logger.warning("No chunks produced from %s", filepath.name)
            return "error"

        # ④ Generate embeddings (async call from sync context)
        if progress and task_id is not None:
            progress.update(task_id, description=f"[cyan]Embedding: {filepath.name}")

        chunk_texts = [c["chunk_text"] for c in chunks_data]
        embeddings = asyncio.run(embed_texts(chunk_texts, settings))

        # ⑤ Persist to PostgreSQL
        if progress and task_id is not None:
            progress.update(task_id, description=f"[cyan]Saving: {filepath.name}")

        with Session(sync_engine) as session:
            # -- Document record
            doc = Document(
                filename=filepath.name,
                file_type=ext.lstrip("."),
                file_hash=file_hash,
                total_pages=len(pages),
            )
            session.add(doc)
            session.flush()  # get doc.id

            # Build a page_no → Page mapping for chunk FK resolution
            page_map: dict[int, Page] = {}
            for page_data in pages:
                page_obj = Page(
                    doc_id=doc.id,
                    page_no=page_data["page_no"],
                    raw_text=page_data["text"],
                )
                session.add(page_obj)
                session.flush()  # get page_obj.id
                page_map[page_data["page_no"]] = page_obj

            # -- Chunk records
            for chunk_data, embedding in zip(chunks_data, embeddings):
                page_obj = page_map[chunk_data["page_no"]]
                chunk_obj = Chunk(
                    page_id=page_obj.id,
                    doc_id=doc.id,
                    chunk_index=chunk_data["chunk_index"],
                    chunk_text=chunk_data["chunk_text"],
                    token_count=chunk_data["token_count"],
                    embedding=embedding,
                )
                session.add(chunk_obj)

            session.flush()

            # ⑥ Update tsvector for each page
            for page_obj in page_map.values():
                _update_search_vector(session, str(page_obj.id))

            session.commit()
            logger.info(
                "Ingested %s — %d pages, %d chunks",
                filepath.name,
                len(pages),
                len(chunks_data),
            )

        # ⑦ Move to processed/
        _move_to_processed(filepath)

        return "ingested"

    except Exception as e:
        logger.error("Error ingesting %s: %s", filepath.name, str(e))
        _move_to_failed(filepath)
        return "error"


# ── CLI ─────────────────────────────────────────────────────────


@click.command()
@click.option(
    "--file",
    "single_file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to a single PDF or TXT file to ingest.",
)
@click.option(
    "--dir",
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="docs/ocr_output",                          # ← default to ocr output
    show_default=True,
    help="Directory of OCR-produced TXT files to embed.",
)
def main(single_file: Optional[Path], directory: Optional[Path]) -> None:
    """Ingest PDF and TXT documents into the RAG vector database."""

    # ── TO CREATE TABLES AUTOMATICALLY ──
    logger.info("Verifying and initializing database schema tables...")
    Base.metadata.create_all(bind=sync_engine)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    if not single_file and not directory:
        console.print(
            "[red]Error:[/red] You must specify --file or --dir. "
            "Run with --help for usage.",
        )
        sys.exit(1)

    settings = get_settings()

    # Collect files to process
    files: list[Path] = []
    if single_file:
        files.append(single_file)
    if directory:
        for ext in _SUPPORTED_EXTENSIONS:
            files.extend(directory.glob(f"*{ext}"))
            files.extend(directory.glob(f"*{ext.upper()}"))

    # Deduplicate (in case of overlapping globs)
    files = sorted(set(files))

    if not files:
        console.print("[yellow]No PDF or TXT files found to ingest.[/yellow]")
        sys.exit(0)

    console.print(f"\n[bold green]Found {len(files)} file(s) to process.[/bold green]\n")

    # Counters
    ingested = 0
    skipped = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Ingesting...", total=len(files))

        for filepath in files:
            result = ingest_file(filepath, settings, progress, task_id)
            if result == "ingested":
                ingested += 1
            elif result == "skipped":
                skipped += 1
            else:
                errors += 1

            progress.advance(task_id)

    # Summary
    console.print("\n[bold]═══ Ingestion Summary ═══[/bold]")
    console.print(f"  [green]✓ Ingested:[/green]  {ingested}")
    console.print(f"  [yellow]⊘ Skipped:[/yellow]   {skipped}  (duplicate)")
    console.print(f"  [red]✗ Errors:[/red]    {errors}")
    console.print()

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
