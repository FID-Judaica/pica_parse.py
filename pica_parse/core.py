# Copyright 2017, Goethe University
#
# This library is free software; you can redistribute it and/or
# modify it either under the terms of:
#
#   the EUPL, Version 1.1 or – as soon they will be approved by the
#   European Commission - subsequent versions of the EUPL (the
#   "Licence"). You may obtain a copy of the Licence at:
#   https://joinup.ec.europa.eu/software/page/eupl
#
# or
#
#   the terms of the Mozilla Public License, v. 2.0. If a copy of the
#   MPL was not distributed with this file, You can obtain one at
#   http://mozilla.org/MPL/2.0/.
#
# If you do not alter this notice, a recipient may use your version of
# this file under either the MPL or the EUPL.
"""Module providing utilities for parsing plaintext pica records. It was
designed with pica+ in mind, but parts may work with other MARC-related
formats, too. or not.

more documentation can be found at:
https://github.com/FID-Judaica/pica_parse.py

A `PicaRecord` object is a wrapper on a dictionary which has a PPN key,
and a key for each field in the record. The value for each field is a
*list* of fields with this key. Generally, there should only be one item
in this list, but some keys do appear multiple times in a record. Each
object in that list is a dictionary of subfields, where the values are
likewise lists.

However, since most (but by no means all) of these lists contain only
one item, there are special .get() methods which will return a single
field, and throw and error if there are multiple.

Because Python is dog slow, there are a few different methods for
getting at data with varying levels of processing large numbers of
records.

file2lines() is a function which looks at a file will plain-text
    pica records and yields them as a ppn and a list of (stripped)
    lines, one at a time. No processing (aside from rstrip).

file2dicts() turns iterates over a plain-text pica records and yields a
    ppn dictionary where each item has a field id for the key and a list
    of coresponding field content with no additional parsing.

file2records() wraps file2dicts() to yield a PicaRecord object for
    each record.


both file2lines() a
"""
import functools
import libaaron


# # helpers # #
class MultipleFields(Exception):
    # exception class for PicaRecord.get(), which should return 1 or zero
    # results.
    def __init__(self, msg, values):
        self.msg = msg
        self.values = values

    def __str__(self):
        return self.msg


# # types # #
class PicaRecord:
    """the internal representation is a dictionary where each field is a list
    of PicaField types. Everything in Pica+ can apparently come in multiple.
    However, this abstraction gives possibilities to return flat(ter)
    abstractions as well and the risk of leaving out some fields.
    """
    def __init__(self, ppn, sub_sep, lines=None, raw_dict=None):
        self.ppn = ppn
        self.dict = raw_dict or {}
        self.sub_sep = sub_sep
        if lines is not None:
            self.extend_raw(lines)

    def __repr__(self):
        return 'PicaRecord(%r, %r, %r)' % (self.ppn, self.sub_sep, self.dict)

    def __setitem__(self, key, value):
        """adds a field to the list of fields with the same id"""
        self.dict.setdefault(key, []).append(value)

    def append_raw(self, line):
        """append an unparsed line to the fields"""
        id_, _, value = line.partition(' ')
        self[id_] = value

    def extend_raw(self, lines):
        for line in lines:
            id_, _, value = line.partition(' ')
            self[id_] = value

    def __getitem__(self, key):
        return [PicaField(key, f, self.sub_sep) for f in self.dict[key]]

    def __iter__(self):
        for key, fields in self.dict.items():
            for value in fields:
                yield PicaField(key, value, self.sub_sep)

    def __contains__(self, key):
        return key in self.dict

    def get(self, key, sub_key=None, default=None):
        """get always returns one or zero fields (None if zero). If a record
        has multiples of the requested field, throw a MultipleFields error. The
        optional sub_key argument will be passed to the .get() method of the
        matching field to return a (single) subfield with the same rules.

        This is to avoid always having to add a list index when you know there
        is only one field with the identifer you're looking for.
        """
        try:
            value = self[key]
        except KeyError:
            return default
        if len(value) == 1:
            if sub_key:
                return value[0].get(sub_key, default)
            return value[0]
        else:
            raise MultipleFields('key %r contains multiple values. use '
                                 'subscript notation.' % key, value)


class PicaField:
    def __init__(self, id_, raw_field, sep):
        self.sep = sep
        self.raw = raw_field
        self.id = id_

    def __str__(self):
        return self.id + ' ' + self.raw

    def __repr__(self):
        return "PicaField(%r, %r)" % (self.id, self.raw)

    @libaaron.reify
    def dict(self):
        fields = {}
        for i in self.raw.lstrip(self.sep).split(self.sep):
            fields.setdefault(i[0], []).append(i[1:])
        return fields

    def __getitem__(self, key):
        return self.dict[key]

    def items(self):
        for key, fields in self.dict.items():
            for item in fields:
                yield (key, item)

    def __contains__(self, key):
        return key in self.dict

    def get(self, key, default=None):
        """get always returns one or zero subfields (None if zero). If a field
        has multiples of the requested subfield, throw a MultipleFields error.

        This is to avoid always having to add a list index when you know there
        is only one subfield with the identifer you're looking for.
        """
        try:
            value = self[key]
        except KeyError:
            return default
        if len(value) == 1:
            return value[0]
        else:
            raise MultipleFields('key %r contains multiple values. use '
                                 'subscript notation.' % key, value)


# # iterators # #
def file_processor(container_factory):
    """Decorator factory. The parameter should be a function to create a
    container you will collect things in will iterating over the lines of a
    pica record, like `list`, `dict`, `set` or what have you.

    The wrapped function should take that container as parameter 1, and the
    current line of pica as parameter 2. The returned function will take a
    file-like object as input and each yielded item will be a tuple containting
    the ppn and the container object after you've iterated over every line.
    This is the internal implementation of file2lines:

    >>> @file_processor(list)
    ... def file2lines(line_buffer, line):
    ...    line_buffer.append(line)

    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped(file):
            line = next(file)
            while not line.startswith('SET:'):
                line = next(file)
            ppn = line.split()[6]
            container = container_factory()
            for line in map(str.rstrip, file):
                if line.startswith('SET:'):
                    yield (ppn, container)
                    ppn = line.split()[6]
                    container = container_factory()
                elif line == '':
                    continue
                else:
                    func(container, line)
            yield (ppn, container)

        return wrapped

    return decorator


@file_processor(list)
def file2lines(line_buffer, line):
    """yield one pica record at a time as a tuple of (ppn, lines), where lines
    are the rstripped lines of uparsed text of the body of the record.
    """
    line_buffer.append(line)


@file_processor(dict)
def file2dicts(record, line):
    """yield one pica record at a time as a tuple of (ppn, raw_dict), where
    raw_dict is a dictionary of fields, where each value is a list, in the
    event of multiple fields. No subfields are parsed.
    """
    id_, _, value = line.partition(' ')
    record.setdefault(id_, []).append(value)


@file_processor(list)
def file2tuplist(lines, line):
    lines.append(line.split(' ', maxsplit=1))


def file2records(file, sub_sep='ƒ'):
    """yield one pica record at a time as PicaRecords"""
    return (PicaRecord(ppn, sub_sep, raw_dict=d)
            for ppn, d in file2dicts(file))
