import re


def clean_log(content: str) -> str:
    """
    Remove username/password details from log file content

    @param content:
    @return:
    """
    replaces = (
        # Replace only the credentials part between '//' and '@'
        (r'(?<=//)([^/@:\s]+):([^/@\s]+)@', r'USER:PASSWORD@'),
        # Also scrub username only (no password)
        (r'(?<=//)([^/@:\s]+)@', r'USER@'),
        # Replace XML username/password; keep it local to the tag
        (r'(?is)<user>[^<]*</user>', r'<user>USER</user>'),
        (r'(?is)<pass>[^<]*</pass>', r'<pass>PASSWORD</pass>'),
    )

    for pattern, repl in replaces:
        content = re.sub(pattern, repl, content)
    return content
