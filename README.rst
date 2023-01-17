===============
organize-ebooks
===============
Automatically organize folders with potentially huge amounts of unorganized ebooks.

This is done by renaming the files with proper names and moving them to other
folders.

This is a Python port of `organize-ebooks.sh <https://github.com/na--/ebook-tools/blob/master/organize-ebooks.sh>`_ 
from `ebook-tools <https://github.com/na--/ebook-tools>`_ written in shell by `na-- <https://github.com/na-->`_.

`:star:` Other related projects based on ``ebook-tools``:

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

Personal notes
==============
- Having multiple metadata sources can slow down the ebooks organization. 

  By default, we have: ``['Goodreads', 'Amazon.com', 'Google', 'ISBNDB', 'WorldCat xISBN', 'OZON.ru']``

  I Usually get results from ``Google`` and ``Goodreads`` and sometimes ``Amazon.com``.

- TODO
