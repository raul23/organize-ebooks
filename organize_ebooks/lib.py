"""Automatically organizes folders with potentially huge amounts of unorganized
ebooks.

This is done by renaming the files with proper names and moving them to other
folders.

This is a Python port of `organize-ebooks.sh` from `ebook-tools` written in
shell by `na--`.

Ref.: https://github.com/na--/ebook-tools
"""
import ast
import logging
import mimetypes
import os
import re
import shlex
import shutil
import string
import subprocess
import tempfile
import time
from argparse import Namespace
from copy import copy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unicodedata import normalize

from organize_ebooks import __version__

logger = logging.getLogger('organize_lib')
logger.setLevel(logging.CRITICAL + 1)


def get_re_year():
    # In bash: (19[0-9]|20[0-$(date '+%Y' | cut -b 3)])[0-9]"
    # output: (19[0-9]|20[0-1])[0-9]
    regex = '(19[0-9]|20[0-{}])[0-9]'.format(str(datetime.now())[2])
    return regex


# TODO: test it
def get_without_isbn_ignore():
    re_year = get_re_year()
    regex = ''
    # Periodicals with filenames that contain something like 2010-11, 199010, 2015_7, 20110203:
    regex += '(^|[^0-9]){}[ _\.-]*(0?[1-9]|10|11|12)([0-9][0-9])?($|[^0-9])'.format(re_year)
    # Periodicals with month numbers before the year
    regex += '|(^|[^0-9])([0-9][0-9])?(0?[1-9]|10|11|12)[ _\.-]*{}($|[^0-9])'.format(re_year)
    # Periodicals with months or issues
    regex += '|((^|[^a-z])(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(tember)?|' \
             'oct(ober)?|nov(ember)?|dec(ember)?|mag(azine)?|issue|#[ _\.-]*[0-9]+)+($|[^a-z]))'
    # Periodicals with seasons and years
    regex += '|((spr(ing)?|sum(mer)?|aut(umn)?|win(ter)?|fall)[ _\.-]*{})'.format(re_year)
    regex += '|({}[ _\.-]*(spr(ing)?|sum(mer)?|aut(umn)?|win(ter)?|fall))'.format(re_year)
    # Remove newlines
    # TODO: is it necessary?
    regex = regex.replace('\n', '')
    return regex


# =====================
# Default config values
# =====================

# Misc options
# ============
DRY_RUN = False
SYMLINK_ONLY = False
KEEP_METADATA = False
REVERSE = False

# Convert-to-txt options
# ======================
DJVU_CONVERT_METHOD = 'djvutxt'
EPUB_CONVERT_METHOD = 'epubtxt'
MSWORD_CONVERT_METHOD = 'textutil'
PDF_CONVERT_METHOD = 'pdftotext'

# Options related to extracting ISBNs from files and finding metadata by ISBN
# ===========================================================================
MAX_ISBNS = 5
# Horizontal whitespace and dash-like ASCII and Unicode characters that are
# used for better matching of ISBNs in (badly) OCR-ed books. Gathered from:
# - https://en.wikipedia.org/wiki/Whitespace_character
# - https://en.wikipedia.org/wiki/Dash#Similar_Unicode_characters
# - https://en.wikipedia.org/wiki/Dash#Common_dashes
# From: https://github.com/na--/ebook-tools/blob/master/lib.sh#L31
# NOTE: I need to escape the most important dash '-' because Python re doesn't recognize it if I don't
WSD = "[\u0009|\u0020|\u00A0|\u1680|\u2000|\u2001|\u2002|\u2003|\u2004|\u2005|\u2006|\u2007|\u2008" \
      "|\u2009|\u200A|\u202F|\u205F|\u3000|\u180E|\u200B|\u200C|\u200D|\u2060|\uFEFF|\-|\u005F|\u007E|\u00AD|\u00AF" \
      "|\u02C9|\u02CD|\u02D7|\u02DC|\u2010|\u2011|\u2012|\u203E|\u2043|\u207B|\u208B|\u2212|\u223C|\u23AF|\u23E4" \
      "|\u2500|\u2796|\u2E3A|\u2E3B|\u10191|\u2012|\u2013|\u2014|\u2015|\u2053" \
      "|\u058A|\u05BE|\u1428|\u1B78|\u3161|\u30FC|\uFE63|\uFF0D|\u10110|\u1104B|\u11052|\u110BE|\u1D360]?"
# ISBN_REGEX = '(?<![0-9])(-?9-?7[789]-?)?((-?[0-9]-?){9}[0-9xX])(?![0-9])'
# NOTE: if I use '?+' like they do in their code, I get `error: multiple repeat at position 592`
# Also, double accolades for 9 or they get removed by f-string
ISBN_REGEX = f"(?<![0-9])({WSD}9{WSD}7{WSD}[789]{WSD})?(({WSD}[0-9]{WSD}){{9}}[0-9xX])(?![0-9])"
ISBN_BLACKLIST_REGEX = '^(0123456789|([0-9xX])\\2{9})$'
ISBN_DIRECT_FILES = '^text/(plain|xml|html)$'
ISBN_IGNORED_FILES = '^(image/(gif|svg.+)|application/(x-shockwave-flash|CDFV2|vnd.ms-opentype|x-font-ttf|x-dosexec|' \
                     'vnd.ms-excel|x-java-applet)|audio/.+|video/.+)$'
# False to disable the functionality or (first_lines,last_lines) to enable it
ISBN_REORDER_FILES = [400, 50]
ISBN_RET_SEPARATOR = ' - '
# NOTE: If you use Calibre versions that are older than 2.84, it's required to
# manually set the following option to an empty string
ISBN_METADATA_FETCH_ORDER = ['Goodreads', 'Google', 'Amazon.com', 'ISBNDB', 'WorldCat xISBN', 'OZON.ru']

# Logging options
# ===============
LOGGING_FORMATTER = 'only_msg'
LOGGING_LEVEL = 'info'

# OCR options
# ===========
OCR_ENABLED = 'false'
OCR_COMMAND = 'tesseract_wrapper'
OCR_ONLY_FIRST_LAST_PAGES = (7, 3)

# Organize options
# ================
SKIP_ARCHIVES = False
CORRUPTION_CHECK = 'true'
ORGANIZE_WITHOUT_ISBN = False
ORGANIZE_WITHOUT_ISBN_SOURCES = ['Goodreads', 'Google', 'Amazon.com']
PAMPHLET_EXCLUDED_FILES = '\.(chm|epub|cbr|cbz|mobi|lit|pdb)$'
PAMPHLET_INCLUDED_FILES = '\.(png|jpg|jpeg|gif|bmp|svg|csv|pptx?)$'
PAMPHLET_MAX_FILESIZE_KIB = 250
PAMPHLET_MAX_PDF_PAGES = 50
TESTED_ARCHIVE_EXTENSIONS = '^(7z|bz2|chm|arj|cab|gz|tgz|gzip|zip|rar|xz|tar|epub|docx|odt|ods|cbr|cbz|maff|iso)$'
WITHOUT_ISBN_IGNORE = get_without_isbn_ignore()
OUTPUT_FILENAME_TEMPLATE = "${d[AUTHORS]// & /, } - ${d[SERIES]:+[${d[SERIES]}] " \
                           "- }${d[TITLE]/:/ -}${d[PUBLISHED]:+ (${d[PUBLISHED]%%-*})}" \
                           "${d[ISBN]:+ [${d[ISBN]}]}.${d[EXT]}"
OUTPUT_FOLDER_CORRUPT = None
OUTPUT_FOLDER_PAMPHLETS = None
OUTPUT_FOLDER_UNCERTAIN = None
# If `keep_metadata` is enabled, this is the extension of the additional
# metadata file that is saved next to each newly renamed file
OUTPUT_METADATA_EXTENSION = 'meta'


class Result:
    def __init__(self, stdout='', stderr='', returncode=None, args=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.args = args

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'stdout={str(self.stdout).strip()}, ' \
               f'stderr={str(self.stderr).strip()}, ' \
               f'returncode={self.returncode}, args={self.args}'


# ------
# Colors
# ------
COLORS = {
    'GREEN': '\033[0;36m',  # 32
    'RED': '\033[0;31m',
    'YELLOW': '\033[0;33m',  # 32
    'BLUE': '\033[0;34m',  #
    'VIOLET': '\033[0;35m',  #
    'BOLD': '\033[1m',
    'NC': '\033[0m',
}
_COLOR_TO_CODE = {
    'g': COLORS['GREEN'],
    'r': COLORS['RED'],
    'y': COLORS['YELLOW'],
    'b': COLORS['BLUE'],
    'v': COLORS['VIOLET'],
    'bold': COLORS['BOLD']
}


def color(msg, msg_color='y', bold_msg=False):
    msg_color = msg_color.lower()
    colors = list(_COLOR_TO_CODE.keys())
    assert msg_color in colors, f'Wrong color: {msg_color}. Only these ' \
                                f'colors are supported: {msg_color}'
    msg = bold(msg) if bold_msg else msg
    msg = msg.replace(COLORS['NC'], COLORS['NC']+_COLOR_TO_CODE[msg_color])
    return f"{_COLOR_TO_CODE[msg_color]}{msg}{COLORS['NC']}"


def blue(msg):
    return color(msg, 'b')


def bold(msg):
    return color(msg, 'bold')


def green(msg):
    return color(msg, 'g')


def red(msg):
    return color(msg, 'r')


def violet(msg):
    return color(msg, 'v')


def yellow(msg):
    return color(msg)


def catdoc(input_file, output_file):
    cmd = f'catdoc "{input_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Everything on the stdout must be copied to the output file
    if result.returncode == 0:
        with open(output_file, 'w') as f:
            f.write(result.stdout)
    return convert_result_from_shell_cmd(result)


# Checks the supplied file for different kinds of corruption:
#  - If it's zero-sized or contains only \0
#  - If it has a pdf extension but different mime type
#  - If it's a pdf and `pdfinfo` returns an error
#  - If it has an archive extension but `7z t` returns an error
# ref.: https://bit.ly/2JLpqgf
def check_file_for_corruption(
        file_path, tested_archive_extensions=TESTED_ARCHIVE_EXTENSIONS):
    file_err = ''
    logger.debug(f"Testing '{Path(file_path).name}' for corruption...")
    logger.debug(f"Full path: {file_path}")

    # TODO: test that it is the same as
    # if [[ "$(tr -d '\0' < "$file_path" | head -c 1)" == "" ]]; then
    # Ref.: https://bit.ly/2jpX0xf
    if is_file_empty(file_path):
        file_err = 'The file is empty or contains only zeros!'
        logger.debug(file_err)
        return file_err

    ext = Path(file_path).suffix[1:]  # Remove the dot from extension
    mime_type = get_mime_type(file_path)

    if mime_type == 'application/octet-stream' and \
            re.match('^(pdf|djv|djvu)$', mime_type):
        file_err = f"The file has a {ext} extension but '{mime_type}' MIME type!"
        logger.debug(file_err)
        return file_err
    elif mime_type == 'application/pdf':
        logger.debug('Checking pdf file for integrity...')
        if not command_exists('pdfinfo'):
            file_err = 'pdfinfo does not exist, could not check if pdf is OK'
            logger.debug(file_err)
            return file_err
        else:
            pdfinfo_output = pdfinfo(file_path)
            if pdfinfo_output.stderr:
                logger.debug('pdfinfo returned an error!')
                logger.debug(f'Error:\n{pdfinfo_output.stderr}')
                file_err = 'Has pdf MIME type or extension, but pdfinfo ' \
                           'returned an error!'
                logger.debug(file_err)
                return file_err
            else:
                logger.debug('pdfinfo returned successfully')
                logger.debug(f'Output of pdfinfo:\n{pdfinfo_output.stdout}')
                if re.search('^Page size:\s*0 x 0 pts$', pdfinfo_output.stdout):
                    logger.debug('pdf is corrupt anyway, page size property is '
                                 'empty!')
                    file_err = 'pdf can be parsed, but page size is 0 x 0 pts!'
                    logger.debug(file_err)
                    return file_err

    if re.match(tested_archive_extensions, ext):
        logger.debug(f"The file has a '{ext}' extension, testing with 7z...")
        log = test_archive(file_path)
        if log.stderr:
            logger.debug('Test failed!')
            logger.debug(log.stderr)
            file_err = 'Looks like an archive, but testing it with 7z failed!'
            return file_err
        else:
            logger.debug('Test succeeded!')
            logger.debug(log.stdout)

    if file_err == '':
        logger.debug('Corruption not detected!')
    else:
        logger.debug(f'We are at the end of the function and '
                     f'file_err="{file_err}"; it should be empty!')
    return file_err


# Ref.: https://stackoverflow.com/a/28909933
def command_exists(cmd):
    return shutil.which(cmd) is not None


def convert_bytes_binary(num, unit):
    """
    this function will convert bytes to MiB.... GiB... etc
    Ref.: https://stackoverflow.com/a/39988702
    """
    unit = unit.lower()
    units = ['bytes', 'kib', 'mib', 'gib', 'tib']
    if unit not in units:
        """
        logger.error(f"'{unit}' is not a valid unit\n"
                     f'Aborting {convert_bytes_binary.__name__}()')
        """
        return None
    for x in units:
        if num < 1024.0 or x == unit:
            # return "%3.1f %s" % (num, x)
            x = x.capitalize()
            if x != 'Bytes':
                x = x[:-1] + x[-1].upper()
            return num, "%3.1f %s" % (num, x)
        num /= 1024.0


def convert_bytes_decimal(num, unit):
    """
    this function will convert bytes to MB.... GB... etc
    Ref.: https://stackoverflow.com/a/39988702
    """
    unit = unit.lower()
    units = ['bytes', 'kb', 'mb', 'gb', 'tb']
    if unit not in units:
        """
        logger.error(f"'{unit}' is not a valid unit\n"
                     f'Aborting {convert_bytes_decimal.__name__}()')
        """
        return None
    for x in units:
        if num < 1000.0 or x == unit:
            # return "%3.1f %s" % (num, x)
            return num, "%3.1f %s" % (num, x)
        num /= 1000.0


def convert_result_from_shell_cmd(old_result):
    new_result = Result()

    for attr_name, new_val in new_result.__dict__.items():
        old_val = getattr(old_result, attr_name)
        if old_val is None:
            shell_args = getattr(old_result, 'args', None)
            # logger.debug(f'result.{attr_name} is None. Shell args: {shell_args}')
        else:
            if isinstance(new_val, str):
                try:
                    new_val = old_val.decode('UTF-8')
                except (AttributeError, UnicodeDecodeError) as e:
                    if type(e) == UnicodeDecodeError:
                        # old_val = b'...'
                        new_val = old_val.decode('unicode_escape')
                    else:
                        # `old_val` already a string
                        # logger.debug('Error decoding old value: {}'.format(old_val))
                        # logger.debug(e.__repr__())
                        # logger.debug('Value already a string. No decoding necessary')
                        new_val = old_val
                try:
                    new_val = ast.literal_eval(new_val)
                except (SyntaxError, ValueError) as e:
                    # NOTE: ValueError might happen if value consists of [A-Za-z]
                    # logger.debug('Error evaluating the value: {}'.format(old_val))
                    # logger.debug(e.__repr__())
                    # logger.debug('Aborting evaluation of string. Will consider
                    # the string as it is')
                    pass
            else:
                new_val = old_val
        setattr(new_result, attr_name, new_val)
    return new_result


# Tries to convert the supplied ebook file into .txt. It uses calibre's
# ebook-convert tool. For optimization, if present, it will use pdftotext
# for pdfs, catdoc for word files and djvutxt for djvu files.
# Ref.: https://bit.ly/2HXdf2I
def convert_to_txt(input_file, output_file, mime_type,
                   djvu_convert_method=DJVU_CONVERT_METHOD,
                   epub_convert_method=EPUB_CONVERT_METHOD,
                   msword_convert_method=MSWORD_CONVERT_METHOD,
                   pdf_convert_method=PDF_CONVERT_METHOD, **kwargs):
    if mime_type.startswith('image/vnd.djvu') \
         and djvu_convert_method == 'djvutxt' and command_exists('djvutxt'):
        logger.debug('The file looks like a djvu, using djvutxt to extract the text')
        result = djvutxt(input_file, output_file)
    elif mime_type.startswith('application/epub+zip') \
            and epub_convert_method == 'epubtxt' and command_exists('unzip'):
        logger.debug('The file looks like an epub, using epubtxt to extract the text')
        result = epubtxt(input_file, output_file)
    elif mime_type == 'application/msword' \
            and msword_convert_method in ['catdoc', 'textutil'] \
            and (command_exists('catdoc') or command_exists('textutil')):
        msg = 'The file looks like a doc, using {} to extract the text'
        # TODO: select convert method as specified by user
        # e.g. if convert_method = 'textutil' and 'catdoc' exists,
        # 'catdoc' will be used
        if command_exists('catdoc'):
            logger.debug(msg.format('catdoc'))
            result = catdoc(input_file, output_file)
        else:
            logger.debug(msg.format('textutil'))
            result = textutil(input_file, output_file)
    elif mime_type == 'application/pdf' and pdf_convert_method == 'pdftotext' \
            and command_exists('pdftotext'):
        logger.debug('The file looks like a pdf, using pdftotext to extract the text')
        result = pdftotext(input_file, output_file)
    elif (not mime_type.startswith('image/vnd.djvu')) \
            and mime_type.startswith('image/'):
        msg = f'The file looks like a normal image ({mime_type}), skipping ' \
              f'ebook-convert usage: {input_file}'
        # logger.debug(msg)
        return convert_result_from_shell_cmd(Result(stderr=msg, returncode=1))
    else:
        logger.debug(f"Trying to use calibre's ebook-convert to convert the {mime_type} file to .txt")
        result = ebook_convert(input_file, output_file)
    return result


def djvutxt(input_file, output_file, pages=None):
    pages = f'--page={pages}' if pages else ''
    cmd = f'djvutxt "{input_file}" "{output_file}" {pages}'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def ebook_convert(input_file, output_file):
    cmd = f'ebook-convert "{input_file}" "{output_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def epubtxt(input_file, output_file):
    cmd = f'unzip -c "{input_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not result.stderr:
        text = str(result.stdout)
        with open(output_file, 'w') as f:
            f.write(text)
        result.stdout = text
    return convert_result_from_shell_cmd(result)


def extract_archive(input_file, output_file):
    cmd = f'7z x -o"{output_file}" "{input_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def fail_file(old_path, reason, new_path=None):
    # More info about printing in terminal with color:
    # https://stackoverflow.com/a/21786287
    old_path = get_parts_from_path(old_path)
    logger.error(red(f'ERR:\t{old_path[:150]}'))
    second_line = red(f'REASON:\t{reason}')
    if new_path:
        new_path = get_parts_from_path(new_path)
        logger.error(second_line)
        logger.error(red(f'TO:\t{new_path[:150]}\n'))
    else:
        logger.error(second_line + '\n')


# Uses Calibre's `fetch-ebook-metadata` CLI tool to download metadata from
# online sources. The first parameter is the comma-separated list of allowed
# plugins (e.g. 'Goodreads,Amazon.com,Google') and the second parameter is the
# remaining of the `fetch-ebook-metadata`'s options, e.g.
# options='--verbose --opf isbn=1234567890'
# Returns the ebook metadata as a string; if no metadata found, an empty string
# is returned
# Ref.: https://bit.ly/2HS0iXQ
def fetch_metadata(isbn_sources, options=''):
    args = f'fetch-ebook-metadata {options}'
    if isinstance(isbn_sources, str):
        isbn_sources = isbn_sources.split(',')
    for isbn_source in isbn_sources:
        args += f' --allowed-plugin={isbn_source} '
    # Remove trailing whitespace
    args = args.strip()
    logger.debug(f'Calling `{args}`')
    args = shlex.split(args)
    # NOTE: `stderr` contains the whole log from running the fetch-data query
    # from the specified online sources. Thus, `stderr` is a superset of
    # `stdout` which only contains the ebook metadata for those fields that
    # have the pattern '[a-zA-Z()]+ +: .*'
    # TODO: make sure that you are getting only the fields that match the pattern
    # '[a-zA-Z()]+ +: .*' since you are not using a regex on the result
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# Searches the input string for ISBN-like sequences and removes duplicates and
# finally validates them using is_isbn_valid() and returns them separated by
# `isbn_ret_separator`
# Ref.: https://bit.ly/2HyLoSQ
def find_isbns(input_str, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
               isbn_regex=ISBN_REGEX, isbn_ret_separator=ISBN_RET_SEPARATOR,
               **kwargs):
    isbns = []
    invalid_isbns = []
    duplicate_isbns = []
    check_more = True
    input_str_copy = copy(input_str)
    while True:
        # TODO: they are using grep -oP
        # Ref.: https://bit.ly/2HUbnIs
        # Remove spaces
        # input_str = input_str.replace(' ', '')
        matches = re.finditer(isbn_regex, input_str_copy)
        for i, match in enumerate(matches):
            match = match.group()
            # Remove everything except numbers [0-9], 'x', and 'X'
            # NOTE: equivalent to UNIX command `tr -c -d '0-9xX'`
            # TODO 1: they don't remove \n in their code
            # TODO 2: put the following in a function
            del_tab = string.printable[10:].replace('x', '').replace('X', '')
            tran_tab = str.maketrans('', '', del_tab)
            match = match.translate(tran_tab)
            # Only keep unique ISBNs
            if match not in isbns:
                # Validate ISBN
                if is_isbn_valid(match):
                    if re.match(isbn_blacklist_regex, match):
                        logger.debug(f'Wrong ISBN (blacklisted): {match}')
                    else:
                        logger.debug(f'Valid ISBN found: {match}')
                        isbns.append(match)
                else:
                    if match not in invalid_isbns:
                        logger.debug(f'Invalid ISBN found: {match}')
                        invalid_isbns.append(match)
            else:
                if match not in duplicate_isbns:
                    logger.debug(f'Non-unique ISBN found: {match}')
                    duplicate_isbns.append(match)
        if isbns or not check_more:
            break
        # NOTE: remove it since we are using a longer regex that covers many cases of dashes
        input_str_copy = input_str_copy.replace('–', '').replace('—', '').replace('-', '').replace('·', ''). \
            replace('.', '').replace(' ', '')
        input_str_no_newlines = input_str_copy.replace('\n', '')[:100]
        logger.debug('Trying to find ISBNs with modified input string (showing only first 100 characters): '
                     f'{input_str_no_newlines}')
        check_more = False
    if not isbns:
        input_str_no_newlines = input_str.replace('\n', '')[:100]
        # msg (next line) not used anymore
        # msg = f'"{input_str_no_newlines}"' if len(input_str_no_newlines) < 100 else ''
        logger.debug(f'No ISBN found in the input string (showing only first 100 characters): {input_str_no_newlines}')
    # NOTE: if isbns = [], it returns ''
    # ' - '.join([]) => ''
    return isbn_ret_separator.join(isbns)


def get_all_isbns_from_archive(
        file_path, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
        isbn_direct_files=ISBN_DIRECT_FILES,
        isbn_reorder_files=ISBN_DIRECT_FILES,
        isbn_ignored_files=ISBN_IGNORED_FILES, isbn_regex=ISBN_REGEX,
        isbn_ret_separator=ISBN_RET_SEPARATOR, ocr_command=OCR_COMMAND,
        ocr_enabled=OCR_ENABLED,
        ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES, **kwargs):
    func_params = locals().copy()
    func_params.pop('file_path')
    all_isbns = []
    tmpdir = tempfile.mkdtemp()
    logger.debug(f"Trying to decompress '{os.path.basename(file_path)}' and "
                 "recursively scan the contents")
    logger.debug(f"Decompressing '{file_path}' into tmp folder '{tmpdir}'")
    result = extract_archive(file_path, tmpdir)
    if result.stderr:
        logger.debug('Error extracting the file (probably not an archive)! '
                     'Removing tmp dir...')
        logger.debug(result.stderr)
        remove_tree(tmpdir)
        return ''
    logger.debug(f"Archive extracted successfully in '{tmpdir}', scanning "
                 f"contents recursively...")
    # TODO: Ref.: https://stackoverflow.com/a/2759553
    # TODO: ignore .DS_Store
    for path, dirs, files in os.walk(tmpdir, topdown=False):
        # TODO: they use flag options for sorting the directory contents
        # see https://github.com/na--/ebook-tools#miscellaneous-options [FILE_SORT_FLAGS]
        for file_to_check in files:
            # TODO: add debug_prefixer
            file_to_check = os.path.join(path, file_to_check)
            isbns = search_file_for_isbns(file_to_check, **func_params)
            if isbns:
                logger.debug(f"Found ISBNs\n{isbns}")
                # TODO: two prints, one for stderror and the other for stdout
                logger.debug(isbns.replace(isbn_ret_separator, '\n'))
                for isbn in isbns.split(isbn_ret_separator):
                    if isbn not in all_isbns:
                        all_isbns.append(isbn)
            logger.debug(f'Removing {file_to_check}...')
            remove_file(file_to_check)
        if len(os.listdir(path)) == 0 and path != tmpdir:
            os.rmdir(path)
        elif path == tmpdir:
            if len(os.listdir(tmpdir)) == 1 and '.DS_Store' in tmpdir:
                remove_file(os.path.join(tmpdir, '.DS_Store'))
    logger.debug(f"Removing temporary folder '{tmpdir}' (should be empty)...")
    if is_dir_empty(tmpdir):
        remove_tree(tmpdir)
    return isbn_ret_separator.join(all_isbns)


def get_ebook_metadata(file_path):
    # TODO: add `ebook-meta` in PATH
    cmd = f'ebook-meta "{file_path}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# NOTE: the original function was returning the file size in MB... GB... but it
# was actually returning the file in MiB... GiB... etc (dividing by 1024, not 1000)
# see the comment @ https://bit.ly/2HL5RnI
# TODO: call this function when computing file size here in lib.py
# TODO: unit can be given with binary prefix as {'bytes', 'KiB', 'MiB', 'GiB', TiB'}
# or decimal prefix as {'bytes', 'KB', 'MB', 'GB', TB'}
def get_file_size(file_path, unit):
    """
    This function will return the file size
    Ref.: https://stackoverflow.com/a/39988702
    """
    if os.path.isfile(file_path):
        file_info = os.stat(file_path)
        if unit[1] == 'i':
            return convert_bytes_binary(file_info.st_size, unit=unit)
        else:
            return convert_bytes_decimal(file_info.st_size, unit=unit)
    else:
        logger.error(f"'{file_path}' is not a file\nAborting get_file_size()")
        return None


# Using Python built-in module mimetypes
def get_mime_type(file_path):
    try:
        mime_type = mimetypes.guess_type(file_path)[0]
    except TypeError as e:
        logger.error(red(f"Couldn't get the mime type: {file_path}"))
        logger.exception(e)
        return ''
    return mime_type if mime_type else ''


# Return number of pages in a djvu document
def get_pages_in_djvu(file_path):
    cmd = f'djvused -e "n" "{file_path}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# Return number of pages in a pdf document
def get_pages_in_pdf(file_path, cmd='mdls'):
    assert cmd in ['mdls', 'pdfinfo']
    if command_exists(cmd) and cmd == 'mdls':
        cmd = f'mdls -raw -name kMDItemNumberOfPages "{file_path}"'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if '(null)' in str(result.stdout):
            return get_pages_in_pdf(file_path, cmd='pdfinfo')
    else:
        cmd = f'pdfinfo "{file_path}"'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if result.returncode == 0:
            result = convert_result_from_shell_cmd(result)
            result.stdout = int(re.findall('^Pages:\s+([0-9]+)',
                                           result.stdout,
                                           flags=re.MULTILINE)[0])
            return result
    return convert_result_from_shell_cmd(result)


def get_parts_from_path(path):
    path = Path(path)
    anchor = path.anchor
    if not anchor:
        anchor = '/'
    return f'{anchor}'.join(path.parts[-2:])


# Checks if directory is empty
# Ref.: https://stackoverflow.com/a/47363995
def is_dir_empty(path):
    return next(os.scandir(path), None) is None


# Ref.: https://stackoverflow.com/a/15924160
def is_file_empty(file_path):
    # TODO: test when file doesn't exist
    # TODO: see if the proposed solution @ https://stackoverflow.com/a/15924160
    # is equivalent to using try and catch the `OSError`
    try:
        return not os.path.getsize(file_path) > 0
    except OSError as e:
        logger.error(f'Error: {e.filename} - {e.strerror}.')
        return False


# Validates ISBN-10 and ISBN-13 numbers
# Ref.: https://bit.ly/2HO2lMD
def is_isbn_valid(isbn):
    # TODO: there is also a Python package for validating ISBNs (but dependency)
    # Remove whitespaces (space, tab, newline, and so on), '-', and capitalize all
    # characters (ISBNs can consist of numbers [0-9] and the letters [xX])
    isbn = ''.join(isbn.split())
    isbn = isbn.replace('-', '')
    isbn = isbn.upper()

    sum = 0
    # Case 1: ISBN-10
    if len(isbn) == 10:
        for i in range(len(isbn)):
            if i == 9 and isbn[i] == 'X':
                number = 10
            else:
                number = int(isbn[i])
            sum += (number * (10 - i))
        if sum % 11 == 0:
            return True
    # Case 2: ISBN-13
    elif len(isbn) == 13:
        if isbn[0:3] in ['978', '979']:
            for i in range(0, len(isbn), 2):
                sum += int(isbn[i])
            for i in range(1, len(isbn), 2):
                sum += (int(isbn[i])*3)
            if sum % 10 == 0:
                return True
    return False


def move(src, dst, clobber=True):
    # TODO: necessary?
    # Since path can be relative to the cwd
    # src = os.path.abspath(src)
    # filename = os.path.basename(src)
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        logger.debug(f'{dst.name}: file already exists')
        logger.debug(f"Destination folder path: {dst.parent}")
        if clobber:
            logger.debug(f'{dst.name}: overwriting the file')
            shutil.move(src, dst)
            logger.debug("File moved!")
        else:
            logger.debug(f'{dst.name}: cannot overwrite existing file')
            logger.debug(f"Skipping it!")
    else:
        logger.debug(f"Moving '{src.name}'...")
        logger.debug(f"Destination folder path: {dst.parent}")
        shutil.move(src, dst)
        logger.debug("File moved!")


# Ref.: https://bit.ly/2HxYEaw
def move_or_link_ebook_file_and_metadata(
        new_folder, current_ebook_path, current_metadata_path, dry_run=DRY_RUN,
        keep_metadata=KEEP_METADATA,
        output_filename_template=OUTPUT_FILENAME_TEMPLATE,
        output_metadata_extension=OUTPUT_METADATA_EXTENSION,
        symlink_only=SYMLINK_ONLY, **kwargs):
    # Get ebook's file extension
    ext = Path(current_ebook_path).suffix
    ext = ext[1:] if ext[0] == '.' else ext
    d = {'EXT': ext}

    # Extract fields from metadata file
    with open(current_metadata_path, 'r') as f:
        for line in f:
            # Get field name and value separately, e.g.
            # 'Title  : A nice ebook' ---> field_name = 'Title  ' and field_value = ' A nice ebook'
            # Find the first colon and split on its position
            pos = line.find(':')
            field_name, field_value = line[:pos], line[pos+1:]

            # TODO: try to use subprocess.run instead of subprocess.Popen and
            # creating two processes
            # OR try to do it without subprocess, only with Python regex

            # Process field name
            # TODO: converting characters to upper case with `-e 's/\(.*\)/\\U\1/'`
            # doesn't work on mac, \\U is not supported
            result = substitute_with_sed(regex='[ \t]*$', replacement='',
                                         text=field_name, use_global=False)
            result = substitute_with_sed(regex=' ', replacement='_', text=result)
            field_name = substitute_with_sed(regex='[^a-zA-Z0-9_]', replacement='', text=result).upper()

            # Process field value
            # Get only the first 100 characters
            d[field_name] = substitute_with_sed(
                regex='[\\/\*\?<>\|\x01-\x1F\x7F\x22\x24\x60]', replacement='_',
                text=field_value)[:100]

    logger.debug('Variables that will be used for the new filename construction:')
    for k, v in d.items():
        # TODO: important, encode('utf-8')? like in rename?
        logger.debug(f'{k}: {v}')

    new_name = substitute_params(d, output_filename_template)
    logger.debug(f"The new file name of the book file/link '{current_ebook_path}' "
                 f'will be: {new_name}')

    new_path = unique_filename(new_folder, new_name)
    logger.debug(f'Full path: {new_path}')
    move_or_link_file(current_ebook_path, new_path, dry_run, symlink_only)

    if keep_metadata:
        new_metadata_path = f'{new_path}.{output_metadata_extension}'
        logger.debug(f"Moving metadata file '{current_metadata_path}' to "
                     f"'{new_metadata_path}'....")
        if dry_run:
            logger.debug('Removing current metadata file: '
                         f'{current_metadata_path}')
            remove_file(current_metadata_path)
        else:
            if Path(new_metadata_path).is_file():
                logger.debug(f'File already exists: {new_metadata_path}')
            else:
                shutil.move(current_metadata_path, new_metadata_path)
    else:
        logger.debug(f'Removing metadata file {current_metadata_path}...')
        remove_file(current_metadata_path)
    return new_path


def move_or_link_file(current_path, new_path, dry_run=DRY_RUN,
                      symlink_only=SYMLINK_ONLY):
    new_folder = Path(new_path).parent
    if dry_run:
        logger.debug('DRY RUN! No file rename/move/symlink/etc. operations '
                     'will actually be executed')

    # Create folder
    if not new_folder.exists():
        logger.debug(f'Creating folder {new_folder}')
        if not dry_run:
            new_folder.mkdir()

    # Symlink or move file
    if symlink_only:
        logger.debug(f"Symlinking file '{current_path}' to '{new_path}'...")
        if not dry_run:
            Path(new_path).symlink_to(current_path)
    else:
        logger.debug(f"Moving file '{current_path}' to '{new_path}'...")
        if not dry_run:
            move(current_path, new_path, clobber=False)


def namespace_to_dict(ns):
    namspace_classes = [Namespace, SimpleNamespace]
    # TODO: check why not working anymore
    # if isinstance(ns, SimpleNamespace):
    if type(ns) in namspace_classes:
        adict = vars(ns)
    else:
        adict = ns
    for k, v in adict.items():
        # if isinstance(v, SimpleNamespace):
        if type(v) in namspace_classes:
            v = vars(v)
            adict[k] = v
        if isinstance(v, dict):
            namespace_to_dict(v)
    return adict


# OCR on a pdf, djvu document or image
# NOTE: If pdf or djvu document, then first needs to be converted to image and then OCR
def ocr_file(file_path, output_file, mime_type,
             ocr_command=OCR_COMMAND,
             ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES, **kwargs):
    # Convert pdf to png image
    def convert_pdf_page(page, input_file, output_file):
        cmd = f'gs -dSAFER -q -r300 -dFirstPage={page} -dLastPage={page} ' \
              '-dNOPAUSE -dINTERPOLATE -sDEVICE=png16m ' \
              f'-sOutputFile="{output_file}" "{input_file}" -c quit'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return convert_result_from_shell_cmd(result)

    # Convert djvu to tif image
    def convert_djvu_page(page, input_file, output_file):
        cmd = f'ddjvu -page={page} -format=tif "{input_file}" "{output_file}"'
        args = shlex.split(cmd)
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return convert_result_from_shell_cmd(result)

    if mime_type.startswith('application/pdf'):
        result = get_pages_in_pdf(file_path)
        num_pages = result.stdout
        logger.debug(f"Result of '{get_pages_in_pdf.__name__}()' on '{file_path}':\n{result}")
        page_convert_cmd = convert_pdf_page
    elif mime_type.startswith('image/vnd.djvu'):
        result = get_pages_in_djvu(file_path)
        num_pages = result.stdout
        logger.debug(f"Result of '{get_pages_in_djvu.__name__}()' on '{file_path}':\n{result}")
        page_convert_cmd = convert_djvu_page
    elif mime_type.startswith('image/'):
        logger.debug(f"Running OCR on file '{file_path}' and with mime type '{mime_type}'...")
        if ocr_command in globals():
            result = eval(f'{ocr_command}("{file_path}", "{output_file}")')
            logger.debug(f"Result of '{ocr_command}':\n{result}")
            return 0
        else:
            msg = red("Function '{ocr_command}' doesn't exit.")
            logger.error(f'{msg}')
            return 1
    else:
        logger.error(f"{red('Unsupported mime type')} '{mime_type}'!")
        return 1

    if result.returncode == 1:
        err_msg = result.stdout if result.stdout else result.stderr
        msg = "Couldn't get number of pages:"
        logger.error(f"{red(msg)} '{str(err_msg).strip()}'")
        return 1

    if ocr_command not in globals():
        msg = red("Function '{ocr_command}' doesn't exit.")
        logger.error(f'{msg}')
        return 1

    logger.debug(f"The file '{file_path}' has {num_pages} page{'s' if num_pages > 1 else ''}")
    logger.debug(f'mime type: {mime_type}')

    # Pre-compute the list of pages to process based on ocr_only_first_last_pages
    if ocr_only_first_last_pages:
        ocr_first_pages = int(ocr_only_first_last_pages[0])
        ocr_last_pages = int(ocr_only_first_last_pages[1])
        pages_to_process = [i for i in range(1, ocr_first_pages + 1)]
        pages_to_process.extend([i for i in range(num_pages + 1 - ocr_last_pages, num_pages + 1)])
    else:
        # ocr_only_first_last_pages is False
        logger.debug('ocr_only_first_last_pages is False')
        logger.warning(f"{yellow('OCR will be applied to all ({pages}) pages of the document')}")
        pages_to_process = [i for i in range(1, num_pages+1)]
    logger.debug(f'Pages to process: {pages_to_process}')

    text = ''
    for i, page in enumerate(pages_to_process, start=1):
        logger.debug(f'Processing page {i} of {len(pages_to_process)}')
        # Make temporary files
        tmp_file = tempfile.mkstemp()[1]
        tmp_file_txt = tempfile.mkstemp(suffix='.txt')[1]
        logger.debug(f'Running OCR of page {page}...')
        logger.debug(f'Using tmp files {tmp_file} and {tmp_file_txt}')
        # doc(pdf, djvu) --> image(png, tiff)
        result = page_convert_cmd(page, file_path, tmp_file)
        if result.returncode == 0:
            logger.debug(f"Result of {page_convert_cmd.__name__}():\n{result}")
            # image --> text
            logger.debug(f"Running the '{ocr_command}'...")
            result = eval(f'{ocr_command}("{tmp_file}", "{tmp_file_txt}")')
            if result.returncode == 0:
                logger.debug(f"Result of '{ocr_command}':\n{result}")
                with open(tmp_file_txt, 'r') as f:
                    data = f.read()
                    # logger.debug(f"Text content of page {page}:\n{data}")
                text += data
            else:
                msg = red(f"Image couldn't be converted to text: {result}")
                logger.error(f'{msg}')
                logger.error(f'Skipping current page ({page})')
        else:
            msg = red(f"Document couldn't be converted to image: {result}")
            logger.error(f'{msg}')
            logger.error(f'Skipping current page ({page})')
        # Remove temporary files
        logger.debug('Cleaning up tmp files')
        remove_file(tmp_file)
        remove_file(tmp_file_txt)
    # Everything on the stdout must be copied to the output file
    logger.debug('Saving the text content')
    with open(output_file, 'w') as f:
        f.write(text)
    return 0


def ok_file(old_path, new_path):
    old_path = get_parts_from_path(old_path)
    new_path = get_parts_from_path(new_path)
    logger.info(green(f'OK:\t{old_path[:150]}\nTO:\t{new_path[:150]}\n'))


def pdfinfo(file_path):
    cmd = 'pdfinfo "{}"'.format(file_path)
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def pdftotext(input_file, output_file, first_page_to_convert=None, last_page_to_convert=None):
    first_page = f'-f {first_page_to_convert}' if first_page_to_convert else ''
    last_page = f'-l {last_page_to_convert}' if last_page_to_convert else ''
    pages = f'{first_page} {last_page}'.strip()
    cmd = f'pdftotext "{input_file}" "{output_file}" {pages}'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


def remove_file(file_path):
    # Ref.: https://stackoverflow.com/a/42641792
    try:
        os.remove(file_path)
        return 0
    except OSError as e:
        logger.error(red(f'{e.filename} - {e.strerror}.'))
        return 1


# Recursively delete a directory tree, including the parent directory
# Ref.: https://stackoverflow.com/a/186236
def remove_tree(file_path):
    try:
        shutil.rmtree(file_path)
        return 0
    except Exception as e:
        logger.error(f'Error: {e.filename} - {e.strerror}.')
        return 1


# If `isbn_reorder_files` is enabled, reorders the specified file
# according to the values of `isbn_rf_scan_first` and
# `isbn_rf_reverse_last`
# Ref.: https://bit.ly/2JuaEKw
# TODO: order params and other places
def reorder_file_content(
        file_path,
        isbn_reorder_files=ISBN_REORDER_FILES, **kwargs):
    if isbn_reorder_files:
        isbn_rf_scan_first = isbn_reorder_files[0]
        isbn_rf_reverse_last = isbn_reorder_files[1]
        logger.debug('Reordering input file (if possible), read first '
                     f'{isbn_rf_scan_first} lines normally, then read '
                     f'last {isbn_rf_reverse_last} lines in reverse and '
                     'then read the rest')
        # TODO: try out with big file, more than 800 pages (approx. 73k lines)
        # TODO: see alternatives for reading big file @
        # https://stackoverflow.com/a/4999741 (mmap),
        # https://stackoverflow.com/a/24809292 (linecache),
        # https://stackoverflow.com/a/42733235 (buffer)
        # Problem: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa9 in position 1475: invalid start byte
        # Solution: encoding="utf8", errors='ignore'
        with open(file_path, 'r', encoding="utf8", errors='ignore') as f:
            # Read whole file as a list of lines
            # TODO: do we remove newlines? e.g. with f.read().rstrip("\n")
            data = f.readlines()
            # Read the first ISBN_GREP_RF_SCAN_FIRST lines of the file text
            first_part = data[:isbn_rf_scan_first]
            del data[:isbn_rf_scan_first]
            # Read the last part and reverse it
            last_part = data[-isbn_rf_reverse_last:]
            if last_part:
                last_part.reverse()
                del data[-isbn_rf_reverse_last:]
            # Read the middle part of the file text
            middle_part = data
            # TODO: try out with large lists, if efficiency is a concern then
            # check itertools.chain
            # ref.: https://stackoverflow.com/a/4344735
            # Concatenate the three parts: first, last part (reversed), and
            # middle part
            data = first_part + last_part + middle_part
            data = "".join(data)
    else:
        logger.debug('Since `isbn_reorder_file`s is False, input file will '
                     'not be reordered')
        with open(file_path, 'r') as f:
            # TODO: do we remove newlines? e.g. with f.read().rstrip("\n")
            # Read whole content of file as a string
            data = f.read()
    data = repr(data).replace('\\uf73', '')
    return data


# Tries to find ISBN numbers in the given ebook file by using progressively
# more "expensive" tactics.
# These are the steps:
# 1. Check the supplied file name for ISBNs (the path is ignored)
# 2. If the MIME type of the file matches `isbn_direct_files`, search the
#    file contents directly for ISBNs
# 3. If the MIME type matches `isbn_ignored_files`, the function returns early
#    with no results
# 4. Check the file metadata from calibre's `ebook-meta` for ISBNs
# 5. Try to extract the file as an archive with `7z`; if successful,
#    recursively call search_file_for_isbns for all the extracted files
# 6. If the file is not an archive, try to convert it to a .txt file
#    via convert_to_txt()
# 7. If OCR is enabled and convert_to_txt() fails or its result is empty,
#    try OCR-ing the file. If the result is non-empty but does not contain
#    ISBNs and OCR_ENABLED is set to "always", run OCR as well.
# Ref.: https://bit.ly/2r28US2
def search_file_for_isbns(
        file_path, isbn_blacklist_regex=ISBN_BLACKLIST_REGEX,
        isbn_direct_files=ISBN_DIRECT_FILES,
        isbn_reorder_files=ISBN_REORDER_FILES,
        isbn_ignored_files=ISBN_IGNORED_FILES, isbn_regex=ISBN_REGEX,
        isbn_ret_separator=ISBN_RET_SEPARATOR, ocr_command=OCR_COMMAND,
        djvu_convert_method=DJVU_CONVERT_METHOD,
        epub_convert_method=EPUB_CONVERT_METHOD,
        pdf_convert_method=PDF_CONVERT_METHOD,
        ocr_enabled=OCR_ENABLED,
        ocr_only_first_last_pages=OCR_ONLY_FIRST_LAST_PAGES, **kwargs):
    func_params = locals().copy()
    # NOTE: pop('file_path'), the convert_to_txt() has file_path as first parameter
    func_params.pop('file_path')
    basename = os.path.basename(file_path)
    logger.debug(f"Searching file '{basename[:100]}' for ISBN numbers...")
    # Step 1: check the filename for ISBNs
    # TODO: make sure that we return an empty string when we can't find ISBNs
    logger.debug('check the filename for ISBNs')
    isbns = find_isbns(basename, **func_params)
    if isbns:
        logger.debug("Extracted ISBNs '{}' from the file name!".format(
            isbns.replace('\n', '; ')))
        return isbns

    # Steps 2-3: (2) if valid MIME type, search file contents for ISBNs and
    # (3) if invalid MIME type, exit without results
    mime_type = get_mime_type(file_path)
    if mime_type and re.match(isbn_direct_files, mime_type):
        logger.debug('Ebook is in text format, trying to find ISBN directly')
        data = reorder_file_content(file_path, **func_params)
        isbns = find_isbns(data, **func_params)
        if isbns:
            logger.debug(f"Extracted ISBNs from the text file contents:\n{isbns}")
        else:
            logger.debug('Did not find any ISBNs')
        return isbns
    elif mime_type and re.match(isbn_ignored_files, mime_type):
        logger.debug('The file type is in the blacklist, ignoring...')
        return isbns

    # Step 4: check the file metadata from calibre's `ebook-meta` for ISBNs
    logger.debug("check the file metadata from calibre's `ebook-meta` for ISBNs")
    if command_exists('ebook-meta'):
        ebookmeta = get_ebook_metadata(file_path)
        logger.debug(f'Ebook metadata:\n{ebookmeta.stdout}')
        isbns = find_isbns(ebookmeta.stdout, **func_params)
        if isbns:
            logger.debug(f"Extracted ISBNs from calibre ebook metadata:\n{isbns}'")
            return isbns
    else:
        logger.debug("`ebook-meta` is not found!")

    # Step 5: decompress with 7z
    logger.debug('decompress with 7z')
    if not mime_type.startswith('application/epub+zip'):
        isbns = get_all_isbns_from_archive(file_path, **func_params)
        if isbns:
            logger.debug(f"Extracted ISBNs from the archive file:\n{isbns}")
            return isbns

    # Step 6: convert file to .txt
    try_ocr = False
    tmp_file_txt = tempfile.mkstemp(suffix='.txt')[1]
    logger.debug(f"Converting ebook to text format...")
    logger.debug(f"Temp file: {tmp_file_txt}")

    # NOTE: important, takes a long time for pdfs (not djvu)
    result = convert_to_txt(file_path, tmp_file_txt, mime_type, **func_params)
    if result.returncode == 0:
        logger.debug('Conversion to text was successful, checking the result...')
        # Problem: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa9 in position 1475: invalid start byte
        # Solution: encoding="utf8", errors='ignore'
        with open(tmp_file_txt, 'r', encoding="utf8", errors='ignore') as f:
            data = f.read()
        if not re.search('[A-Za-z0-9]+', data):
            logger.debug('The converted txt with size '
                         f'{os.stat(tmp_file_txt).st_size} bytes does not seem '
                         'to contain text')
            logger.debug(f'First 1000 characters:\n{data[:1000].strip()}')
            try_ocr = True
        else:
            data = reorder_file_content(tmp_file_txt, **func_params)
            # ipdb.set_trace()
            isbns = find_isbns(data, **func_params)
            if isbns:
                logger.debug(f"Text output contains ISBNs:\n{isbns}")
            elif ocr_enabled == 'always':
                logger.debug('We will try OCR because the successfully converted '
                             'text did not have any ISBNs')
                try_ocr = True
            else:
                logger.debug('Did not find any ISBNs and will NOT try OCR')
    else:
        logger.error(red('There was an error converting the ebook to txt format:'))
        logger.error(red(result.stderr))
        try_ocr = True

    # Step 7: OCR the file
    if not isbns and ocr_enabled != 'false' and try_ocr:
        logger.debug('Trying to run OCR on the file...')
        if ocr_file(file_path, tmp_file_txt, mime_type, **func_params) == 0:
            logger.debug('OCR was successful, checking the result...')
            data = reorder_file_content(tmp_file_txt, **func_params)
            # ipdb.set_trace()
            isbns = find_isbns(data, **func_params)
            if isbns:
                logger.debug(f"Text output contains ISBNs {isbns}!")
            else:
                logger.debug('Did not find any ISBNs in the OCR output')
        else:
            # TODO: show error!
            logger.info('There was an error while running OCR!')

    logger.debug(f"Removing tmp file '{tmp_file_txt}'...")
    remove_file(tmp_file_txt)

    if isbns:
        logger.debug(f"Returning the found ISBNs:\n{isbns}")
    else:
        logger.debug(f'Could not find any ISBNs in {file_path} :(')

    return isbns


# Returns a single value by key by parsing the calibre-style text metadata
# hashmap that is passed as argument
# Ref.: https://bit.ly/2rIUHZM
def search_meta_val(ebookmeta, key):
    val = None
    lines = ebookmeta.splitlines()
    for line in lines:
        if line.startswith(key):
            return line.split(':')[-1].strip()
    return val


def setup_log(quiet=False, verbose=False, logging_level=LOGGING_LEVEL,
              logging_formatter=LOGGING_FORMATTER, logger_names=None):
    if logger_names is None:
        logger_names = ['script', 'lib']
    max_width = 0
    for name in logger_names:
        max_width = max(max_width, len(name))
    if not quiet:
        for logger_name in logger_names:
            logger_ = logging.getLogger(logger_name)
            if verbose:
                logger_.setLevel('DEBUG')
            else:
                logging_level = logging_level.upper()
                logger_.setLevel(logging_level)
            # Create console handler and set level
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            # Create formatter
            if logging_formatter:
                formatters = {
                    'console': f'%(name)-{max_width}s | %(levelname)-8s | %(message)s',
                    # 'console': '%(asctime)s | %(levelname)-8s | %(message)s',
                    'only_msg': '%(message)s',
                    'simple': '%(levelname)-8s %(message)s',
                    'verbose': '%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s'
                }
                formatter = logging.Formatter(formatters[logging_formatter])
                # Add formatter to ch
                ch.setFormatter(formatter)
            # Add ch to logger
            logger_.addHandler(ch)
        # =============
        # Start logging
        # =============
        logger.debug("Running {} v{}".format(__file__, __version__))
        logger.debug("Verbose option {}".format("enabled" if verbose else "disabled"))


def skip_file(old_path, new_path):
    # TODO: https://bit.ly/2rf38f5
    old_path = get_parts_from_path(old_path)
    new_path = get_parts_from_path(new_path)
    logger.warning(yellow(f"SKIP:\t{old_path[:150]}"))
    logger.warning(yellow(f'REASON:\t{new_path[:150]}\n'))


def substitute_params(hashmap, output_filename_template=OUTPUT_FILENAME_TEMPLATE):
    array = ''
    for k, v in hashmap.items():
        if not k:
            continue
        if isinstance(v, bytes):
            v = v.decode('UTF-8')
        # logger.debug(f'{hashmap[k]}')
        array += ' ["{}"]="{}" '.format(k, v)

    cmd = 'declare -A d=( {} )'  # debug: `echo "${d[TITLE]}"`
    cmd = cmd.format(array)
    # TODO: make it safer; maybe by removing single/double quotes marks from
    # OUTPUT_FILENAME_TEMPLATE
    # TODO: explain what's going on
    cmd += f'; OUTPUT_FILENAME_TEMPLATE=\'"{output_filename_template}"\'; ' \
           'eval echo "$OUTPUT_FILENAME_TEMPLATE"'
    # In the Docker container (Ubuntu), no '/usr/local/bin/bash' (macOS), only '/bin/bash'
    # TODO: important, once tested on Ubuntu, remove next line
    # bin_path = bash_path if Path(bash_path).exists() else '/bin/bash'
    result = subprocess.Popen([shutil.which('bash'), '-c', cmd], stdout=subprocess.PIPE)
    return result.stdout.read().decode('UTF-8').strip()


# TODO: important, use re.sub
def substitute_with_sed(regex, replacement, text, use_global=True):
    # Remove trailing whitespace, including tab
    text = text.strip()
    p1 = subprocess.Popen(['echo', text], stdout=subprocess.PIPE)
    # TODO: explain what's going on with this replacement code
    cmd = f"sed -e 's/{regex}/{replacement}/'"
    if use_global:
        cmd += 'g'
    args = shlex.split(cmd)
    p2 = subprocess.Popen(args, stdin=p1.stdout, stdout=subprocess.PIPE)
    return p2.communicate()[0].decode('UTF-8').strip()


# OCR: convert image to text
def tesseract_wrapper(input_file, output_file):
    cmd = f'tesseract "{input_file}" stdout --psm 12'
    args = shlex.split(cmd)
    result = subprocess.run(args,
                            stdout=open(output_file, 'w'),
                            stderr=subprocess.PIPE,
                            encoding='utf-8',
                            bufsize=4096)
    return convert_result_from_shell_cmd(result)


def test_archive(file_path):
    cmd = '7z t "{}"'.format(file_path)
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# macOS equivalent for catdoc
# See https://stackoverflow.com/a/44003923/14664104
def textutil(input_file, output_file):
    cmd = f'textutil -convert txt "{input_file}" -output "{output_file}"'
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return convert_result_from_shell_cmd(result)


# Return "folder_path/basename" if no file exists at this path. Otherwise,
# sequentially insert " ($n)" before the extension of `basename` and return the
# first path for which no file is present.
# ref.: https://bit.ly/3n1JNuk
def unique_filename(folder_path, basename):
    stem = Path(basename).stem
    ext = Path(basename).suffix
    new_path = Path(Path(folder_path).joinpath(basename))
    counter = 0
    while new_path.is_file():
        counter += 1
        logger.debug(f"File '{new_path.name}' already exists in destination "
                     f"'{folder_path}', trying with counter {counter}!")
        new_stem = f'{stem} {counter}'
        new_path = Path(Path(folder_path).joinpath(new_stem + ext))
    return new_path.as_posix()


class OrganizeEbooks:
    def __init__(self):
        # ===============
        # General options
        # ===============
        self.dry_run = DRY_RUN
        self.symlink_only = SYMLINK_ONLY
        self.keep_metadata = KEEP_METADATA
        self.reverse = REVERSE
        # ======================
        # Convert-to-txt options
        # ======================
        self.djvu_convert_method = DJVU_CONVERT_METHOD
        self.epub_convert_method = EPUB_CONVERT_METHOD
        self.msword_convert_method = MSWORD_CONVERT_METHOD
        self.pdf_convert_method = PDF_CONVERT_METHOD
        # ===========================================================================
        # Options related to extracting ISBNS from files and finding metadata by ISBN
        # ===========================================================================
        self.max_isbns = MAX_ISBNS
        self.isbn_regex = ISBN_REGEX
        self.isbn_blacklist_regex = ISBN_BLACKLIST_REGEX
        self.isbn_direct_files = ISBN_DIRECT_FILES
        self.isbn_ignored_files = ISBN_IGNORED_FILES
        self.isbn_reorder_files = ISBN_REORDER_FILES
        self.isbn_ret_separator = ISBN_RET_SEPARATOR
        self.isbn_metadata_fetch_order = ISBN_METADATA_FETCH_ORDER
        # ===========
        # OCR options
        # ===========
        self.ocr_enabled = OCR_ENABLED
        self.ocr_only_first_last_pages = OCR_ONLY_FIRST_LAST_PAGES
        self.ocr_command = OCR_COMMAND
        # ================
        # Organize options
        # ================
        self.skip_archives = SKIP_ARCHIVES
        self.corruption_check = CORRUPTION_CHECK
        self.tested_archive_extensions = TESTED_ARCHIVE_EXTENSIONS
        self.organize_without_isbn = ORGANIZE_WITHOUT_ISBN
        self.organize_without_isbn_sources = ORGANIZE_WITHOUT_ISBN_SOURCES
        self.without_isbn_ignore = WITHOUT_ISBN_IGNORE
        self.pamphlet_included_files = PAMPHLET_INCLUDED_FILES
        self.pamphlet_excluded_files = PAMPHLET_EXCLUDED_FILES
        self.pamphlet_max_pdf_pages = PAMPHLET_MAX_PDF_PAGES
        self.pamphlet_max_filesize_kib = PAMPHLET_MAX_FILESIZE_KIB
        # ====================
        # Input/Output options
        # ====================
        self.folder_to_organize = None
        self.output_folder = os.getcwd()
        self.output_folder_uncertain = OUTPUT_FOLDER_UNCERTAIN
        self.output_folder_corrupt = OUTPUT_FOLDER_CORRUPT
        self.output_folder_pamphlets = OUTPUT_FOLDER_PAMPHLETS
        self.output_filename_template = OUTPUT_FILENAME_TEMPLATE
        self.output_metadata_extension = OUTPUT_METADATA_EXTENSION

    def _is_pamphlet(self, file_path):
        logger.debug(f"Checking whether '{file_path}' looks like a pamphlet...")
        # TODO: check that it does the same as to_lower() @ https://bit.ly/2w0O5LN
        lowercase_name = os.path.basename(file_path).lower()
        # TODO: check that it does the same as
        # `if [[ "$lowercase_name" =~ $PAMPHLET_INCLUDED_FILES ]];`
        # Ref.: https://bit.ly/2I5nvFW
        if re.search(self.pamphlet_included_files, lowercase_name):
            parts = []
            # TODO: check that it does the same as
            # `matches="[$(echo "$lowercase_name" |
            # grep -oE "$PAMPHLET_INCLUDED_FILES" | paste -sd';')]"`
            # TODO: they are using grep -oE
            # Ref.: https://bit.ly/2w2PeCo
            matches = re.finditer(self.pamphlet_included_files, lowercase_name)
            for i, match in enumerate(matches):
                parts.append(match.group())
            matches = ';'.join(parts)
            logger.debug('Parts of the filename match the pamphlet include '
                         f'regex: [{matches}]')
            return True
        logger.debug('The file does not match the pamphlet include regex, '
                     'continuing...')
        # TODO: check that it does the same as
        # `if [[ "$lowercase_name" =~ $PAMPHLET_EXCLUDED_FILES ]]; then`
        # Ref.: https://bit.ly/2KscBZj
        if re.search(self.pamphlet_excluded_files, lowercase_name):
            parts = []
            # TODO: check that it does the same as
            # `matches="[$(echo "$lowercase_name" | grep -oE "$PAMPHLET_EXCLUDED_FILES" | paste -sd';')]"`
            # NOTE: they are using grep -oE
            # Ref.: https://bit.ly/2JHhlZJ
            matches = re.finditer(self.pamphlet_excluded_files, lowercase_name)
            for i, match in enumerate(matches):
                parts.append(match.group())
            matches = ';'.join(parts)
            logger.debug('Parts of the filename match the pamphlet ignore '
                         f'regex: [{matches}]')
            return False
        logger.debug('The file does not match the pamphlet exclude regex, '
                     'continuing...')
        mime_type = get_mime_type(file_path)
        file_size_KiB, _ = get_file_size(file_path, unit='KiB')
        if file_size_KiB is None:
            logger.error(f'Could not get the file size (KiB) for {file_path}')
            return None
        if mime_type == 'application/pdf':
            logger.debug('The file looks like a pdf, checking if the number of '
                         f'pages is larger than {self.pamphlet_max_pdf_pages}...')
            result = get_pages_in_pdf(file_path)
            pages = result.stdout
            if pages is None:
                logger.error(f'Could not get the number of pages for {file_path}')
                return None
            elif pages > self.pamphlet_max_pdf_pages:
                logger.debug(f'The file has {pages} pages, too many for a '
                             'pamphlet')
                return False
            else:
                logger.debug(f'The file has only {pages} pages, looks like a '
                             'pamphlet')
                return True
        elif file_size_KiB < self.pamphlet_max_filesize_kib:
            logger.debug(f"The file has a type '{mime_type}' and a small size "
                         f'({file_size_KiB} KiB), looks like a pamphlet')
            return True
        else:
            logger.debug(f"The file has a type '{mime_type}' and a large size "
                         f'({file_size_KiB} KB), does NOT look like a pamphlet')
            return False

    def _organize_by_filename_and_meta(self, old_path, prev_reason):
        # TODO: important, return nothing?
        prev_reason = f'{prev_reason}; '
        logger.debug(f"Organizing '{old_path}' by non-ISBN metadata and "
                     "filename...")
        # TODO: check that it does the same as to_lower() @ https://bit.ly/2w0O5LN
        lowercase_name = os.path.basename(old_path).lower()
        # TODO: check that it does the same as
        # `if [[ "$WITHOUT_ISBN_IGNORE" != "" &&
        # "$lowercase_name" =~ $WITHOUT_ISBN_IGNORE ]]`
        # Ref.: https://bit.ly/2HJTzfg
        if self.without_isbn_ignore and re.match(self.without_isbn_ignore,
                                                 lowercase_name):
            parts = []
            # TODO: check that it does the same as
            # `matches="[$(echo "$lowercase_name" |
            # grep -oE "$WITHOUT_ISBN_IGNORE" | paste -sd';')]`
            # NOTE: they are using grep -oE
            # Ref.: https://bit.ly/2jj2Vnz
            matches = re.finditer(self.without_isbn_ignore, lowercase_name)
            for i, match in enumerate(matches):
                parts.append(match.group())
            matches = ';'.join(parts)
            logger.debug('Parts of the filename match the ignore regex: '
                         f'[{matches}]')
            skip_file(old_path,
                      f'{prev_reason}File matches the ignore regex ({matches})')
            return
        else:
            logger.debug('File does not match the ignore regex, continuing...')
        is_p = self._is_pamphlet(file_path=old_path)
        if is_p is True:
            logger.debug(f"File '{old_path}' looks like a pamphlet!")
            if self.output_folder_pamphlets:
                new_path = unique_filename(self.output_folder_pamphlets,
                                           os.path.basename(old_path))
                logger.debug(f"Moving file '{old_path}' to '{new_path}'!")
                ok_file(old_path, new_path)
                move_or_link_file(old_path, new_path, self.dry_run, self.symlink_only)
            else:
                logger.debug('Output folder for pamphlet files is not set, '
                             'skipping...')
                skip_file(old_path, 'No pamphlet folder specified')
            return
        elif is_p is False:
            logger.debug(f"File '{old_path}' doesn't look like a pamphlet")
        else:
            logger.debug(f"Couldn't determine if file '{old_path}' is a pamphlet")
        if not self.output_folder_uncertain:
            # logger.debug('No uncertain folder specified, skipping...')
            skip_file(old_path, 'No uncertain folder specified')
            return
        result = get_ebook_metadata(old_path)
        if result.stderr:
            logger.error(f'`ebook-meta` returns an error: {result.stderr}')
        ebookmeta = result.stdout
        logger.debug('Ebook metadata:')
        logger.debug(ebookmeta)
        tmpmfile = tempfile.mkstemp(suffix='.txt')[1]
        logger.debug(f'Created temporary file for metadata downloads {tmpmfile}')

        # NOTE: tmp file is removed in move_or_link_ebook_file_and_metadata()
        def finisher(fetch_method, ebookmeta, metadata):
            logger.debug('Successfully fetched metadata: ')
            logger.debug('Adding additional metadata to the end of the metadata '
                         'file...')
            more_metadata = '\nOld file path       : {}\n' \
                            'Meta fetch method   : {}\n'.format(old_path,
                                                                fetch_method)
            lines = []
            for line in ebookmeta.splitlines():
                # TODO: remove next line if simpler version does the same thing
                # lines.append(re.sub('^(.+[^ ]) ([ ]+):', 'OF \1 \2', line))
                lines.append(re.sub(r'^(.+):', r'OF \1:', line))
            ebookmeta = '\n'.join(lines)
            with open(tmpmfile, 'a') as f:
                f.write(more_metadata)
                f.write(ebookmeta)
            isbns = find_isbns(metadata + ebookmeta, **self.__dict__)
            if isbns:
                # TODO: important, there can be more than one isbn
                isbn = isbns.split(self.isbn_ret_separator)[0]
                with open(tmpmfile, 'a') as f:
                    f.write(f'\nISBN                : {isbn}')
            else:
                logger.debug(f'No isbn found for file {old_path}')
            logger.debug(f"Organizing '{old_path}' (with '{tmpmfile}')...")
            new_path = move_or_link_ebook_file_and_metadata(
                new_folder=self.output_folder_uncertain,
                current_ebook_path=old_path,
                current_metadata_path=tmpmfile, **self.__dict__)
            ok_file(old_path, new_path)

        title = search_meta_val(ebookmeta, 'Title')
        author = search_meta_val(ebookmeta, 'Author(s)')
        # Equivalent to (in bash):
        # if [[ "${title//[^[:alpha:]]/}" != "" && "$title" != "unknown" ]]
        # Ref.: https://bit.ly/2HDHZGm
        # Remove everything that is not a letters (lower or upper) and check the result
        if re.sub(r'[^A-Za-z]', '', title) != '' and title != 'unknown':
            logger.debug('There is a relatively normal-looking title, '
                         'searching for metadata...')
            if re.sub(r'\s', '', author) != '' and author != 'unknown':
                logger.debug(f'Trying to fetch metadata by title "{title}" '
                             f'and author "{author}"...')
                options = f'--verbose --title="{title}" --author="{author}"'
                # TODO: check that fetch_metadata() can also return an empty string
                metadata = fetch_metadata(self.organize_without_isbn_sources,
                                          options)
                if metadata.returncode == 0:
                    # TODO: they are writing outside the if, https://bit.ly/2FyIiwh
                    with open(tmpmfile, 'a') as f:
                        # TODO: do we write even if metadata can be empty?
                        # TODO: important, stdout (only one 1 result) or stderr (all results)
                        f.write(metadata.stdout)
                    finisher('title&author', ebookmeta, metadata.stdout)
                    return
                logger.debug(f"Trying to swap places - author '{title}' and "
                             f"title '{author}'...")
                options = f'--verbose --title="{author}" --author="{title}"'
                metadata = fetch_metadata(self.organize_without_isbn_sources,
                                          options)
                if metadata.returncode == 0:
                    # NOTE: they are writing outside the if, https://bit.ly/2Kt78kX
                    with open(tmpmfile, 'a') as f:
                        # TODO: do we write even if metadata can be empty?
                        f.write(metadata.stdout)
                    finisher('rev-title&author', ebookmeta, metadata.stdout)
                    return
                logger.debug(f'Trying to fetch metadata only by title {title}...')
                options = f'--verbose --title="{title}"'
                metadata = fetch_metadata(self.organize_without_isbn_sources,
                                          options)
                if metadata.returncode == 0:
                    # NOTE: they are writing outside the if, https://bit.ly/2vZeFES
                    with open(tmpmfile, 'a') as f:
                        # TODO: do we write even if metadata can be empty?
                        f.write(metadata.stdout)
                    finisher('title', ebookmeta, metadata.stdout)
                    return
        # TODO: tokenize basename
        # filename="$(basename "${old_path%.*}" | tokenize)"
        # Ref.: https://bit.ly/2jlyBIR
        filename = os.path.splitext(os.path.basename(old_path))[0]
        logger.debug(f'Trying to fetch metadata only by filename {filename}...')
        options = f'--verbose --title="{filename}"'
        metadata = fetch_metadata(self.organize_without_isbn_sources, options)
        if metadata.returncode == 0:
            # TODO: they are writing outside the if, https://bit.ly/2I3GH6X
            with open(tmpmfile, 'a') as f:
                # TODO: do we write even if metadata can be empty?
                f.write(filename)
            finisher('title', ebookmeta, filename)
            return
        logger.debug('Could not find anything, removing the temp file '
                     f'{tmpmfile}...')
        remove_file(tmpmfile)
        skip_file(old_path, f'{prev_reason}Insufficient or wrong: 1) filename or 2) metadata')

    def _organize_by_isbns(self, file_path, isbns):
        # TODO: important, returns nothing?
        isbn_sources = self.isbn_metadata_fetch_order
        if not isbn_sources:
            # NOTE: If you use Calibre versions that are older than 2.84, it's
            # required to manually set the following option to an empty string.
            isbn_sources = []
        for i, isbn in enumerate(isbns.split(self.isbn_ret_separator), start=1):
            if i > self.max_isbns:
                logger.debug(f"Only testing the first {self.max_isbns} ISBNs")
                break
            tmp_file = tempfile.mkstemp(suffix='.txt')[1]
            logger.debug(f"Trying to fetch metadata for ISBN '{isbn}' into "
                         f"temp file '{tmp_file}'...")

            # IMPORTANT: as soon as we find metadata from one source, we return
            for isbn_source in isbn_sources:
                # Remove whitespaces around the isbn source
                isbn_source = isbn_source.strip()
                # Check if there are spaces in the arguments, and if it is the
                # case enclose the arguments in quotation marks
                # e.g. WorldCat xISBN --> "WorldCat xISBN"
                if ' ' in isbn_source:
                    isbn_source = f'"{isbn_source}"'
                logger.debug(f"Fetching metadata from '{isbn_source}' sources...")
                options = f'--verbose --isbn={isbn}'
                result = fetch_metadata(isbn_source, options)
                metadata = result.stdout
                if metadata:
                    with open(tmp_file, 'w') as f:
                        f.write(metadata)

                    # NOTE: is it necessary to sleep after fetching the
                    # metadata from online sources like they do? The rest of the
                    # code here is executed once fetch_metadata() is done
                    # Ref.: https://bit.ly/2vV9MfU
                    time.sleep(0.1)
                    logger.debug('Successfully fetched metadata')
                    logger.debug(f'Fetched metadata:{metadata}')

                    logger.debug('Adding additional metadata to the end of the '
                                 'metadata file...')
                    more_metadata = 'ISBN                : {}\n' \
                                    'All found ISBNs     : {}\n' \
                                    'Old file path       : {}\n' \
                                    'Metadata source     : {}'.format(
                        isbn, isbns.replace('\n', ','), file_path, isbn_source)
                    logger.debug(more_metadata)
                    with open(tmp_file, 'a') as f:
                        f.write(more_metadata)

                    logger.debug(f"Organizing '{file_path}' (with {tmp_file})...")
                    new_path = move_or_link_ebook_file_and_metadata(
                        new_folder=self.output_folder,
                        current_ebook_path=file_path,
                        current_metadata_path=tmp_file, **self.__dict__)

                    ok_file(file_path, new_path)
                    # NOTE: `tmp_file` was already removed in
                    # move_or_link_ebook_file_and_metadata()
                    return

            logger.debug(f'Removing temp file {tmp_file}...')
            remove_file(tmp_file)

        isbns = isbns.replace('\n', ' - ')
        if self.organize_without_isbn:
            logger.debug('Could not organize via the found ISBNs, organizing '
                         'by filename and metadata instead...')
            self._organize_by_filename_and_meta(
                old_path=file_path,
                prev_reason=f"Could not fetch metadata for ISBNs: {isbns}")
        else:
            logger.debug('Organization by filename and metadata is not turned '
                         'on, giving up...')
            skip_file(file_path, f'Could not fetch metadata for ISBNs: {isbns}; '
                                 f'Non-ISBN organization disabled')

    def _organize_file(self, file_path):
        suffix = f' [{Path(file_path).suffix}] ' if len(Path(file_path).name) > 100 else ' '
        fp = normalize("NFKC", str(file_path))
        logger.info(f'Processing{suffix}{fp[:100]}...')
        ext = Path(file_path).suffix[1:]  # Remove the dot from extension
        if self.skip_archives and ext != 'epub' and re.match(self.tested_archive_extensions, ext):
            logger.debug(f"The file has a '{ext}' extension, skipping it since it is an archive!")
            skip_file(file_path, 'File is an archive!')
            return 0
        if self.corruption_check != 'false':
            file_err = check_file_for_corruption(file_path,
                                                 self.tested_archive_extensions)
        else:
            file_err = None
            logger.debug('Skipping corruption check')
        if file_err:
            logger.debug(f"File '{file_path}' is corrupt with error: {file_err}")
            if self.output_folder_corrupt:
                new_path = unique_filename(self.output_folder_corrupt,
                                           file_path.name)
                move_or_link_file(file_path, new_path, self.dry_run,
                                  self.symlink_only)
                # NOTE: do we add the meta extension directly to new_path (which
                # already has an extension); thus if new_path='/test/path/book.pdf'
                # then new_metadata_path='/test/path/book.pdf.meta' or should it be
                # new_metadata_path='/test/path/book.meta'
                # Ref.: https://bit.ly/2I6K3pW
                """
                new_metadata_path = f'{os.path.splitext(new_path)[0]}.' \
                                    f'{self.output_metadata_extension}'
                """
                # NOTE: no unique name for matadata path (and other places)
                new_metadata_path = f'{new_path}.{self.output_metadata_extension}'
                logger.debug(f'Saving original filename to {new_metadata_path}...')
                if not self.dry_run:
                    metadata = f'Corruption reason   : {file_err}\n' \
                               f'Old file path       : {file_path}'
                    with open(new_metadata_path, 'w') as f:
                        f.write(metadata)
                fail_file(file_path, f'File is corrupt: {file_err}', new_path)
            else:
                logger.debug('Output folder for corrupt files is not set, doing '
                             'nothing')
                fail_file(file_path, f'File is corrupt: {file_err}')
        elif self.corruption_check == 'check_only':
            logger.debug('We are only checking for corruption, do not continue '
                         'organising...')
            skip_file(file_path, 'File appears OK')
        else:
            # NOTE: important, if html has ISBN it will be considered as an ebook
            # self._is_pamphlet() needs to be called before search...()
            if self.corruption_check == 'true':
                logger.debug('File passed the corruption test, looking for ISBNs...')
            else:
                logger.debug('Looking for ISBNs...')
            isbns = search_file_for_isbns(file_path, **self.__dict__)
            if isbns:
                logger.debug(f"Organizing '{file_path}' by ISBNs\n{isbns}")
                self._organize_by_isbns(file_path, isbns)
            elif self.organize_without_isbn:
                logger.debug(f"No ISBNs found for '{file_path}', organizing by "
                             'filename and metadata...')
                self._organize_by_filename_and_meta(
                    old_path=file_path, prev_reason='No ISBNs found')
            else:
                skip_file(file_path,
                          'No ISBNs found; Non-ISBN organization disabled')
        logger.debug('=====================================================')
        return 0

    def _update(self, **kwargs):
        logger.debug('Updating attributes for organizer...')
        if self.output_folder != os.getcwd():
            logger.debug(f'output_folder: {os.getcwd()} [cwd] -> {self.output_folder}')
        for k, v in self.__dict__.items():
            new_val = kwargs.get(k)
            if new_val and v != new_val:
                logger.debug(f'{k}: {v} -> {new_val}')
                self.__setattr__(k, new_val)

    def _check_folders(self):
        folders = [self.folder_to_organize, self.output_folder, self.output_folder_uncertain,
                   self.output_folder_corrupt, self.output_folder_pamphlets]
        for folder in folders:
            if folder and not Path(folder).exists():
                logger.error(red(f"Folder doesn't exist: {folder}"))
                return 1
        return 0

    def organize(self, folder_to_organize, output_folder=os.getcwd(), **kwargs):
        if folder_to_organize is None:
            logger.error(red("\nerror: the following arguments are required: folder_to_organize"))
            return 1
        self.folder_to_organize = folder_to_organize
        self.output_folder = output_folder
        self._update(**kwargs)
        if self._check_folders():
            return 1
        files = []
        if is_dir_empty(folder_to_organize):
            logger.warning(yellow(f'Folder is empty: {folder_to_organize}'))
        if self.corruption_check == 'check_only':
            logger.info('We are only checking for corruption\n')
        logger.debug(f"Recursively scanning '{folder_to_organize}' for files...")
        for fp in Path(folder_to_organize).rglob('*'):
            # Ignore directory and hidden files
            if Path.is_file(fp) and not fp.name.startswith('.'):
                # logger.debug(f"{fp.name}")
                files.append(fp)
        if not files:
            logger.warning(yellow(f'No ebooks found in folder: {folder_to_organize}'))
        logger.debug("Files sorted {}".format("in desc" if self.reverse else "in asc"))
        files.sort(key=lambda x: x.name, reverse=self.reverse)
        logger.debug('=====================================================')
        for fp in files:
            # NOTE: not a good idea because then it can't find the file because its filename has been normalized
            # e.g. Control №290-> Control No290 [FileNotFoundError]
            # fp = normalize("NFKC", str(fp))
            self._organize_file(Path(fp))
        return 0


# TODO: fix accents
organizer = OrganizeEbooks()
