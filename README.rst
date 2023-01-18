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

TODO

Examples
========
Organize a collection of assorted documents
-------------------------------------------

Through the script ``organize_ebooks.py``
"""""""""""""""""""""""""""""""""""""""""
To organize a collection of documents (ebooks, pamplets) through the script ``organize_ebooks.py``::

 python organize.py ~/Data/test/input_folder/ -o ~/ebooks/output_folder --ofp ~/ebooks/pamphlets/
 
`:information_source:` Explaining the command

- You only specify the input and two ouput folders and thus ignore corrupted files and ebooks without ISBNs.
  These ignored files will just be skipped.
- Also books made up with images will be skipped since OCR was not choosen.

Through the API
"""""""""""""""
To organize a collection of documents (ebooks, pamplets) through the API: 

.. code-block:: python

   from organize_ebooks.lib import organizer

   retcode = organizer.organize('/Users/test/Data/test/input_folder/',
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
