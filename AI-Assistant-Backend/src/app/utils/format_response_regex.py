import re

def format_response(raw: str) -> str:
    """This formats the response in a structured manner.
    args:
        raw:(string that need to format)
    """
    # Wrap bare code patterns in fenced blocks
    # Detect lines that look like Python code
    lines = raw.split('\n')
    formatted = []
    in_code_block = False
    code_buffer = []

    for line in lines:
        is_code = bool(re.match(
            r'^(\s{2,})?(import |from |def |class |@|app\.|return |pip |fastapi )',
            line
        ))

        if is_code and not in_code_block:
            in_code_block = True
            lang = "bash" if re.match(r'^\s*(pip |fastapi |uvicorn )', line) else "python"
            formatted.append(f"```{lang}")
            code_buffer.append(line.strip())
        elif is_code and in_code_block:
            code_buffer.append(line.strip())
        elif not is_code and in_code_block:
            formatted.extend(code_buffer)
            formatted.append("```")
            code_buffer = []
            in_code_block = False
            formatted.append(line)
        else:
            formatted.append(line)

    if in_code_block:
        formatted.extend(code_buffer)
        formatted.append("```")

    result = '\n'.join(formatted)

    # Format URLs as markdown links
    result = re.sub(
        r'(?<![\(\[])(https?://\S+)',
        r'[\1](\1)',
        result
    )

    # Format source citations
    result = re.sub(
        r'\[Source:\s*(.+?)\s*\|\s*Section:\s*(.+?)\]',
        r'`\1` § \2',
        result
    )

    return result