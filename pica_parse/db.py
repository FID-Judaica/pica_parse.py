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
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
SEP = 'ƒ'
Base = declarative_base()


class Field(Base):
    __tablename__ = 'records'

    id = sa.Column(sa.Integer, primary_key=True)
    ppn = sa.Column(sa.String, index=True)
    field = sa.Column(sa.String, index=True)
    content = sa.Column(sa.String)


sa.Index('ppnfield', Field.ppn, Field.field)


class PicaDB:
    """wraps an sqlite database containing pica records so they will be
    converted to pica_parse.PicaRecord instances when they are returned.

    It also has facilities for adding verified normalizations into the
    database.
    """
    def __init__(self, sqlachemy_url):
        """database queries for pica records.

        - sqlachemy_url: a sqlalchemy-format database url. see:
        http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
        """
        self.engine = sa.create_engine(sqlachemy_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create(self):
        with self:
            Base.metadata.create_all(self.engine)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type:
            self.session.rollback()
        else:
            self.session.commit()

    def __getitem__(self, ppn):
        if isinstance(ppn, str):
            results = self.session.query(Field.field, Field.content)\
                     .filter_by(ppn=ppn).all()
            if not results:
                raise KeyError(ppn)
            raw_dict = {}
            for f, c in results:
                raw_dict.setdefault(f, []).append(c)
            return core.PicaRecord(ppn, SEP, raw_dict=raw_dict)
        else:
            ppn, field = ppn
            results = self.session.query(Field.content)\
                .filter(Field.ppn == ppn, Field.field == field).all()
            if not results:
                raise KeyError(repr((ppn, field)))
            return [core.PicaField(field, f.content, SEP) for f in results]

    def get_field(self, field, like=False):
        query = self.session.query(Field).filter(field=field)
        return ((ppn, core.PicaField(f, c, SEP))
                for ppn, f, c in query)

    def build_from_file(self, file, commit_every=10000):
        for i in self.bff_iter(file, commit_every):
            pass

    def bff_iter(self, file, commit_every=10000):
        self.create()
        with self:
            for i, (ppn, rec) in enumerate(core.file2tuplist(file)):
                self.add_record(ppn, rec)
                if i % commit_every == 0:
                    self.session.commit()
                    yield i
            yield i

    def add_record(self, ppn, tuplist):
        self.session.add_all(
            Field(ppn=ppn, field=field, content=content)
            for field, content in tuplist)
