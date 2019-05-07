"""offers simple index of pica files, which is much, much faster both to
create and use than a the pica database using sqlachemy. The disadvantage
is that it's not a database. No queries, just lookups by PPN.
"""
from os import path
from . import core


def imake(pica_path, unicode=True):
    with open(pica_path, "rb") as pica:
        for line in pica:
            if line.startswith(b"SET:"):
                address = pica.tell()
                ppn = line.split()[6]
                if unicode:
                    ppn = ppn.decode()
                yield ppn, address


def make_tsv(pica_path, index_path):
    with open(index_path, "wb") as index:
        index.write(path.abspath(pica_path).encode() + b"\n")
        for ppn, address in imake(pica_path, unicode=False):
            for bt in (ppn, b"\t", address, b"\n"):
                index.write(bt)


def read(index_path):
    with open(index_path) as index:
        path = next(index).rstrip()
        idx = {f[0]: int(f[1]) for f in map(str.split, index)}
        return path, idx


def getlines(file, address):
    file.seek(address)
    lines = []
    for line in map(str.rstrip, file):
        if line.startswith("SET:"):
            break
        if line:
            lines.append(line)
    return lines


class PicaIndex:
    __slots__ = "index", "file"

    def __init__(self, index, path):
        self.index = index
        self.file = open(path)

    @classmethod
    def from_tsv(cls, index_path):
        path, index = read(index_path)
        return cls(index, path)

    @classmethod
    def from_file(cls, path):
        index = {ppn: addr for ppn, addr in imake(path)}
        return cls(index, path)

    def __getitem__(self, ppn):
        address = int(self.index[ppn])
        lines = getlines(self.file, address)
        return core.PicaRecord(ppn, "ƒ", lines)

    def close(self):
        self.file.close()
