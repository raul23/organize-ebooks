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
TODO

Uninstall
=========
TODO

Script options
==============
To display the script `organize_ebooks.py <./find_iorganize_ebooks/scripts/organize_ebooks.py>`_ list of options and their descriptions::

 $ organize_ebooks -h

TODO

Examples
========
Organize a collection of ebooks
-------------------------------

Through the script ``organize_ebooks.py``
"""""""""""""""""""""""""""""""""""""""""
TODO

Through the API
"""""""""""""""
TODO

TODOs and personal notes
========================
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
  - A book with an invalid ISBN from the get go: only found one such book so far (a French book about analysis)
  - Books with an invalid ISBN because when converting them to text for extracting their ISBNs, an extra number was added to 
    the ISBN (and not at the end but in the middle of it) which made it invalid
    
    For the moment, I don't know what to do about this case
  - Books whose ISBNs couldn't be extracted because the conversion to text (with or without OCR) was not cleaned, i.e.
    it added extra characters (not necessarily numbers) such as '·' or '\uf73' between the numbers of the ISBN which "broke" the regex
    
    Solution: I had to modify ``find_isbns()`` to take into account these annoying "artifacts" from the conversion procedure
  - PhD thesis

  Obviously, they are skipped if I didn't enable OCR with the option ``--ocr-enabled`` (by default it is set to 'false')

- ``pdfinfo`` can be too sensitive sometimes by labeling PDF books as corrupted even though they can be opened without problems::

   Syntax Error: Dictionary key must be a name object
   Syntax Error: Couldn't find trailer dictionary
   
  TODO: ignore these errors and continue processing the PDF file
  
- Maybe skip archives (e.g. ``zip`` and ``7z``) by default? Can really slow down everything since each decompressed file is analyzed for ISBNs. [TODO]
