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

A `PicaRecord` object is a wrapper on a dictionary which has a PPN key, and a
key for each field in the record. The value for each field is a *list* of
fields with this key. Generally, there should only be one item in this list,
but some keys do appear multiple times in a record. Each object in that list is
a dictionary of subfields.

Because Python is dog slow, there are a few different methods for getting at
data with varying levels of processing.

iter_pica_file() is a function which looks at a file will plain-text pica
    records and yields them as a list of (stripped) lines one at a time. No
    processing.


pica_parse() wraps iter_pica_file() to return a PicaRecord object for each
    record.
"""
import collections
from functools import wraps, partial, update_wrapper
import unicodedata
import json
import sys


class reify:
    """ Use as a class method decorator.  It operates almost exactly like the
    Python ``@property`` decorator, but it puts the result of the method it
    decorates into the instance dict after the first call, effectively
    replacing the function it decorates with an instance variable.  It is, in
    Python parlance, a non-data descriptor.
    """
    # stolen from pyramid. http://docs.pylonsproject.org/projects/pyramid/en/latest/api/decorator.html#pyramid.decorator.reify
    def __init__(self, wrapped):
        self.wrapped = wrapped
        update_wrapper(self, wrapped)

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val


class MultipleFields(Exception):
    # exception class for PicaRecord.get(), which should return 1 or zero
    # results.
    def __init__(self, msg, values):
        self.msg = msg
        self.values = values

    def __str__(self):
        return self.msg


class PicaRecord:
    """the internal representation is a dictionary where each field is a list
    of PicaField types. Everything in Pica+ can apparently come in multiple.
    However, this abstraction gives possibilities to return flat(ter)
    abstractions as well and the risk of leaving out some fields.
    """
    def __init__(self, ppn, sub_sep, lines=None):
        self.ppn = ppn
        self.fields = collections.defaultdict(list)
        self.sub_sep = sub_sep
        if lines is not None:
            self.extend_raw(lines)

    def __setitem__(self, key, value):
        """adds a field to the list of fields with the same name"""
        self.fields[key].append(PicaField(key, value, sep=self.sub_sep))


    def append_raw(self, line):
        """append an unparsed line to the fields"""
        name, _, value = line.partition(' ')
        self[name] = value

    def extend_raw(self, lines):
        for line in lines:
            self.append_raw(line)

    def __getitem__(self, key):
        return self.fields[key]

    def items(self):
        for key, fields in self.fields.items():
            for item in fields:
                yield (key, item)

    def get(self, key, sub_key=None):
        """get always returns one or zero fields (None if zero). If a record
        has multiples of the requested field, throw a MultipleFields error. The
        optional sub_key argument will be passed to the .get() method of the
        matching field to return a (single) subfield with the same rules.

        This is to avoid always having to add a list index when you know there
        is only one field with the identifer you're looking for.
        """
        value = self[key]
        length = len(value)
        if length == 0:
            return None
        elif length == 1:
            if sub_key:
                return value[0].get(sub_key)
            return value[0]
        else:
            raise MultipleFields('key %r contains multiple values. use '
                                 'subscript notation.' % key, values)

    def dump_json(self, *args, **kwargs):
        """dump json of the record. Each field and subfield is a list. This
        list will usually only have one item, but ocassionally fields can be
        repeated in records and so too subfields in fields.
        """
        obj = {'PPN': self.ppn}
        for k, v in self.fields.items():
            obj[k] = [i.fields for i in v]

        json.dump(obj, *args, **kwargs)


class PicaField:
    def __init__(self, name, raw_field, sep):
        self.sep = sep
        self.raw = raw_field
        self.name = name

    def __str__(self):
        return self.raw

    def __repr__(self):
        return "PicaField(%r, %r)" % (self.name, self.raw)

    @reify
    def fields(self):
        fields = collections.defaultdict(list)
        for i in self.raw.split(self.sep)[1:]:
            fields[i[0]].append(i[1:])
        return fields

    def __getitem__(self, key):
        return self.fields[key]

    def items(self):
        for key, fields in self.fields.items():
            for item in fields:
                yield (key, item)

    def get(self, key):
        """get always returns one or zero subfields (None if zero). If a field
        has multiples of the requested subfield, throw a MultipleFields error.

        This is to avoid always having to add a list index when you know there
        is only one subfield with the identifer you're looking for.
        """
        value = self[key]
        length = len(value)
        if length == 0:
            return None
        elif length == 1:
            return value[0]
        else:
            raise MultipleFields('key %r contains multiple values. use '
                                 'subscript notation.' % key, values)


def iter_pica_file(file):
    """yield one pica record at a time as a tuple of (ppn, lines), where lines
    are the rstripped lines of uparsed text of the body of the record.
    """
    line_buffer = None
    for line in map(str.rstrip, file):
        if line.startswith('SET:'):
            if line_buffer:
                yield (ppn, line_buffer)

            ppn = line.split()[6]
            line_buffer = []

        elif line == '':
            continue

        line_buffer.append(line)

    yield (ppn, line_buffer)


def pica_parse(file, subfield_separator='ƒ'):
    """yield one pica record at a time as PicaRecords"""
    record = None
    for line in map(str.rstrip, file):
        if line.startswith('SET:'):
            if record:
                yield record

            ppn = line.split()[6]
            record = PicaRecord(ppn, subfield_separator)

        elif line == '':
            continue

        else:
            record.append_raw(line)

    yield record
