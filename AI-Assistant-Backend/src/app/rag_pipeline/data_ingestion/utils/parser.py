from pathlib import Path
from app.rag_pipeline.data_ingestion.utils.clean_markdown_file import clean_markdown

# Data parsing
def parse_file(filepath: str) -> dict:
    """Read a markdown file and return its content with metadata"""
    path = Path(filepath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Cleaning Markdown to remove HTML tags
    content = clean_markdown(content)
    
    return {
        "source": path.name,
        "path": str(path),
        "content": content,
    }