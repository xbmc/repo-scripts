import glob
import os

import re

START_WITH = 32040

files = glob.glob('*.py')
for f in files:
    pass


def contains_alpha(str):
    for c in str:
        if c.isalpha():
            return True

    return False


def is_interesting_str(str):
    return ' ' in str and contains_alpha(str)


trans_dict = {}


def get_line_and_po(n, original_line):
    global trans_dict
    matches = re.findall('"(.*?)"', original_line)
    matches += re.findall('\'(.*)\'', original_line)
    assert len(matches) == 1
    if original_line in trans_dict:
        n = trans_dict[original_line]
        po = None
    else:
        trans_dict[original_line] = n
        po = """
msgctxt "#%d"
msgid "%s"
msgstr ""

""" % (n, matches[0])
    python_code_string = 'localize(%d)' % n
    new_line = original_line[:]
    new_line = new_line.replace('\'%s\'' % matches[0], python_code_string)
    new_line = new_line.replace('"%s"' % matches[0], python_code_string)

    return original_line, new_line, po


def iterate_commented_lines(commented_lines):
    for n, line in enumerate(commented_lines):
        yield get_line_and_po(START_WITH + n, line)


def extract_by_comment(fname):
    c = open('unlocalized/%s' % fname).read()
    commented_lines = re.findall("\n(.*?)# @@", c)
    po_c = ''
    for original_line, new_line, po in iterate_commented_lines(commented_lines):
        c = c.replace(original_line, new_line)
        if po is not None:
            po_c += po

    if not os.path.isdir('localized'):
        os.makedirs('localized')
    open('%s' % fname, 'wb').write(c)
    open('resources/language/resource.language.en_gb/strings.po', 'ab').write(po_c)


if __name__ == '__main__':
    extract_by_comment('intent_handlers.py')
