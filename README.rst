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
  used to instantiate a ``PicaRecord``.

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
returned function with be a generator that yields a ppn and the container
after every line of the filed has been processed.

For example, if you wanted to count in how many records a field appears,
you could do something like this:

.. code:: python

  get_ids = file_processor(set)(lambda s, l: s.add(l.partition(' ')[0]))
  field_count = collections.Counter()
  for _, id_set in get_ids(open('some_pica.txt'):
      field_count.update(id_set)
  print(*field_count.most_common(), sep='\n')

``PicaRecord`` objects
----------------------

.. code:: python

  >>> import pica_parse
  >>> records = pica_parse.file2records(open('titles in hebrew language 06.10.16.txt'))
  >>> r = next(records)
  >>> r.ppn
  '019106858'

A ``PicaRecord`` provides an interface similar to a dictionary for pica
records with a few convenience features. A Pica+ record can
multiple versions of the same field containing different data, in a
``PicaRecord`` is a list of fields. If you use the normal subscript
syntax, you will a list of ``PicaField`` instances. Usually, this list
will contain one item. Because of this, a ``PicaRecord`` has a special
``.get()`` method which will only ever return a single ``PicaField``
instance or fall back to the default if there is no such field (default
defaults to ``None``). If there are multiple matching fields, it will
throw a ``MultipleFields`` error.

.. code:: python

  >>> r['021A']
  [PicaField('021A', "ƒa@Šel-lô be-derek ham-melekƒhMiryām Har'ēl")]
  >>> r.get('021A')
  PicaField('021A', "ƒa@Šel-lô be-derek ham-melekƒhMiryām Har'ēl")

Additionally the ``.get()`` method can take an additional argument that
will be passed on to the ``get`` method of the ``PicaField``, in order
to return the contents of a subfield.

.. code:: python

  >>> r.get('021A', 'a')
  '@Šel-lô be-derek ham-melek'

Again, this is only for cases where you know there is only one matching
field and one matching subfield (subfields can also be repeated within a
field, so they are stored internally as lists as well).

These list shenanigans are also abstracted away when iterating.
Iterating on a ``PicaRecord`` instance yields all fields independently,
even if there are repeat field ids.

.. code:: python

  >>> for i in r:
  ...   print(repr(i))
  PicaField('002@', 'ƒ0Aauc')
  PicaField('003O', 'ƒaOCoLCƒ0180488447')
  PicaField('010@', 'ƒaheb')
  PicaField('011@', 'ƒa1991ƒn1991')
  PicaField('013H', 'ƒ0z')
  PicaField('015@', 'ƒ00')
  PicaField('021A', "ƒa@Šel-lô be-derek ham-melekƒhMiryām Har'ēl")
  PicaField('028A', 'ƒ9162624026ƒ8Harel, Miriam')
  PicaField('033A', 'ƒpTel-AvivƒnTammuz Publ.')
  PicaField('034D', 'ƒa288 S.')
  PicaField('046B', 'ƒaParallelsacht.: Not the main road')
  PicaField('046L', 'ƒaIn hebr. Schr.')
  PicaField('101@', 'ƒa3')
  PicaField('101B', 'ƒ009-07-04ƒt11:35:38.000')
  PicaField('145S/06', 'ƒa770')
  PicaField('145Z/01', 'ƒaZ-sl')
  PicaField('208@/01', 'ƒa26-02-92ƒbhAa')
  PicaField('201B/01', 'ƒ027-01-02ƒt21:26:25.028')
  PicaField('203@/01', 'ƒ0026363410')
  PicaField('209A/01', 'ƒa84.792.99ƒf000ƒduƒh84 792 99ƒx00')
  PicaField('209G/01', 'ƒa84792993ƒx00')
  PicaField('247C/01', 'ƒ9102598258ƒ8601000-3 <30>Frankfurt, Universitätsbibliothek J. C. Senckenberg, Zentralbibliothek (ZB)')

OK, bad example, since there aren't any repeat ids in this record, but
if there were, you'd get a separate item for each one. If this were one
of the newer records with Hebrew and Romanized metadata entries, you'd
see something a bit more like this:

.. code:: python

  ...
  PicaField('021A', 'ƒT01ƒULatnƒaha- @Galil bi-teḳufat ha-MishnahƒhAharon Openhaymer')
  PicaField('021A', 'ƒT01ƒUHebrƒaה @גליל בתקופת המשנהƒhאהרון אופנהיימר')
  PicaField('027A', 'ƒaGalilee in the Mishnaic period')
  PicaField('027A/01', 'ƒahag- @Gālîl bi-teqûfat ham-Mišnā')
  PicaField('028A', 'ƒT01ƒULatnƒ9138634653ƒ8Ôppenhaimer, Aharon, 1940-')
  PicaField('028A', 'ƒT01ƒUHebrƒ9138634653ƒ8אופנהיימר, אהרן, 1940-')
  PicaField('033A', 'ƒT01ƒULatnƒpJerusalemƒnThe Zalman Shazar Center for Jewish History')
  PicaField('033A', 'ƒT01ƒUHebrƒpירושליםƒnמרכז זלמן שזר לתולדות ישראל')
  PicaField('034D', 'ƒa199 S.')
  PicaField('034M', 'ƒaIll., Kt.')
  PicaField('036E', 'ƒT01ƒULatnƒaMonografyot be-toldot ʿam Yiśraʾelƒl22')
  PicaField('036E', 'ƒT01ƒUHebrƒaמונוגרפיות בתולדות עם ישראלƒl22')
  ...
