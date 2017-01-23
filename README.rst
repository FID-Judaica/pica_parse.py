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
  text file. More on ``PicaRecords`` in the next section.
- ``file2dicts()`` yields 2-tuples containing the ppn and a dictionary
  with field ids for keys and a list of corresponding fields as values.
  The subfields are not parsed. This allows you to check some things
  about the data before incurring the cost of instantiating a bunch of
  pure python objects. However, a ``PicaRecord`` can easily be
  instantiated from the raw dictionary.

  .. code:: python

    for ppn, pica_dict in file2dicts(open('some_pica.txt')):
        if '021A' in pica_dict:
            record = PicaRecord(ppn, 'ƒ', raw_dict=pica_dict)

  This can yield a performance benefit which may make a difference when
  dealing with large numbers of records.
- ``file2lines()`` yields 2-tuples containing the ppn and a list of the
  rstripped lines of the record. This is for optimizing tasks which will
  disregard most of the data, and does not incur the overhead of
  beginning to parse each field. The output of this function can also be
  used to cheaply instantiate a ``PicaRecord``.

  .. code:: python

    for ppn, lines in file2lines(open('some_pica.txt')):
        record = PicaRecord(ppn, 'ƒ', lines=lines)

If you want additional control, there is a decorator factory you can use
to have more control over how information is collected and passed along,
``file_processor``. It's easier to show than explain:

.. code:: python

  @file_processor(list)
  def file2lines(line_buffer, line):
      line_buffer.append(line)

This is the actual implementation of the library function
``file2lines``. ``file_processor`` takes a function to create a mutable
container (e.g. ``list``, ``dict``, ``set``, etc.). The function it
decorates should take that container and an rstripped line of unparsed
pica as input. The body of the decorated function should add data to the
container with a side-effect. Return values will be discarded. The
returned funtion with be a generator that yeilds a ppn and the container
after all line of the filed has been processed.

For example, if you wanted to count in how many records a fields
appears, you could do something like this:

.. code:: python

  get_ids = file_processor(set)(lambda s, l: s.add(l.partition(' ')[0]))
  field_count = collections.Counter()
  for _, id_set in get_ids(open('some_pica.txt'):
      field_count.update(id_set)
  print(*field_count.most_common(), sep='\n')


