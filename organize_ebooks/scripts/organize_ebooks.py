"""
The script organize_ebooks.py automatically organizes folders with potentially
huge amounts of unorganized ebooks.

This is a Python port of `organize-ebooks.sh` from `ebook-tools` written in shell
by `na--`.

Ref.: https://github.com/na--/ebook-tools
"""
import argparse
import codecs
import logging
import os

from organize_ebooks import __version__, lib
from organize_ebooks.lib import namespace_to_dict, organizer, setup_log, blue, green, red, yellow

# import ipdb

logger = logging.getLogger('organize_script')
logger.setLevel(logging.CRITICAL + 1)

# =====================
# Default config values
# =====================

# Misc options
# ============
QUIET = False
OUTPUT_FILE = 'output.txt'


class ArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        print_(self.format_usage().splitlines()[0])
        self.exit(2, red(f'\nerror: {message}\n'))


class MyFormatter(argparse.HelpFormatter):
    """
    Corrected _max_action_length for the indenting of subactions
    """

    def add_argument(self, action):
        if action.help is not argparse.SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            current_indent = self._current_indent
            for subaction in self._iter_indented_subactions(action):
                # compensate for the indent that will be added
                indent_chg = self._current_indent - current_indent
                added_indent = 'x' * indent_chg
                invocations.append(added_indent + get_invocation(subaction))
            # print_('inv', invocations)

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    # Ref.: https://stackoverflow.com/a/23941599/14664104
    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            # change to
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    # parts.append('%s %s' % (option_string, args_string))
                    parts.append('%s' % option_string)
                parts[-1] += ' %s'%args_string
            return ', '.join(parts)


class OptionsChecker:
    def __init__(self, add_opts, remove_opts):
        self.add_opts = init_list(add_opts)
        self.remove_opts = init_list(remove_opts)

    def check(self, opt_name):
        return not self.remove_opts.count(opt_name) or \
               self.add_opts.count(opt_name)


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


# General options
def add_general_options(parser, add_opts=None, remove_opts=None,
                        program_version=__version__,
                        title='General options'):
    checker = OptionsChecker(add_opts, remove_opts)
    parser_general_group = parser.add_argument_group(title=title)
    if checker.check('help'):
        parser_general_group.add_argument('-h', '--help', action='help',
                                          help='Show this help message and exit.')
    if checker.check('version'):
        parser_general_group.add_argument(
            '-v', '--version', action='version',
            version=f'%(prog)s v{program_version}',
            help="Show program's version number and exit.")
    if checker.check('quiet'):
        parser_general_group.add_argument(
            '-q', '--quiet', action='store_true',
            help='Enable quiet mode, i.e. nothing will be printed.')
    if checker.check('verbose'):
        parser_general_group.add_argument(
            '--verbose', action='store_true',
            help='Print various debugging information, e.g. print traceback '
                 'when there is an exception.')
    if checker.check('dry-run'):
        parser_general_group.add_argument(
            '-d', '--dry-run', dest='dry_run', action='store_true',
            help='If this is enabled, no file rename/move/symlink/etc. '
                 'operations will actually be executed.')
    if checker.check('symlink-only'):
        parser_general_group.add_argument(
            '-s', '--symlink-only', dest='symlink_only', action='store_true',
            help='Instead of moving the ebook files, create symbolic links to '
                 'them.')
    if checker.check('keep-metadata'):
        parser_general_group.add_argument(
            '-k', '--keep-metadata', dest='keep_metadata', action='store_true',
            help='Do not delete the gathered metadata for the organized ebooks, '
                 'instead save it in an accompanying file together with each '
                 'renamed book. It is very useful for semi-automatic '
                 'verification of the organized files for additional verification, '
                 'indexing or processing at a later date.')
    # TODO: implement more sort options, e.g. random sort
    if checker.check('reverse'):
        parser_general_group.add_argument(
            '-r', '--reverse', dest='reverse', action='store_true',
            help='If this is enabled, the files will be sorted in reverse (i.e. '
                 'descending) order. By default, they are sorted in ascending '
                 'order.')
    if checker.check('log-level'):
        parser_general_group.add_argument(
            '--log-level', dest='logging_level',
            choices=['debug', 'info', 'warning', 'error'], default=lib.LOGGING_LEVEL,
            help='Set logging level.' + get_default_message(lib.LOGGING_LEVEL))
    if checker.check('log-format'):
        parser_general_group.add_argument(
            '--log-format', dest='logging_formatter',
            choices=['console', 'only_msg', 'simple',], default=lib.LOGGING_FORMATTER,
            help='Set logging formatter.' + get_default_message(lib.LOGGING_FORMATTER))
    return parser_general_group


# Ref.: https://stackoverflow.com/a/5187097/14664104
def decode(value):
    return codecs.decode(value, 'unicode_escape')


def get_default_message(default_value):
    return green(f' (default: {default_value})')


def init_list(list_):
    return [] if list_ is None else list_


def print_(msg):
    global QUIET
    if not QUIET:
        print(msg)


# Ref.: https://stackoverflow.com/a/4195302/14664104
def required_length(nmin, nmax, is_list=True):
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if isinstance(values, str):
                tmp_values = [values]
            else:
                tmp_values = values
            if not nmin <= len(tmp_values) <= nmax:
                if nmin == nmax:
                    msg = 'argument "{f}" requires {nmin} arguments'.format(
                        f=self.dest, nmin=nmin, nmax=nmax)
                else:
                    msg = 'argument "{f}" requires between {nmin} and {nmax} ' \
                          'arguments'.format(f=self.dest, nmin=nmin, nmax=nmax)
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)
    return RequiredLength


def setup_argparser():
    width = os.get_terminal_size().columns - 5
    name_input = 'folder_to_organize'
    usage_msg = blue(f'%(prog)s [OPTIONS] {{{name_input}}}')
    desc_msg = 'Automatically organize folders with potentially huge amounts of ' \
               'unorganized ebooks.\nThis is done by renaming the files with ' \
               'proper names and moving them to other folders.''.\n\n' \
               'This script is based on the great ebook-tools written in shell ' \
               'by na-- (See https://github.com/na--/ebook-tools).'
    parser = ArgumentParser(
        description="",
        usage=f"{usage_msg}\n\n{desc_msg}",
        add_help=False,
        formatter_class=lambda prog: MyFormatter(
            prog, max_help_position=50, width=width))
    general_group = add_general_options(
        parser,
        remove_opts=[],
        program_version=__version__,
        title=yellow('General options'))
    # ======================
    # Convert-to-txt options
    # ======================
    convert_group = parser.add_argument_group(title=yellow('Convert-to-txt options'))
    convert_group.add_argument(
        '--djvu', dest='djvu_convert_method',
        choices=['djvutxt', 'ebook-convert'], default=lib.DJVU_CONVERT_METHOD,
        help='Set the conversion method for djvu documents.'
             + get_default_message(lib.DJVU_CONVERT_METHOD))
    convert_group.add_argument(
        '--epub', dest='epub_convert_method',
        choices=['epubtxt', 'ebook-convert'], default=lib.EPUB_CONVERT_METHOD,
        help='Set the conversion method for epub documents.'
             + get_default_message(lib.EPUB_CONVERT_METHOD))
    convert_group.add_argument(
        '--msword', dest='msword_convert_method',
        choices=['catdoc', 'textutil', 'ebook-convert'], default=lib.MSWORD_CONVERT_METHOD,
        help='Set the conversion method for epub documents.'
             + get_default_message(lib.MSWORD_CONVERT_METHOD))
    convert_group.add_argument(
        '--pdf', dest='pdf_convert_method',
        choices=['pdftotext', 'ebook-convert'], default=lib.PDF_CONVERT_METHOD,
        help='Set the conversion method for pdf documents.'
             + get_default_message(lib.PDF_CONVERT_METHOD))
    # ===========================================================================
    # Options related to extracting ISBNS from files and finding metadata by ISBN
    # ===========================================================================
    find_group = parser.add_argument_group(
        title=yellow('Options related to extracting ISBNS from files and finding metadata by ISBN'))
    # TODO: add look-ahead and look-behind info, see https://bit.ly/2OYsY76
    find_group.add_argument(
        "-i", "--isbn-regex", dest='isbn_regex', default=lib.ISBN_REGEX,
        help='''This is the regular expression used to match ISBN-like
            numbers in the supplied books.''' + get_default_message(lib.ISBN_REGEX))
    find_group.add_argument(
        "--isbn-blacklist-regex", dest='isbn_blacklist_regex', metavar='REGEX',
        default=lib.ISBN_BLACKLIST_REGEX,
        help='''Any ISBNs that were matched by the ISBN_REGEX above and pass
            the ISBN validation algorithm are normalized and passed through this
            regular expression. Any ISBNs that successfully match against it are
            discarded. The idea is to ignore technically valid but probably wrong
            numbers like 0123456789, 0000000000, 1111111111, etc..'''
             + get_default_message(lib.ISBN_BLACKLIST_REGEX))
    find_group.add_argument(
        "--isbn-direct-files", dest='isbn_direct_files',
        metavar='REGEX', default=lib.ISBN_DIRECT_FILES,
        help='''This is a regular expression that is matched against the MIME
            type of the searched files. Matching files are searched directly for
            ISBNs, without converting or OCR-ing them to .txt first.'''
             + get_default_message(lib.ISBN_DIRECT_FILES))
    find_group.add_argument(
        "--isbn-ignored-files", dest='isbn_ignored_files', metavar='REGEX',
        default=lib.ISBN_IGNORED_FILES,
        help='''This is a regular expression that is matched against the MIME
            type of the searched files. Matching files are not searched for ISBNs
            beyond their filename. By default, it tries to ignore .gif and .svg
            images, audio, video and executable files and fonts.'''
             + get_default_message(lib.ISBN_IGNORED_FILES))
    find_group.add_argument(
        "--reorder-files", dest='isbn_reorder_files', nargs='+',
        action=required_length(1, 2), metavar='LINES', default=lib.ISBN_REORDER_FILES,
        help='''These options specify if and how we should reorder the ebook
            text before searching for ISBNs in it. By default, the first 400 lines
            of the text are searched as they are, then the last 50 are searched in
            reverse and finally the remainder in the middle. This reordering is
            done to improve the odds that the first found ISBNs in a book text
            actually belong to that book (ex. from the copyright section or the
            back cover), instead of being random ISBNs mentioned in the middle of
            the book. No part of the text is searched twice, even if these regions
            overlap. Set it to `False` to disable the functionality or
            `first_lines last_lines` to enable it with the specified values.'''
             + get_default_message(str(lib.ISBN_REORDER_FILES).strip('[|]').replace(',', '')))
    find_group.add_argument(
        '--irs', '--isbn-return-separator', dest='isbn_ret_separator',
        metavar='SEPARATOR', type=decode, default=lib.ISBN_RET_SEPARATOR,
        help='''This specifies the separator that will be used when returning
                any found ISBNs.''' +
             get_default_message(repr(codecs.encode(lib.ISBN_RET_SEPARATOR).decode('utf-8'))))
    find_group.add_argument(
        "-m", "---metadata-fetch-order", nargs='+',
        dest='isbn_metadata_fetch_order', metavar='METADATA_SOURCE',
        help='''This option allows you to specify the online metadata
                sources and order in which the subcommands will try searching in
                them for books by their ISBN. The actual search is done by
                calibre's `fetch-ebook-metadata` command-line application, so any
                custom calibre metadata plugins can also be used. To see the
                currently available options, run `fetch-ebook-metadata --help` and
                check the description for the `--allowed-plugin` option. If you use
                Calibre versions that are older than 2.84, it's required to
                manually set this option to an empty string.'''
             + get_default_message(lib.ISBN_METADATA_FETCH_ORDER))
    # ===========
    # OCR options
    # ===========
    ocr_group = parser.add_argument_group(title=yellow('OCR options'))
    ocr_group.add_argument(
        "--ocr", "--ocr-enabled", dest='ocr_enabled',
        choices=['always', 'true', 'false'], default=lib.OCR_ENABLED,
        help='Whether to enable OCR for .pdf, .djvu and image files. It is '
             'disabled by default.' + get_default_message(lib.OCR_ENABLED))
    ocr_group.add_argument(
        "--ocrop", "--ocr-only-first-last-pages",
        dest='ocr_only_first_last_pages', metavar='PAGES', nargs=2,
        default=lib.OCR_ONLY_FIRST_LAST_PAGES,
        help='''Value 'n m' instructs the script to convert only the
             first n and last m pages when OCR-ing ebooks.'''
             + get_default_message(str(lib.OCR_ONLY_FIRST_LAST_PAGES).strip('(|)').replace(',', '')))
    # ================
    # Organize options
    # ================
    organize_group = parser.add_argument_group(title=yellow('Organize options'))
    organize_group.add_argument(
        "-c", "--corruption-check-only", dest='corruption_check_only',
        action="store_true",
        help='Do not organize or rename files, just check them for corruption '
             '(ex. zero-filled files, corrupt archives or broken .pdf files). '
             'Useful with the `output-folder-corrupt` option.')
    organize_group.add_argument(
        "-t", '--tested-archive-extensions', dest='tested_archive_extensions',
        metavar='REGEX', default=lib.TESTED_ARCHIVE_EXTENSIONS,
        help='A regular expression that specifies which file extensions will '
             'be tested with `7z t` for corruption.'
             + get_default_message(lib.TESTED_ARCHIVE_EXTENSIONS))
    organize_group.add_argument(
        '--owi', '--organize-without-isbn', dest='organize_without_isbn',
        action="store_true",
        help='Specify whether the script will try to organize ebooks if there '
             'were no ISBN found in the book or if no metadata was found '
             'online with the retrieved ISBNs. If enabled, the script will '
             'first try to use calibre\'s `ebook-meta` command-line tool to '
             'extract the author and title metadata from the ebook file. The '
             'script will try searching the online metadata sources '
             '(`organize-without-isbn-sources`) by the extracted author & '
             'title and just by title. If there is no useful metadata or '
             'nothing is found online, the script will try to use the filename '
             'for searching.')
    organize_group.add_argument(
        '--owis', '--organize-without-isbn-sources', nargs='+',
        dest='organize_without_isbn_sources', metavar='METADATA_SOURCE',
        default=lib.ORGANIZE_WITHOUT_ISBN_SOURCES,
        help='''This option allows you to specify the online metadata sources
            in which the script will try searching for books by non-ISBN
            metadata (i.e. author and title). The actual search is done by
            calibre's `fetch-ebook-metadata` command-line application, so any
            custom calibre metadata plugins can also be used. To see the currently
            available options, run `fetch-ebook-metadata --help` and check the
            description for the `--allowed-plugin` option. Because Calibre versions
            older than 2.84 don't support the `--allowed-plugin` option, if you
            want to use such an old Calibre version you should manually set
            `organize_without_isbn_sources` to an empty string.'''
             + get_default_message(lib.ORGANIZE_WITHOUT_ISBN_SOURCES))
    organize_group.add_argument(
        '-w', '--without-isbn-ignore', dest='without_isbn_ignore',
        metavar='REGEX', default=lib.WITHOUT_ISBN_IGNORE,
        help='This is a regular expression that is matched against lowercase '
             'filenames. All files that do not contain ISBNs are matched '
             'against it and matching files are ignored by the script, even if '
             '`organize-without-isbn` is true. The default value is calibrated '
             'to match most periodicals (magazines, newspapers, etc.) so the '
             'script can ignore them.'
             + get_default_message('complex default value, see the README'))
    organize_group.add_argument(
        '--pamphlet-included-files', dest='pamphlet_included_files',
        metavar='REGEX', default=lib.PAMPHLET_INCLUDED_FILES,
        help='This is a regular expression that is matched against lowercase '
             'filenames. All files that do not contain ISBNs and do not match '
             '`without-isbn-ignore` are matched against it and matching files '
             'are considered pamphlets by default. They are moved to '
             '`output_folder_pamphlets` if set, otherwise they are ignored.'
             + get_default_message(lib.PAMPHLET_INCLUDED_FILES))
    organize_group.add_argument(
        '--pamphlet-excluded-files', dest='pamphlet_excluded_files',
        metavar='REGEX', default=lib.PAMPHLET_EXCLUDED_FILES,
        help='This is a regular expression that is matched against lowercase '
             'filenames. If files do not contain ISBNs and match against it, '
             'they are NOT considered as pamphlets, even if they have a small '
             'size or number of pages.'
             + get_default_message(lib.PAMPHLET_EXCLUDED_FILES))
    organize_group.add_argument(
        '--pamphlet-max-pdf-pages', dest='pamphlet_max_pdf_pages', type=int,
        metavar='PAGES', default=lib.PAMPHLET_MAX_PDF_PAGES,
        help='.pdf files that do not contain valid ISBNs and have a lower '
             'number pages than this are considered pamplets/non-ebook '
             'documents.' + get_default_message(lib.PAMPHLET_MAX_PDF_PAGES))
    organize_group.add_argument(
        '--pamphlet-max-filesize-kb', dest='pamphlet_max_filesize_kib', type=int,
        metavar='SIZE', default=lib.PAMPHLET_MAX_FILESIZE_KIB,
        help='Other files that do not contain valid ISBNs and are below this '
             'size in KBs are considered pamplets/non-ebook documents.'
             + get_default_message(lib.PAMPHLET_MAX_FILESIZE_KIB))
    # ====================
    # Input/Output options
    # ====================
    input_output_group = parser.add_argument_group(title=yellow('Input/Output options'))
    input_output_group.add_argument(
        name_input,
        help='Folder containing the ebook files that need to be organized.')
    input_output_group.add_argument(
        '-o', '--output-folder', dest='output_folder', metavar='PATH', default=os.getcwd(),
        help='The folder where ebooks that were renamed based on the ISBN '
             'metadata will be moved to.' + get_default_message(os.getcwd()))
    input_output_group.add_argument(
        '--ofu', '--output-folder-uncertain', dest='output_folder_uncertain',
        metavar='PATH', default=lib.OUTPUT_FOLDER_UNCERTAIN,
        help='If `organize-without-isbn` is enabled, this is the folder to '
             'which all ebooks that were renamed based on non-ISBN metadata '
             'will be moved to.' + get_default_message(lib.OUTPUT_FOLDER_UNCERTAIN))
    input_output_group.add_argument(
        '--ofc', '--output-folder-corrupt', dest='output_folder_corrupt',
        metavar='PATH', default=lib.OUTPUT_FOLDER_CORRUPT,
        help='If specified, corrupt files will be moved to this folder.'
             + get_default_message(lib.OUTPUT_FOLDER_CORRUPT))
    input_output_group.add_argument(
        '--ofp', '--output-folder-pamphlets', dest='output_folder_pamphlets',
        metavar='PATH', default=lib.OUTPUT_FOLDER_PAMPHLETS,
        help='If specified, pamphlets will be moved to this folder.'
             + get_default_message(lib.OUTPUT_FOLDER_PAMPHLETS))
    return parser


def show_exit_code(exit_code):
    msg = f'Program exited with {exit_code}'
    if exit_code == 1:
        logger.error(red(f'{msg}'))
    else:
        logger.debug(msg)


def main():
    global QUIET
    try:
        parser = setup_argparser()
        args = parser.parse_args()
        QUIET = args.quiet
        setup_log(args.quiet, args.verbose, args.logging_level, args.logging_formatter)
        # Actions
        error = False
        args_dict = namespace_to_dict(args)
        if len(args.isbn_reorder_files) == 1:
            if args.isbn_reorder_files[0] == 'False':
                args_dict['isbn_reorder_files'] = False
            else:
                logger.error(f"{red(f'error: invalid choice for reorder-files: ')}"
                             f"'{args.isbn_reorder_files[0]}' (choose from 'False' or two integers)")
                error = True
        else:
            args_dict['isbn_reorder_files'][0] = int(args_dict['isbn_reorder_files'][0])
            args_dict['isbn_reorder_files'][1] = int(args_dict['isbn_reorder_files'][1])
        if error:
            exit_code = 1
        else:
            exit_code = organizer.organize(**args_dict)
    except KeyboardInterrupt:
        # Loggers might not be setup at this point
        print_(yellow('\nProgram stopped!'))
        exit_code = 2
    except Exception as e:
        print_(red('Program interrupted!'))
        print_(red(str(e)))
        logger.exception(e)
        exit_code = 1
    if __name__ != '__main__':
        show_exit_code(exit_code)
    return exit_code


if __name__ == '__main__':
    retcode = main()
    show_exit_code(retcode)
