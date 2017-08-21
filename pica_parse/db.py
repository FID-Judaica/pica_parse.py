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

schema = '''
CREATE TABLE records
(id integer primary key, ppn varchar, field varchar, content varchar);
CREATE INDEX ppns on records (ppn);
CREATE INDEX fields on records (field);
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


if __name__ == '__main__':
    from pathlib import Path
    import sqlite3
    PROJECT_DIR = Path(__file__).absolute().parents[1]
    DB_PATH = PROJECT_DIR/'pica.db'
    db = PicaDB(sqlite3.connect(str(DB_PATH)))
