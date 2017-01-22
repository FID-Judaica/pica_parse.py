pica_parse
==========
The ``pica_parse`` module provides a couple simple data types for
parsing and modeling plain-test Pica+ records, as well as functions for
iterating on large dumps of these records.

installation
------------
.. code:: sh

  $ git clone https://github.com/fid_judaica/pica_parse.py.git
  $ pip install pica_parse.py

pica file iterators
-------------------
One of the ways we have access to pica records is from plaintext dumps
produced by WinIBW. Because we may frequently deal with files containing
tens or hundreds of thousands of records, it is useful to have ways to
iterate over these files one record at a time.

- ``file2records`` yields a ``PicaRecord`` object for each record in the
  text file. more on ``PicaRecords`` in the next section.
- ``file2dicts()`` yields 2-tuples containing the ppn and a dictionary 

- ``file2raw()`` yields 2-tuples containing the ppn and a list of the
  rstriped lines of the record. This is for optimizing tasks which will
  disregard most of the data, and does not incure the overhead of
  beginning to parse each field (initializing a ``PicaRecord`` does not
  fully parse the record, but it does the field ids and contents into a
  dictionary and incure the cost creating an instance of a pure-python
  class).

