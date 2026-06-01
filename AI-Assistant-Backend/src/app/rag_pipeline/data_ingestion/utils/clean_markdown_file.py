import re

# Clean Markdown - Removing HTML Tags
def clean_markdown(text: str) -> str:
    """Remove HTML tags, badges, and style blocks from markdown."""

    # Remove <style>...</style> blocks
    text = re.sub(r"<style[\s\S]*?</style>", "", text)

    # Remove HTML tags but keep their text content
    text = re.sub(r"<[^>]+>", "", text)

    # Remove image markdown that are just badges
    # ![Test](https://img.shields.io/...) → removed
    text = re.sub(r"!\[.*?\]\(https://img\.shields\.io/.*?\)", "", text)

    # Remove excessive blank lines left behind
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()