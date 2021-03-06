import argparse
import collections
from . import core

print(__file__)


def tsvpica():
    fields = [
        "PPN",
        "002@",
        "003O",
        "004A",
        "009P",
        "010@",
        "011@",
        "021A",
        "021M",
        "022A",
        "022A/01",
        "025@",
        "027A",
        "027A/01",
        "027A/02",
        "027A/03",
        "028A",
        "028B/01",
        "028C",
        "028C/01",
        "028C/02",
        "028C/03",
        "028F",
        "032@",
        "032B",
        "033A",
        "034D",
        "036C",
        "036C/01",
        "036D",
        "036E",
        "036G",
        "037A",
        "037C",
        "041A",
        "041A/01",
        "041A/02",
        "044A",
        "044K",
        "045B",
        "045E",
        "045F",
        "045F/01",
        "045K",
        "045R",
        "045U",
        "045Z",
        "046B",
        "046C",
        "046L",
        "046M",
        "047C",
        "145S/01",
        "145S/02",
        "145S/06",
        "145S/07",
        "145S/08",
        "145S/11",
        "145Z/01",
        "145Z/02",
        "145Z/03",
    ]
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("file")
    add(
        "-f",
        "--freq-sort",
        action="store_true",
        help="sort fields by frequency",
    )
    add("-d", "--field-list", nargs="*", help="list of fields to use")
    add(
        "-j",
        "--join-multi",
        help="join duplicate fields together with given string",
    )

    args = ap.parse_args()

    fields = args.field_list or fields
    if "PPN" not in fields:
        fields.insert(0, "PPN")
    field_set = set(fields)

    if args.freq_sort:

        @core.file_processor(set)
        def get_ids(f_set, line):
            id_ = line.partition(" ")[0]
            if id_ in field_set:
                f_set.add(id_)

        with open(args.file) as file:
            field_count = collections.Counter()
            for _, id_set in get_ids(file):
                field_count.update(id_set)
        fields = ["PPN"] + [f for f, _ in field_count.most_common()]

    file = open(args.file)
    print("\t".join(fields))

    if args.join_multi:
        for ppn, record in core.file2dicts(file):
            record["PPN"] = [ppn]
            field_list = []
            for field in fields:
                field_list.append(args.join_multi.join(record.get(field, [])))
            print("\t".join(field_list))

    else:
        for ppn, record in core.file2dicts(file):
            record["PPN"] = [ppn]
            record = {k: record.get(k, []) for k in fields}
            # make enough lines for when there are multiples of a single ID
            for i in range(len(max(record.values(), key=len))):
                field_list = []
                for field in fields:
                    try:
                        field_list.append(record[field][i])
                    except IndexError:
                        field_list.append("")
                print("\t".join(field_list))
