# parser.py
def parse_command(text: str):
    """Parsing perintah deterministic. Hanya kenali /command"""
    if not text.startswith('/'):
        return None, []
    parts = text.split()
    cmd = parts[0][1:].lower()  # buang '/' dan lower
    args = parts[1:]
    return cmd, args
