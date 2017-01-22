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

file2raw() is a function which looks at a file will plain-text
    pica records and yields them as a ppn and a list of (stripped)
    lines, one at a time. No processing (aside from rstrip).

file2dicts() turns iterates over a plain-text pica records and yields a
    ppn dictionary where each item has a field id for the key and a list
    of coresponding field content with no additional parsing.

file2records() wraps file2dicts() to yield a PicaRecord object for
    each record.


both file2raw() a
"""
import functools


### helpers ###
class reify:
    """ Use as a class method decorator.  It operates almost exactly like the
    Python ``@property`` decorator, but it puts the result of the method it
    decorates into the instance dict after the first call, effectively
    replacing the function it decorates with an instance variable.  It is, in
    Python parlance, a non-data descriptor.

    Stolen from pyramid. http://docs.pylonsproject.org/projects/pyramid/en/latest/api/decorator.html#pyramid.decorator.reify
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped
        functools.update_wrapper(self, wrapped)

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


### types ###
class PicaRecord:
    """the internal representation is a dictionary where each field is a list
    of PicaField types. Everything in Pica+ can apparently come in multiple.
    However, this abstraction gives possibilities to return flat(ter)
    abstractions as well and the risk of leaving out some fields.
    """
    def __init__(self, ppn, sub_sep, lines=None, raw_dict=None):
        self.ppn = ppn
        self.raw = raw or {}
        self.sub_sep = sub_sep
        if lines is not None:
            self.extend_raw(lines)

    def __setitem__(self, key, value):
        """adds a field to the list of fields with the same name"""
        self.raw.setdefault(key, []).append(value)


    def append_raw(self, line):
        """append an unparsed line to the fields"""
        name, _, value = line.partition(' ')
        self[name] = value

    def extend_raw(self, lines):
        for line in lines:
            name, _, value = line.partition(' ')
            self[name] = value

    def __getitem__(self, key):
        return [PicaField(key, f, self.sub_sep) for f in self.raw[key]]

    def __iter__(self):
        for key, fields in self.raw.items():
            for value in fields:
                yield PicaField(key, value, self.sub_sep)

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
        fields = {}
        for i in self.raw.split(self.sep)[1:]:
            fields.setdefault(i[0], []).append(i[1:])
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


### iterators ###
def file_processor(container_factory):
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
def file2raw(line_buffer, line):
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


def file2records(file, sub_sep='ƒ'):
    """yield one pica record at a time as PicaRecords"""
    return (PicaRecord(ppn, sub_sep, raw=raw) for ppn, raw in file2dicts(file))


### tsvpica ###
def tsvpica():
    import sys
    import argparse
    fields = ['PPN', "002@", "003O", "004A", "009P", "010@", "011@", "021A",
              "021M", "022A", "022A/01", "025@", "027A", "027A/01", "027A/02",
              "027A/03", "028A", "028B/01", "028C", "028C/01", "028C/02",
              "028C/03", "028F", "032@", "032B", "033A", "034D", "036C",
              "036C/01", "036D", "036E", "036G", "037A", "037C", "041A",
              "041A/01", "041A/02", "044A", "044K", "045B", "045E", "045F",
              "045F/01", "045K", "045R", "045U", "045Z", "046B", "046C",
              "046L", "046M", "047C", "145S/01", "145S/02", "145S/06",
              "145S/07", "145S/08", "145S/11", "145Z/01", "145Z/02",
              "145Z/03"]
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add('file')
    add('-f', '--freq-sort', action='store_true',
            help='sort fields by frequency')
    add('-d', '--field-list', nargs='*', help='list of fields to use')
    add('-j', '--join-multi',
            help='join duplicate fields together with given string')

    args = ap.parse_args()

    fields = args.field_list or fields
    if 'PPN' not in fields:
        fields.insert(0, 'PPN')
    field_set = set(fields)

    if args.freq_sort:
        with open(args.file) as file:
            fields = freqfields(file, field_set)

    file = open(args.file)
    print('\t'.join(fields))

    if args.join_multi:
        for ppn, record in file2dicts(file):
            record['PPN'] = [ppn]
            field_list = []
            for field in fields:
                field_list.append(
                        args.join_multi.join(record.get(field, [])))
            print('\t'.join(field_list))

    else:
        for ppn, record in file2dicts(file):
            record['PPN'] = [ppn]
            for i in range(len(max(record.values(), key=len))):
                field_list = []
                for field in fields:
                    try:
                        field_list.append(record.get(field, [])[i])
                    except IndexError:
                        field_list.append('')
                print('\t'.join(field_list))


def freqfields(file, field_set):
    import collections
    field_count = collections.Counter()
    for ppn, record in file2dicts(file):
        field_count.update(record.keys())
    return ['PPN'] + [field for field, _ in field_count.most_common()
                      if field in field_set]
