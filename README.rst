===============
organize-ebooks
===============
Automatically organize folders with potentially huge amounts of unorganized ebooks.

This is done by renaming the files with proper names and moving them to other
folders.

This is a Python port of `organize-ebooks.sh <https://github.com/na--/ebook-tools/blob/master/organize-ebooks.sh>`_ 
from `ebook-tools <https://github.com/na--/ebook-tools>`_ written in shell by `na-- <https://github.com/na-->`_.

`:star:` Other related Python projects based on ``ebook-tools``:

- `convert-to-txt <https://github.com/raul23/convert-to-txt>`_: convert documents (pdf, djvu, epub, word) to txt
- `find-isbns <https://github.com/raul23/find-isbns>`_: find ISBNs from ebooks (pdf, djvu, epub) or any string given as input to the script
- `ocr <https://github.com/raul23/ocr>`_: OCR documents (pdf, djvu, and images)
- `split-ebooks-into-folders <https://github.com/raul23/split-ebooks-into-folders>`_: split the supplied ebook files into 
  folders with consecutive names

|

.. contents:: **Contents**
   :depth: 3
   :local:
   :backlinks: top

Dependencies
============
This is the environment on which the script `organize_ebooks.py <./organize_ebooks/scripts/organize_ebooks.py>`_ was tested:

* **Platform:** macOS
* **Python**: version **3.7**

TODO

Installation
============
To install the `organize_ebooks <./organize_ebooks/>`_ package::

 $ pip install git+https://github.com/raul23/organize-ebooks#egg=organize-ebooks
 
**Test installation**

1. Test your installation by importing ``organize_ebooks`` and printing its
   version::

   $ python -c "import organize_ebooks; print(organize_ebooks.__version__)"

2. You can also test that you have access to the ``organize_ebooks.py`` script by
   showing the program's version::

   $ organize_ebooks --version

Uninstall
=========
To uninstall the `organize_ebooks <./organize_ebooks/>`_ package::

 $ pip uninstall organize_ebooks

Script options
==============
To display the script `organize_ebooks.py <./find_iorganize_ebooks/scripts/organize_ebooks.py>`_ list of options and their descriptions::

  $ organize_ebooks -h

  usage: organize_ebooks [OPTIONS] {folder_to_organize}

  Automatically organize folders with potentially huge amounts of unorganized ebooks.
  This is done by renaming the files with proper names and moving them to other folders..

  This script is based on the great ebook-tools written in shell by na-- (See https://github.com/na--/ebook-tools).

  General options:
    -h, --help                                      Show this help message and exit.
    -v, --version                                   Show program's version number and exit.
    -q, --quiet                                     Enable quiet mode, i.e. nothing will be printed.
    --verbose                                       Print various debugging information, e.g. print traceback when there is an exception.
    -d, --dry-run                                   If this is enabled, no file rename/move/symlink/etc. operations will actually be executed.
    -s, --symlink-only                              Instead of moving the ebook files, create symbolic links to them.
    -k, --keep-metadata                             Do not delete the gathered metadata for the organized ebooks, instead save it in an 
                                                    accompanying file together with each renamed book. It is very useful for semi-automatic 
                                                    verification of the organized files for additional verification, indexing or processing at 
                                                    a later date.
    -r, --reverse                                   If this is enabled, the files will be sorted in reverse (i.e. descending) order. By default, 
                                                    they are sorted in ascending order.
    --log-level {debug,info,warning,error}          Set logging level. (default: info)
    --log-format {console,only_msg,simple}          Set logging formatter. (default: only_msg)

  Convert-to-txt options:
    --djvu {djvutxt,ebook-convert}                  Set the conversion method for djvu documents. (default: djvutxt)
    --epub {epubtxt,ebook-convert}                  Set the conversion method for epub documents. (default: epubtxt)
    --msword {catdoc,textutil,ebook-convert}        Set the conversion method for epub documents. (default: textutil)
    --pdf {pdftotext,ebook-convert}                 Set the conversion method for pdf documents. (default: pdftotext)

  Options related to extracting ISBNS from files and finding metadata by ISBN:
    -i, --isbn-regex ISBN_REGEX                     This is the regular expression used to match ISBN-like numbers in the supplied books. (default:
                                                    (?<![0-9])(-?9-?7[789]-?)?((-?[0-9]-?){9}[0-9xX])(?![0-9]))
    --isbn-blacklist-regex REGEX                    Any ISBNs that were matched by the ISBN_REGEX above and pass the ISBN validation algorithm are
                                                    normalized and passed through this regular expression. Any ISBNs that successfully match against 
                                                    it are discarded. The idea is to ignore technically valid but probably wrong numbers like 
                                                    0123456789, 0000000000, 1111111111, etc.. (default: ^(0123456789|([0-9xX])\2{9})$)
    --isbn-direct-files REGEX                       This is a regular expression that is matched against the MIME type of the searched files. Matching 
                                                    files are searched directly for ISBNs, without converting or OCR-ing them to .txt first. 
                                                    (default: ^text/(plain|xml|html)$)
    --isbn-ignored-files REGEX                      This is a regular expression that is matched against the MIME type of the searched files. Matching 
                                                    files are not searched for ISBNs beyond their filename. By default, it tries to ignore .gif and 
                                                    .svg images, audio, video and executable files and fonts. 
                                                    (default: ^(image/(gif|svg.+)|application/(x-shockwave-flash|CDFV2|vnd.ms-
                                                    opentype|x-font-ttf|x-dosexec|vnd.ms-excel|x-java-applet)|audio/.+|video/.+)$)
    --reorder-files LINES [LINES ...]               These options specify if and how we should reorder the ebook text before searching for ISBNs in 
                                                    it. By default, the first 400 lines of the text are searched as they are, then the last 50 are 
                                                    searched in reverse and finally the remainder in the middle. This reordering is done to improve 
                                                    the odds that the first found ISBNs in a book text actually belong to that book (ex. from the 
                                                    copyright section or the back cover), instead of being random ISBNs mentioned in the middle of the 
                                                    book. No part of the text is searched twice, even if these regions overlap. Set it
                                                    to `False` to disable the functionality or `first_lines last_lines` to enable it with the 
                                                    specified values. (default: 400 50)
    --irs, --isbn-return-separator SEPARATOR        This specifies the separator that will be used when returning any found ISBNs. (default: ' - ')
    -m, ---metadata-fetch-order METADATA_SOURCE [METADATA_SOURCE ...]
                                                    This option allows you to specify the online metadata sources and order in which the subcommands 
                                                    will try searching in them for books by their ISBN. The actual search is done by calibre's `fetch-
                                                    ebook-metadata` command-line application, so any custom calibre metadata plugins can also be used. 
                                                    To see the currently available options, run `fetch-ebook-metadata --help` and check the 
                                                    description for the `--allowed-plugin` option. If you use Calibre versions that are older than 
                                                    2.84, it's required to manually set this option to an empty string. 
                                                    (default: ['Goodreads', 'Google', 'Amazon.com', 'ISBNDB', 'WorldCat xISBN', 'OZON.ru'])

  OCR options:
    --ocr, --ocr-enabled {always,true,false}        Whether to enable OCR for .pdf, .djvu and image files. It is disabled by default. (default: false)
    --ocrop, --ocr-only-first-last-pages PAGES PAGES
                                                    Value 'n m' instructs the script to convert only the first n and last m pages when OCR-ing ebooks. 
                                                    (default: 7 3)

  Organize options:
    -c, --corruption-check-only                     Do not organize or rename files, just check them for corruption (ex. zero-filled files, corrupt 
                                                    archives or broken .pdf files). Useful with the `output-folder-corrupt` option.
    -t, --tested-archive-extensions REGEX           A regular expression that specifies which file extensions will be tested with `7z t` for 
                                                    corruption.
                                                    (default: ^(7z|bz2|chm|arj|cab|gz|tgz|gzip|zip|rar|xz|tar|epub|docx|odt|ods|cbr|cbz|maff|iso)$)
    --owi, --organize-without-isbn                  Specify whether the script will try to organize ebooks if there were no ISBN found in the book or 
                                                    if no metadata was found online with the retrieved ISBNs. If enabled, the script will first try to 
                                                    use calibre's `ebook-meta` command-line tool to extract the author and title metadata from the 
                                                    ebook file. The script will try searching the online metadata sources (`organize-without-isbn-
                                                    sources`) by the extracted author & title and just by title. If there is no useful metadata or 
                                                    nothing is found online, the script will try to use the filename for searching.
    --owis, --organize-without-isbn-sources METADATA_SOURCE [METADATA_SOURCE ...]
                                                    This option allows you to specify the online metadata sources in which the script will try 
                                                    searching for books by non-ISBN metadata (i.e. author and title). The actual search is done by 
                                                    calibre's `fetch-ebook-metadata` command- line application, so any custom calibre metadata plugins 
                                                    can also be used. To see the currently available options, run `fetch-ebook-metadata --help` and 
                                                    check the description for the `--allowed-plugin` option. Because Calibre versions older than 2.84 
                                                    don't support the `--allowed-plugin` option, if you want to use such an old Calibre
                                                    version you should manually set `organize_without_isbn_sources` to an empty string. 
                                                    (default: ['Goodreads', 'Google', 'Amazon.com'])
    -w, --without-isbn-ignore REGEX                 This is a regular expression that is matched against lowercase filenames. All files that do not 
                                                    contain ISBNs are matched against it and matching files are ignored by the script, even if 
                                                    `organize-without-isbn` is true. The default value is calibrated to match most periodicals 
                                                    (magazines, newspapers, etc.) so the script can ignore them. (default: complex default value, see 
                                                    the README)
    --pamphlet-included-files REGEX                 This is a regular expression that is matched against lowercase filenames. All files that do not 
                                                    contain ISBNs and do not match `without-isbn-ignore` are matched against it and matching files are 
                                                    considered pamphlets by default. They are moved to `output_folder_pamphlets` if set, otherwise 
                                                    they are ignored. (default: \.(png|jpg|jpeg|gif|bmp|svg|csv|pptx?)$)
    --pamphlet-excluded-files REGEX                 This is a regular expression that is matched against lowercase filenames. If files do not contain 
                                                    ISBNs and match against it, they are NOT considered as pamphlets, even if they have a small size 
                                                    or number of pages. (default: \.(chm|epub|cbr|cbz|mobi|lit|pdb)$)
    --pamphlet-max-pdf-pages PAGES                  .pdf files that do not contain valid ISBNs and have a lower number pages than this are considered 
                                                    pamplets/non-ebook documents. (default: 50)
    --pamphlet-max-filesize-kb SIZE                 Other files that do not contain valid ISBNs and are below this size in KBs are considered 
                                                    pamplets/non-ebook documents. (default: 250)

  Input/Output options:
    folder_to_organize                              Folder containing the ebook files that need to be organized.
    -o, --output-folder PATH                        The folder where ebooks that were renamed based on the ISBN metadata will be moved to. (default:
                                                    /Users/test/PycharmProjects/testing/organize/test_installation)
    --ofu, --output-folder-uncertain PATH           If `organize-without-isbn` is enabled, this is the folder to which all ebooks that were renamed 
                                                    based on non-ISBN metadata will be moved to. (default: None)
    --ofc, --output-folder-corrupt PATH             If specified, corrupt files will be moved to this folder. (default: None)
    --ofp, --output-folder-pamphlets PATH           If specified, pamphlets will be moved to this folder. (default: None)

Example: organize a collection of assorted documents
====================================================
Through the script ``organize_ebooks.py``
-----------------------------------------
To organize a collection of documents (ebooks, pamplets) through the script ``organize_ebooks.py``::

 organize ~/ebooks/input_folder/ -o ~/ebooks/output_folder/ --ofp ~/ebooks/pamphlets/
 
`:information_source:` Explaining the command

- I only specify the input and two ouput folders and thus ignore corrupted files (``--ofu`` not used) and 
  ebooks without ISBNs (``--ofu`` and ``--owi`` not used). These ignored files will just be skipped.
- Also books made up with images will be skipped since OCR was not choosen (``--ocr`` is set to 'false' by default).

Through the API
---------------
To organize a collection of documents (ebooks, pamplets) through the API: 

.. code-block:: python

   from organize_ebooks.lib import organizer

   retcode = organizer.organize('/Users/test/ebooks/input_folder/',
                                output_folder='/Users/test/ebooks/output_folder',
                                output_folder_corrupt='/Users/test/ebooks/corrupt/',
                                output_folder_pamphlets='/Users/test/ebooks/pamphlets/',
                                output_folder_uncertain='/Users/test/ebooks/uncertain/',
                                organize_without_isbn=True,
                                keep_metadata=True)

`:information_source:` Explaining the parameters of the function ``organize()``

- The first parameter to ``organize()`` is the input folder containing the documents to organize
- ``output_folder``: this is the folder where every ebooks whose ISBNs could be retrieved will be saved and renamed with proper names. 
  Thus the program is highly confident that these ebooks are correctly labeled based on the found ISBNs.
- ``output_folder_corrupt``: any document that was checked (with ``pdfinfo``) and found to be corrupted will be saved in this folder.
- ``output_folder_pamphlets``: this is the folder that will contain any documents without valid ISBNs (e.g. HMTL pages) that satisfy certain 
  criteria for pamphlets (such as small size and low number of pages).
- ``output_folder_uncertain``: this folder will contain any documents that could be identified based on non-ISBN metadata (e.g. title) 
  from online sources (e.g. Goodreads). However this folder is only used if the flag ``organize_without_isbn`` (next option explained) 
  is set to True.
- ``organize_without_isbn``: If True, this flag specifies to fetch metadata from online sources in case no ISBN could be found in ebooks.
- ``keep_metadata``: If True, a metadata file will be saved along the renamed ebooks in the output folder. Also, documents that were
  identified as corrupted will be saved along with a metadata file that will contain info about the detected corruption.

TODOs and notes
===============
- Having multiple metadata sources can slow down the ebooks organization. 

  - By default, we have for ``metadata-fetch-order``:: 
  
     ['Goodreads', 'Amazon.com', 'Google', 'ISBNDB', 'WorldCat xISBN', 'OZON.ru']
  
  - By default, we have for ``organize-without-isbn-sources``::
     
     ['Goodreads', 'Amazon.com', 'Google']
  
  I usually get results from ``Google`` and ``Goodreads``. Thus need to change the default order of both lists [TODO]

- Books that are sometimes **skipped** for insufficient information from filename\\ISBN or wrong filename\\ISBN

  - Solution manuals
  - Obscure and/or non-english books
  - Very old books without any ISBN
  - A book with an invalid ISBN from the get go: only found two such books so far (French math books)
  - Books with an invalid ISBN because when converting them to text for extracting their ISBNs, an extra number was added to 
    the ISBN (and not at the end but in the middle of it) which made it invalid
    
    For the moment, I don't know what to do about this case
  - Books whose ISBNs couldn't be extracted because the conversion to text (with or without OCR) was not cleaned, i.e.
    it added extra characters (not necessarily numbers) such as '·' or '\uf73' between the numbers of the ISBN which "broke" the regex
    
    Solution: I had to modify ``find_isbns()`` to take into account these annoying "artifacts" from the conversion procedure

  Obviously, they are skipped if I didn't enable OCR with the option ``--ocr-enabled`` (by default it is set to 'false')

- ``pdfinfo`` can be too sensitive sometimes by labeling PDF books as corrupted even though they can be opened without problems::

   Syntax Error: Dictionary key must be a name object
   Syntax Error: Couldn't find trailer dictionary
   
  TODO: ignore these errors and continue processing the PDF file
  
- Maybe skip archives (e.g. ``zip`` and ``7z``) by default? Can really slow down everything since each decompressed file is analyzed for ISBNs. [TODO]
