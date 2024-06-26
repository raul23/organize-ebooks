# organize-ebooks

Automatically organize folders with potentially huge amounts of
unorganized ebooks. This is a Python port of
[organize-ebooks.sh](https://github.com/na--/ebook-tools/blob/master/organize-ebooks.sh)
from [ebook-tools](https://github.com/na--/ebook-tools) written in shell
by [na--](https://github.com/na--).

This is done by renaming the files with proper names and moving them to
other folders. The new names are obtained based on the ISBNs found in
the ebook files. These ISBNs are extracted by using progressively more
complex methods (from searching the filename to OCR-ing the given file)
depending on the user's specified options.

<div class="contents" depth="3" local="" backlinks="top">

**Contents**
- [organize-ebooks](#organize-ebooks)
  * [About](#about)
  * [Dependencies](#dependencies)
  * [Installing with Docker (Recommended) ⭐](#installing-with-docker-recommended-)
    + [Installation instructions](#installation-instructions)
    + [Content of the Docker image](#content-of-the-docker-image)
  * [Installing the development version](#installing-the-development-version)
    + [Install](#install)
    + [Uninstall](#uninstall)
  * [Script options](#script-options)
    + [List of options](#list-of-options)
    + [Explaining some of the options/arguments](#explaining-some-of-the-optionsarguments)
  * [Script usage](#script-usage)
    + [Basic command](#basic-command)
    + [Useful commands](#useful-commands)
      - [Organize ebooks with and without ISBNs: `--owi`](#organize-ebooks-with-and-without-isbns---owi)
      - [Add more information to the filename (e.g. publisher or languages): `--oft`](#add-more-information-to-the-filename-eg-publisher-or-languages---oft)
  * [Example: organize a collection of assorted documents](#example-organize-a-collection-of-assorted-documents)
    + [Through the script `organize_ebooks.py`](#through-the-script-organize_ebookspy)
    + [Through the Python API](#through-the-python-api)
  * [Notes](#notes)
    + [`epub` and archives](#epub-and-archives)
    + [Conversion to text: files supported](#conversion-to-text-files-supported)
    + [Docker error: `requested access to the resource is denied` 😡](#docker-error-requested-access-to-the-resource-is-denied-)

</div>

## About

[organize_ebooks.py](./organize_ebooks/scripts/organize_ebooks.py)
automatically organize folders with potentially huge amounts of
unorganized ebooks. This is done by renaming the files with proper names
and moving them to other folders.

The new names are obtained based on the ISBNs found in the ebook files.
These ISBNs are extracted by using progressively more complex methods
(from searching the filename to OCR-ing the given file) depending on the
user's specified options (see [Basic command](#basic-command)).

It is a Python port of
[organize-ebooks.sh](https://github.com/na--/ebook-tools/blob/master/organize-ebooks.sh)
from [ebook-tools](https://github.com/na--/ebook-tools) written in shell
by [na--](https://github.com/na--).

<span class="title-ref">:star:</span> Other related Python projects
based on `ebook-tools`:

-   [convert-to-txt](https://github.com/raul23/convert-to-txt): convert
    documents (pdf, djvu, epub, word) to txt
-   [find-isbns](https://github.com/raul23/find-isbns): find ISBNs from
    ebooks (pdf, djvu, epub) or any string given as input to the script
-   [ocr](https://github.com/raul23/ocr): run OCR on documents (pdf,
    djvu, and images)
-   [split-ebooks-into-folders](https://github.com/raul23/split-ebooks-into-folders):
    split the supplied ebook files into folders with consecutive names
-   [interactive-organizer](https://github.com/raul23/interactive-organizer):
    interactively and manually check the ebook files that were organized
    by `organized_ebooks`.

## Dependencies

<span class="title-ref">:warning:</span>

> You can ignore this section and go straight to pulling the [Docker
> image](#installing-with-docker-recommended) which contains all the
> required dependencies and the Python package `organize_ebooks` already
> installed. This section is more for showing how I setup my system when
> porting the shell script
> [organize-ebooks.sh](https://github.com/na--/ebook-tools/blob/master/organize-ebooks.sh)
> et al. to Python.

This is the environment on which the Python package
[organize_ebooks](./organize_ebooks/) was developed and tested:

-   **Platform:** macOS

-   **Python**: version **3.7**

-   [p7zip](https://sourceforge.net/projects/p7zip/) for ISBN searching
    in ebooks that are in archives.

-   [Tesseract](https://github.com/tesseract-ocr/tesseract) for running
    OCR on books - version 4 gives better results.

    <span class="title-ref">:warning:</span> OCR is a slow
    resource-intensive process. Hence, by default only the first 7 and
    last 3 pages are OCR-ed through the option
    `--ocr-only-first-last-pages`. More info at [Script
    options](#script-options).

-   [Ghostscript](https://www.ghostscript.com/): `gs` converts *pdf* to
    *png* (useful for OCR)

-   [textutil](https://ss64.com/osx/textutil.html) or
    [catdoc](http://www.wagner.pp.ru/~vitus/software/catdoc/): for
    converting *doc* to *txt*

    **NOTE:** On macOS, you don't need `catdoc` since it has the
    built-in `textutil` command-line tool that converts any *txt*,
    *html*, *rtf*, *rtfd*, *doc*, *docx*, *wordml*, *odt*, or
    *webarchive* file

-   [DjVuLibre](http://djvu.sourceforge.net/):

    -   it includes `ddjvu` for converting *djvu* to *tif* image (useful
        for OCR), and `djvused` to get number of pages from a *djvu*
        document

    -   it includes `djvutxt` for converting *djvu* to *txt*

        <span class="title-ref">:warning:</span>

        -   To access the *djvu* command line utilities and their
            documentation, you must set the shell variable `PATH` and
            `MANPATH` appropriately. This can be achieved by invoking a
            convenient shell script hidden inside the application
            bundle:

                $ eval `/Applications/DjView.app/Contents/setpath.sh`

            **Ref.:** ReadMe from DjVuLibre

        -   You need to softlink `djvutxt` in `/user/local/bin` (or add
            it in `$PATH`)

-   [poppler](https://poppler.freedesktop.org/):

    -   it includes `pdftotext` for converting *pdf* to *txt*
    -   it includes `pdfinfo` to get number of pages from a *pdf*
        document if [mdls (macOS)](https://ss64.com/osx/mdls.html) is
        not found.

<span class="title-ref">:information_source:</span> *epub* is converted
to *txt* by using `unzip -c {input_file}`

**Optionally:**

-   [calibre](https://calibre-ebook.com/):
    -   Versions **2.84** and above are preferred because of their
        ability to manually specify from which specific online source we
        want to fetch metadata. For earlier versions you have to set
        `ISBN_METADATA_FETCH_ORDER` and `ORGANIZE_WITHOUT_ISBN_SOURCES`
        to empty strings.

    -   for fetching metadata from online sources

    -   for getting an ebook's metadata with `ebook-meta` in order to
        search it for ISBNs

    -   for converting {*pdf*, *djvu*, *epub*, *msword*} to *txt* (for
        ISBN searching) by using calibre's
        [ebook-convert](https://manual.calibre-ebook.com/generated/en/ebook-convert.html)

        <span class="title-ref">:warning:</span> `ebook-convert` is
        slower than the other conversion tools (`textutil`, `catdoc`,
        `pdftotext`, `djvutxt`)
-   **Optionally** [poppler](https://poppler.freedesktop.org/),
    [catdoc](http://www.wagner.pp.ru/~vitus/software/catdoc/) and
    [DjVuLibre](http://djvu.sourceforge.net/) can be installed for
    **faster** than calibre's conversion of `.pdf`, `.doc` and `.djvu`
    files respectively to `.txt`.
-   **Optionally** the
    [Goodreads](https://www.mobileread.com/forums/showthread.php?t=130638)
    and [WorldCat
    xISBN](https://github.com/na--/calibre-worldcat-xisbn-metadata-plugin)
    calibre plugins can be installed for better metadata fetching.

<span class="title-ref">:star:</span>

> If you only install **calibre** among these dependencies, you can
> still have a functioning program that will organize ebook collections:
>
> -   fetching metadata from online sources will work: by <span
>     class="title-ref">default
>     \<https://manual.calibre-ebook.com/generated/en/fetch-ebook-metadata.html#
>     cmdoption-fetch-ebook-metadata-allowed-plugin\></span>\_\_
>     **calibre** comes with Amazon and Google sources among others
> -   conversion to *txt* will work: <span
>     class="title-ref">calibre</span>'s own `ebook-convert` tool will
>     be used. However, accuracy and performance will be affected as
>     explained in the list of dependencies above.

## Installing with Docker (Recommended) ⭐

### Installation instructions

<span class="title-ref">:information_source:</span>

> It is recommended to install the Python package
> [organize_ebooks](./organize_ebooks/) with **Docker** because the
> Docker container has all the many [dependencies](#dependencies)
> already installed along with the Python package `organize_ebooks`.

1.  Pull the Docker image from
    [hub.docker.com](https://hub.docker.com/repository/docker/raul23/organize/general):

    ``` bash
    docker pull raul23/organize:latest
    ```

2.  Run the Docker container:

    ``` bash
    docker run -it -v /host/input/folder:/unorganized-books raul23/organize:latest
    ```

    <span class="title-ref">:information_source:</span>

    > -   `/host/input/folder` is a directory within your OS that can
    >     contain all the ebooks to be organized and is mounted as
    >     `/unorganized-books` within the Docker container.
    >
    > -   You can use the `-v` option mulitple times to mount several
    >     host output folders within the container, e.g.:
    >
    >     ``` bash
    >     docker run -it -v /host/input/folder:/unorganized-books -v /host/output/folder:/output-folder raul23/organize:latest
    >     ```
    >
    > -   `raul23/organize:latest` is the name of the image upon which
    >     the Docker container will be created.

3.  Now that you are within the Docker container, you can run the Python
    script `organize_ebooks` with the desired
    [options](#script-options):

        user:~$ organize_ebooks /unorganized-books/

    <span class="title-ref">:information_source:</span>

    > -   This basic command instructs the script `organize_ebooks` to
    >     organize the ebooks within `/unorganized-books/` and to save
    >     the renamed ebooks within the working directory which is the
    >     default location of the `-o` option (output folder).
    > -   When you log in as `user` (non-root) within the Docker
    >     container, your working directory is `/ebook-tools`.

### Content of the Docker image

<span class="title-ref">:information_source:</span>

> -   The layers of the Docker image can be checked in details at the
>     project's [Docker
>     repo](https://hub.docker.com/layers/raul23/organize/latest/images/sha256-b7a93954ff08a59a1539a45b8811d4740ca6d5fc87fc9e37d80f206fd456f55a?context=repo)
>     where you can find the commands used in the Dockerfile for
>     installing all the dependencies in the base OS (Ubuntu 18.04).
> -   This Python-based Docker image is derived from the project
>     [ebook-tools](https://github.com/na--/ebook-tools) (shell scripts
>     by [na--](https://github.com/na--)) which you can find at the
>     [Docker Hub](https://hub.docker.com/r/ebooktools/scripts/tags).
>     One of the main differences being that the base OS is Ubuntu 18.04
>     and Debian, respectively.

The [Docker
image](https://hub.docker.com/repository/docker/raul23/organize/general)
for this project contains the following components:

1.  Ubuntu 18.04: the base system of the Docker image

2.  All the [dependencies](#dependencies) (required and optional) needed
    for supporting all the features (e.g. OCR, document conversion to
    text) offered by the package `organize_ebooks`:

    -   Python 3.6.9 along with `setuptools` and `wheel`

    -   p7zip: `7z`

    -   Tesseract

    -   Ghostscript: `gs`

    -   `catdoc`

    -   DjVuLibre: `ddjvu`, `djvused`, `djvutxt`

    -   Poppler: `pdftotext` and `pdfinfo`

    -   calibre: `ebook-convert`, `ebook-meta`, calibre's metadata
        plugins (including Goodreads and WorldCat xISBN)

        The Goodreads plugin (goodreads.zip) is from this forum post (by
        a calibre Developer) (2022-12-23):
        [mobileread.com](https://www.mobileread.com/forums/showpost.php?p=4283801&postcount=5)

    -   `unzip`

3.  The Python package `organize_books` is installed. You can call the
    corresponding script with any of the [options](#script-options):

        user:~$ organize_ebooks /unorganized-books/

4.  The Python package
    [interactive_organizer](https://github.com/raul23/interactive-organizer)
    is installed. You can call the corresponding script with any of the
    [options](https://github.com/raul23/interactive-organizer#script-s-list-of-options):

        user:~$ interactive_organizer /uncertain/

5.  `user`: a user named `user` is created with UID 1000. `user` doesn't
    have root privileges within the Docker container. Thus you can't
    among other things install packages with `apt-get install`.

## Installing the development version

### Install

<span class="title-ref">:warning:</span>

> You can ignore this section and go straight to pulling the [Docker
> image](#installing-with-docker-recommended) which contains all the
> required dependencies and the Python package `organize_ebooks` already
> installed. This section is for installing the bleeding-edge version of
> the Python package `organize_ebooks` after you have installed yourself
> the many [dependencies](#dependencies).

After you have installed the [dependencies](#dependencies), you can then
install the development (bleeding-edge) version of the package
[organize_ebooks](./organize_ebooks/):

``` bash
pip install git+https://github.com/raul23/organize-ebooks#egg=organize-ebooks
```

**NOTE:** the development version has the latest features

**Test installation**

1.  Test your installation by importing `organize_ebooks` and printing
    its version:

    ``` bash
    python -c "import organize_ebooks; print(organize_ebooks.__version__)"
    ```

2.  You can also test that you have access to the `organize_ebooks.py`
    script by showing the program's version:

    ``` bash
    organize_ebooks --version
    ```

### Uninstall

To uninstall the development version of the package
[organize_ebooks](./organize_ebooks/):

``` bash
pip uninstall organize_ebooks
```

## Script options

### List of options

To display the script
[organize_ebooks.py](./organize_ebooks/scripts/organize_ebooks.py) list
of options and their descriptions:

    $ organize_ebooks -h

    usage: organize_ebooks [OPTIONS] {folder_to_organize}

    Automatically organize folders with potentially huge amounts of unorganized ebooks.
    This is done by renaming the files with proper names and moving them to other folders.

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
      --msword {catdoc,textutil,ebook-convert}        Set the conversion method for msword documents. (default: textutil)
      --pdf {pdftotext,ebook-convert}                 Set the conversion method for pdf documents. (default: pdftotext)

    Options related to extracting ISBNS from files and finding metadata by ISBN:
      --max-isbns NUMBER                              Maximum number of ISBNs to try when fetching metadata from online sources by ISBNs. (default: 5)
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
      --skip-archives                                 Skip all archives (e.g. zip, 7z) except epub files.
      -c, --corruption-check {check_only,true,false}  `check_only`: do not organize or rename files, just check them for corruption (ex. zero-filled 
                                                      files, corrupt archives or broken .pdf files). `true`: check corruption and organize/rename files. 
                                                      `false`: skip corruption check. This option is useful with the `output-folder-corrupt` option.
                                                      (default: true)
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
                                                      calibre's `fetch-ebook-metadata` command-line application, so any custom calibre metadata plugins 
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
      --pamphlet-max-filesize-kib SIZE                Other files that do not contain valid ISBNs and are below this size in KiBs are considered 
                                                      pamplets/non-ebook documents. (default: 250)

    Input/Output options:
      folder_to_organize                              Folder containing the ebook files that need to be organized.
      -o, --output-folder PATH                        The folder where ebooks that were renamed based on the ISBN metadata will be moved to. (default:
                                                      /Users/test/PycharmProjects/testing/organize/test_installation)
      --ofu, --output-folder-uncertain PATH           If `organize-without-isbn` is enabled, this is the folder to which all ebooks that were renamed 
                                                      based on non-ISBN metadata will be moved to. (default: None)
      --ofc, --output-folder-corrupt PATH             If specified, corrupt files will be moved to this folder. (default: None)
      --ofp, --output-folder-pamphlets PATH           If specified, pamphlets will be moved to this folder. (default: None)
      --oft, --output-filename-template TEMPLATE      This specifies how the filenames of the organized files will look. It is a bash string that is 
                                                      evaluated so it can be very flexible (and also potentially unsafe). 
                                                      (default: ${d[AUTHORS]// & /, } - ${d[SERIES]:+[${d[SERIES]}] - }${d[TITLE]/:/ -}
                                                      ${d[PUBLISHED]:+ (${d[PUBLISHED]%-*})}${d[ISBN]:+[${d[ISBN]}]}.${d[EXT]})
    --ome, --output-metadata-extension EXTENSION      If `keep-metadata` is enabled, this is the extension of the additional metadata file that is saved 
                                                      next to each newly renamed file. (default: meta)

### Explaining some of the options/arguments

-   `--keep-metadata`: as stated in its description above, the metadata
    files that are created alongside the renamed ebook files are useful
    for the script
    [interactive_organizer](https://github.com/raul23/interactive-organizer)
    which used them for various post-processing tasks such as showing
    the differences between the old and new filenames.

-   `--log-level`: if it is set to the logging level `warning`, you will
    only be shown on the terminal those documents that were skipped
    (e.g. the file is an image) or failed (e.g. corrupted file).

-   `--max-isbns`: especially when organizing epub files (they can
    contain many files since they are archives), many valid ISBNs can be
    found and thus the fetching of metadata from online sources might
    take longer than usual. By limiting the number of ISBNs to check,
    the script can run faster by not being bogged down by testing lots
    of ISBNs. And usually it is the first ISBN found that is the correct
    one since it appears in the very first pages of the document which
    is the most likely place to find it (the script searches ISBNs in
    the first pages, then in the end, and finally in the middle of the
    file).

-   `--skip-archives`: by default all archives (e.g. 7z, zip) are
    searched for ISBNs and this means that they will be decompressed and
    each extracted file will be recursively searched for ISBNs. Thus you
    can just skip these archives (except epub documents) when organizing
    your ebooks by using this flag.

-   `--corruption-check`: corruption check with `pdfinfo` can be very
    sensitive by flagging some PDF files as corrupted even though they
    can be opened without problems:

        Syntax Error: Dictionary key must be a name object
        Syntax Error: Couldn't find trailer dictionary

    Thus by setting this option to 'false', you can skip any corruption
    check (whether by `pdfinfo` or `7z`). By default, corruption check
    is enabled. Also if you set it to 'check_only', only corruption
    check will be performed, i.e. no organization or renaming of ebooks
    will be done.

-   The choices for `--ocr` are {always, true, false}

    -   'always': If the conversion to text was successful but no ISBNs
        were found, then OCR is run on the document. Also, if the
        conversion failed (e.g. its content is empty or doesn't contain
        any text), then OCR is applied to the document.
    -   'true': OCR is applied to the document only if the conversion to
        text failed.
    -   'false': No OCR is applied after the conversion to text.

-   `--owi, --organize-without-isbn`: if no ISBNs could be found within
    the document, the document can still be organized based on its
    author and/or title or filename by calling calibre's
    `fetch-ebook-metadata` command-line application which fetches
    metadata from online metadata sources (by default they are
    'Goodreads', 'Google', 'Amazon.com').

    These ebooks are then saved under the user specifed uncertain folder
    (`--ofu, --output-folder-uncertain`).

## Script usage

### Basic command

At bare minimum, the script `organize_ebooks` requires an input folder
containing the ebooks to organize. Thus, the following is one the most
basic command you can provide to the script:

``` bash
organize_ebooks ~/ebooks/input_folder/
```

The ebooks in the input folder will be searched for ISBNs. The script
tries to find ISBN numbers in the given ebook file by using
progressively more "expensive" tactics (as stated in
[lib.sh](https://github.com/na--/ebook-tools/blob/master/lib.sh#L519)
from [ebook-tools](https://github.com/na--/ebook-tools)).

These are the steps in order followed by the `organize_ebooks` script
when searching ISBNs for a given ebook (as soon as ISBNs are found, the
script return them):

1.  The first location it tries to find ISBNs is the filename.
2.  Then it checks the contents directly if it is a text file.
3.  The next place that is searched for ISBNs is the file metadata by
    calling calibre's `ebook-meta`.
4.  The file is decompressed with `7z` if it is an archive and the
    extracted files are recursively searched for ISBNs (epubs are
    excluded from this step even though they are basically zipped HTML
    files as explained in [epub and archives](#epub-and-archives)).
5.  The file is converted to `txt` and its text content is searched for
    ISBNs.
6.  If OCR is enabled (through the `--ocr` option), the file is OCR-ed
    and the resultant text content is searched for ISBNs.

### Useful commands

#### Organize ebooks with and without ISBNs: `--owi`

``` bash
organize_ebooks ~/input_folder/ -o ~/outut_folder/ --ofc ~/corrupt/ --ofu ~/uncertain/ --owi
```

<span class="title-ref">:information_source:</span>

> -   `--ofu, --output-folder-uncertain`: this folder will contain any
>     document that could be identified based on non-ISBN metadata (e.g.
>     title) from online sources (e.g. Goodreads). However this folder
>     is only used along with the flag `--owi` (next option explained).
> -   `--owi, --organize-without-isbn`: This flag instructs the script
>     to fetch metadata from online sources in case no ISBN could be
>     found in an ebook. The filename or the author and/or title are
>     used for fetching metadata about the book.

#### Add more information to the filename (e.g. publisher or languages): `--oft`
By default (see the [--oft](#list-of-options) option), this is the bash
string used as template when naming ebooks:

    ${d[AUTHORS]// & /, } - ${d[SERIES]:+[${d[SERIES]}] - }${d[TITLE]/:/ -}${d[PUBLISHED]:+ (${d[PUBLISHED]%-*})}${d[ISBN]:+ [${d[ISBN]}]}.${d[EXT]})

For example, it produces the following filenames:

    Cory Doctorow - Little Brother (2008) [9780007288427]
    Eric von Hippel - Democratizing Innovation (2005) [0262002744]
    Steve Jones - Almost Like a Whale - The Origin of Species Updated (2000) [9780385409858].html

If you want to add other data to the filenames such as the publisher and
languages, here is how you can modify this bash string:

``` bash
${d[AUTHORS]// & /, } - ${d[SERIES]:+[${d[SERIES]}] - }${d[TITLE]/: -} (${d[PUBLISHER]:+${d[PUBLISHER]}}, ${d[PUBLISHED]:+${d[PUBLISHED]%%-*}})${d[ISBN]:+ [${d[ISBN]}]}${d[LANGUAGES]:+ [${d[LANGUAGES]}]}.${d[EXT]}
```

Here is an example of a filename that is generated based on this
modified bash string:

    Cory Doctorow - With a Little Help (CorDoc-Company, Limited, 2010) [9780557943050] [eng].epub

This is how you would call the script `organize_ebooks` with this
modified string (`--oft, --output-filename-template` option):

``` bash
organize_ebooks ~/input -o ~/output/ --oft '${d[AUTHORS]// & /, } - ${d[SERIES]:+[${d[SERIES]}] - }${d[TITLE]/: -} (${d[PUBLISHER]:+${d[PUBLISHER]}}, ${d[PUBLISHED]:+${d[PUBLISHED]%%-*}})${d[ISBN]:+ [${d[ISBN]}]}${d[LANGUAGES]:+ [${d[LANGUAGES]}]}.${d[EXT]}'
```

<span class="title-ref">:warning:</span> When calling the Python script,
it is important to surround the bash string within **single** quotes
(not double quotes or the bash string will be evaluated right in the
command line and we don't want that).

## Example: organize a collection of assorted documents

### Through the script `organize_ebooks.py`

To organize a collection of documents (ebooks, pamplets) through the
script `organize_ebooks.py`:

``` bash
organize_ebooks ~/input_folder/ -o ~/output_folder/ --ofp ~/pamphlets/
```

<span class="title-ref">:information_source:</span> Explaining the
command

-   I only specify the input and two ouput folders and thus ignore
    corrupted files (`--ofu` not used) and ebooks without ISBNs (`--ofu`
    and `--owi` not used). These ignored files will just be skipped.
-   Also books made up with images will be skipped since OCR was not
    choosen (`--ocr` is set to 'false' by default).

### Through the Python API

Let's say we have this folder containing assorted documents:

[<img src="./images/input_folder.png" class="align-left"
alt="Example: documents to organize" />](./images/input_folder.png)

To organize this collection of documents (ebooks, pamphlets) through the
Python API (i.e. `organize_ebooks` package):

``` python
from organize_ebooks.lib import organizer

retcode = organizer.organize('/Users/test/ebooks/input_folder/',
                             output_folder='/Users/test/ebooks/output_folder',
                             output_folder_corrupt='/Users/test/ebooks/corrupt/',
                             output_folder_pamphlets='/Users/test/ebooks/pamphlets/',
                             output_folder_uncertain='/Users/test/ebooks/uncertain/',
                             organize_without_isbn=True,
                             keep_metadata=True)
```

<span class="title-ref">:information_source:</span> Explaining the
parameters of the function `organize()`

-   The first parameter to `organize()` is the input folder containing
    the documents to organize
-   `output_folder`: this is the folder where every ebooks whose ISBNs
    could be retrieved will be saved and renamed with proper names. Thus
    the program is highly confident that these ebooks are correctly
    labeled based on the found ISBNs.
-   `output_folder_corrupt`: any document that was checked (with
    `pdfinfo`) and found to be corrupted will be saved in this folder.
-   `output_folder_pamphlets`: this is the folder that will contain any
    documents without valid ISBNs (e.g. HMTL pages) that satisfy certain
    criteria for pamphlets (such as small size and low number of pages).
-   `output_folder_uncertain`: this folder will contain any documents
    that could be identified based on non-ISBN metadata (e.g. title)
    from online sources (e.g. Goodreads). However this folder is only
    used if the flag `organize_without_isbn` (next option explained) is
    set to True.
-   `organize_without_isbn`: If True, this flag specifies to fetch
    metadata from online sources in case no ISBN could be found in
    ebooks.
-   `keep_metadata`: If True, a metadata file will be saved along the
    renamed ebooks in the output folder. Also, documents that were
    identified as corrupted will be saved along with a metadata file
    that will contain info about the detected corruption.
-   If everything went well with the organization of documents,
    `organize()` will return 0 (success). Otherwise, `retcode` will be 1
    (failure).

Sample output:

[<img src="./images/script_output.png" class="align-left"
alt="Example: output terminal" />](./images/script_output.png)

Contents of the different folders after the organization:

[<img src="./images/output_folder2.png" class="align-left"
alt="Example: output folder" />](./images/output_folder2.png)

[<img src="./images/pamphlets_and_uncertain.png" class="align-left"
alt="Example: pamphlets and uncertain folders" />](./images/pamphlets_and_uncertain.png)

By default when using the API, the loggers are disabled. If you want to
enable them, call the function `setup_log()` (with the desired log level
in all caps) at the beginning of your code before the function
`organize()`:

``` python
from organize_ebooks.lib import organizer, setup_log

setup_log(logging_level='INFO')
retcode = organizer.organize('/Users/test/ebooks/input_folder/',
                             output_folder='/Users/test/ebooks/output_folder',
                             output_folder_corrupt='/Users/test/ebooks/corrupt/',
                             output_folder_pamphlets='/Users/test/ebooks/pamphlets/',
                             output_folder_uncertain='/Users/test/ebooks/uncertain/',
                             organize_without_isbn=True,
                             keep_metadata=True)
```

Sample output:

[<img src="./images/script_output_debug.png" class="align-left"
alt="Example: output terminal with debug messages" />](./images/script_output_debug.png)

## Notes

-   Having multiple metadata sources can slow down the ebooks
    organization.

    -   By default, we have for `metadata-fetch-order`:

            ['Goodreads', 'Amazon.com', 'Google', 'ISBNDB', 'WorldCat xISBN', 'OZON.ru']

    -   By default, we have for `organize-without-isbn-sources`:

            ['Goodreads', 'Amazon.com', 'Google']

    I usually get results from `Google` and `Goodreads`.

-   Books that are sometimes **skipped** for insufficient information
    from filename\\ISBN or wrong filename\\ISBN

    -   Solution manuals

    -   Obscure and/or non-english books

    -   Very old books without any ISBN

    -   A book with an invalid ISBN from the get go: only found two such
        books so far (French math books)

    -   Books with an invalid ISBN because when converting them to text
        for extracting their ISBNs, an extra number was added to the
        ISBN (and not at the end but in the middle of it) which made it
        invalid

        For the moment, I don't know what to do about this case

    -   Books whose ISBNs couldn't be extracted because the conversion
        to text (with or without OCR) was not cleaned, i.e. it added
        extra characters (not necessarily numbers) such as '·' or 'uf73'
        between the numbers of the ISBN which "broke" the regex

        Solution: I had to modify `find_isbns()` to take into account
        these annoying "artifacts" from the conversion procedure

    Obviously, they are skipped if I didn't enable OCR with the option
    `--ocr-enabled` (by default it is set to 'false')

-   I was trying to build a docker image based from
    [ebooktools/scripts](https://hub.docker.com/r/ebooktools/scripts/tags)
    which contains all the necessary dependencies (e.g. calibre,
    Tesseract) for a Debian system and I was going to add the Python
    package [organize_ebooks](./organize_ebooks/) . However, I couldn't
    build an image from the base OS `debian:sid-slim` as specified in
    its
    [Dockerfile](https://github.com/na--/ebook-tools/blob/master/Dockerfile):

        The following signatures couldn't be verified because the public key is not available: NO_PUBKEY

    Thus, I created an image from scratch starting with `ubuntu:18.04`
    that I am trying to push to hub.docker.com but I am always getting
    the error `requested access to the resource is denied` (see
    [solution](#docker-error-requested-access-to-the-resource-is-denied)).

### `epub` and archives

When searching for ISBNs, the Python script `organize_ebooks` doesn't
decompress *epub* files with `7z` because it would be a very slow
operation since `7z` decompresses archives and recursively scans the
contents which can be many files within an *epub* file. Then you would
have to search ISBNs for each of the extracted files which would
increase the running time of the script.

Instead, *epub* files are decompressed with `unzip -c` which extracts
files to stdout/screen and then the output is redirected to a temporary
text file. This text file is then searched for ISBNs. Hence the
searching for ISBNs is quicker when applying `unzip` to *epub* files
than with `7z`.

Also, the reason for using `unzip` is to make the conversion of *epub*
files to text quicker and more accurate than calibre's `ebook-convert`.

<span class="title-ref">:information_source:</span> epubs are basically
zipped HTML files

### Conversion to text: files supported

These are the files that are supported for conversion to *txt* and the
corresponding conversion tools used:

<table>
<colgroup>
<col style="width: 19%" />
<col style="width: 26%" />
<col style="width: 26%" />
<col style="width: 26%" />
</colgroup>
<thead>
<tr class="header">
<th>Files supported</th>
<th>Conversion tool #1</th>
<th>Conversion tool #2</th>
<th>Conversion tool #3</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><em>pdf</em></td>
<td><code>pdftotext</code></td>
<td><code>ebook-convert</code> (calibre)</td>
<td><ul>
<li></li>
</ul></td>
</tr>
<tr class="even">
<td><em>djvu</em></td>
<td><code>djvutxt</code></td>
<td><code>ebook-convert</code> (calibre)</td>
<td><ul>
<li></li>
</ul></td>
</tr>
<tr class="odd">
<td><em>epub</em></td>
<td><code>epubtxt</code></td>
<td><code>ebook-convert</code> (calibre)</td>
<td><ul>
<li></li>
</ul></td>
</tr>
<tr class="even">
<td><em>docx</em> (Word 2007)</td>
<td><code>ebook-convert</code> (calibre)</td>
<td><ul>
<li></li>
</ul></td>
<td><ul>
<li></li>
</ul></td>
</tr>
<tr class="odd">
<td><em>doc</em> (Word 97)</td>
<td><code>textutil</code> (macOS)</td>
<td><code>catdoc</code></td>
<td><code>ebook-convert</code> (calibre)</td>
</tr>
<tr class="even">
<td><em>rtf</em></td>
<td><code>ebook-convert</code> (calibre)</td>
<td><ul>
<li></li>
</ul></td>
<td><ul>
<li></li>
</ul></td>
</tr>
</tbody>
</table>

<span class="title-ref">:information_source:</span> Some explanations
about the table

-   `epubtxt` is a fancy way to say `unzip`.
-   By default, `ebook-convert` (calibre) is always used as a last
    resort when other methods already exist since it is slower than the
    other conversion tools.

For comparison, here are the times taken to convert completely a
154-pages PDF document to *txt* for both supported conversion methods:

-   `pdftotext`: 4.27s
-   `ebook-convert` (calibre): 80.91s

### Docker error: `requested access to the resource is denied` 😡

<span class="title-ref">:information_source:</span> If you are having
trouble pushing your docker image to hub.docker.com with an old macOS,
here is what worked for me

> I was trying to push to hub.docker.com but I was getting the error
> `requested access to the resource is denied`.
>
> I tried everything that was suggested on various forums: checking that
> I named my image and repo correctly, making sure I was logged in
> before pushing, making sure that I was not pushing to a private repo
> or to docker.io/library/, making sure that my Docker client was
> running, and so on.
>
> I was finally able to push the Docker image to hub.docker.com by
> installing Ubuntu 22.04 in a virtual machine since I was finally
> convinced that my very old macOS wasn't compatible with Docker anymore
> 😞. Also my Docker version was way too old and the latest Docker
> requires newer versions of macOS. The only `docker` operation I was
> not able to accomplish (as far as I know) with my old macOS was
> `docker push`.
>
> 👉 **SOLUTION:** if you tried everything under the sun to fix the
> `push` problem but you still couldn't solve it, then the solution is
> to finally accept that your old macOS (or any other OS) is the cause
> and you should try Docker on a newer system. Since I didn't want to
> install a newer version of macOS (I don't want to break my current
> programs and I don't think my system is able to support it), I opted
> for installing Docker with Ubuntu 22.04 under a virtual machine.
>
> What I noticed strange though was that on my old macOS when I logged
> out from Docker, I got the following message:
>
>     Not logged in to https://index.docker.io/v1/
>
> However on Ubuntu 22.04, this is what I get when I log out from Docker
> (and this is what I see from [other
> people](https://jhooq.com/requested-access-to-resource-is-denied/)
> using Docker):
>
>     Removing login credentials for https://index.docker.io/v1/
>
> Maybe on the old macOS I was not correctly authenticated (even though
> I got the message `Login Succeeded`) and thus I couldn't do the
> `docker push`.
