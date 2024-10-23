import re


def clean_log(content):
    """
    Remove username/password details from log file content

    @param content:
    @return:
    """
    replaces = (('//.+?:.+?@', '//USER:PASSWORD@'), ('<user>.+?</user>', '<user>USER</user>'), ('<pass>.+?</pass>', '<pass>PASSWORD</pass>'),)

    for pattern, repl in replaces:
        sanitised = re.sub(pattern, repl, content)
        return sanitised
