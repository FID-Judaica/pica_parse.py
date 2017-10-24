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
from . import core

SCHEMA = '''
CREATE TABLE IF NOT EXISTS records (
    id integer primary key,
    ppn varchar,
    field varchar,
    content varchar);
CREATE INDEX IF NOT EXISTS ppns on records (ppn);
CREATE INDEX IF NOT EXISTS fields on records (field);
CREATE INDEX IF NOT EXISTS ppnfield on records (ppn, field);
'''


class PicaDB:
    """wraps an sqlite database containing pica records so they will be
    converted to pica_parse.PicaRecord instances when they are returned.

    It also has facilities for adding verified normalizations into the
    database.
    """
    def __init__(self, connection):
        """database queries for pica records.

        - connection: an sqlit3 database. The schema for the records is
          assigned to the value of the variable `scheme` near the top of
          the file.

        - sep is the character used to separate subfields in the records.
        """
        self.con = connection
        self.cur = connection.cursor()

    def create(self):
        with self:
            self.cur.executescript(SCHEMA)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self.con.__exit__(type, value, traceback)

    def __getitem__(self, ppn):
        if isinstance(ppn, str):
            self.cur.execute(
                "SELECT field, content FROM records WHERE ppn = ?", (ppn,))
            fields = self.cur.fetchall()
            if not fields:
                raise KeyError(ppn)
            raw_dict = {}
            for f, c in fields:
                raw_dict.setdefault(f, []).append(c)
            return core.PicaRecord(ppn, self.sep, raw_dict=raw_dict)
        else:
            ppn, field = ppn
            self.cur.execute(
                "SELECT content FROM records WHERE ppn = ? AND field = ?",
                (ppn, field))
            matches = self.cur.fetchall()
            if not matches:
                raise KeyError(repr((ppn, field)))
            return [core.PicaField(field, content[0], 'ƒ')
                    for content in matches]

    def get_field(self, field, like=False):
        op = 'like' if like else '='
        self.cur.execute(
            'SELECT ppn, field, content FROM records WHERE field %s ?' % op,
            (field,))
        return ((ppn, core.PicaField(f, c, 'ƒ'))
                for ppn, f, c in self.cur.fetchall())

    def build_from_file(self, file, commit_every=10000):
        for i in self.bff_iter(file, commit_every):
            pass

    def bff_iter(self, file, commit_every=10000):
        self.create()
        with self:
            for i, rec in enumerate(core.file2dicts(file)):
                self.add_record(*rec)
                if i % commit_every == 0:
                    self.con.commit()
                    yield i
            yield i

    def add_record(self, ppn, raw_dict):
        for field, content in raw_dict.items():
            for c in content:
                self.cur.execute(
                    'INSERT INTO records (ppn, field, content) '
                    'VALUES(?, ?, ?)',
                    (ppn, field, c))


if __name__ == '__main__':
    from pathlib import Path
    import sqlite3
    PROJECT_DIR = Path(__file__).absolute().parents[1]
    DB_PATH = PROJECT_DIR/'pica.db'
    db = PicaDB(sqlite3.connect(str(DB_PATH)))
