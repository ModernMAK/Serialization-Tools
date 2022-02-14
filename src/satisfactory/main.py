import dataclasses
import json
import os
import sys
from enum import Enum
from json import JSONEncoder
from os.path import splitext, basename
from pathlib import Path

from satisfactory.save import CompressedSave


def dataclass2safedict(obj):
    if dataclasses.is_dataclass(obj):
        result = []
        for f in dataclasses.fields(obj):
            value = dataclass2safedict(getattr(obj, f.name))
            result.append((f.name, value))
        return dict(result)
    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[dataclass2safedict(v) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(dataclass2safedict(v) for v in obj)
    elif isinstance(obj, dict):
        return [{"Key": dataclass2safedict(k), "Value": dataclass2safedict(v)} for k, v in obj.items()]
        # return type(obj)((dataclass2safedict(k, dict_factory),
        #                   dataclass2safedict(v, dict_factory))
        #                  for k, v in obj.items())
    else:
        return obj


class FullJsonEncoder(JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclass2safedict(o)
        elif isinstance(o, bytes):
            return o.hex(bytes_per_sep=4, sep=" ")
        elif isinstance(o, Enum):
            return o.value
        else:
            return super().default(o)


def run(infile: str, dumpfile: str = None, jsonfile: str = None, redump: bool = True):
    dumpfile = dumpfile or basename(infile) + ".bodydump"
    jsonfile = jsonfile or splitext(basename(infile))[0] + ".json"

    with open(infile, "rb") as save_reader:
        save = CompressedSave.unpack(save_reader)
        # print("Compressed:", save)
        if redump or not os.path.exists(dumpfile):
            with open(dumpfile, "w+b") as writer:
                save.decompress_body_into(writer)
                writer.seek(0)
                full_save = save.decompress_from(writer)
        else:
            with open(dumpfile, "rb") as dump_reader:
                full_save = save.decompress_from(dump_reader)

        with open(jsonfile, "w") as json_writer:
            json.dump(full_save, json_writer, cls=FullJsonEncoder, indent=4)


def get_latest_save() -> str:
    p = Path('~/Appdata/Local/FactoryGame/Saved/SaveGames').expanduser()
    if not p.exists():
        # raise FileNotFoundError()
        return None
    return list(sorted(p.glob('**/*.sav'), key=lambda f: f.stat().st_mtime, reverse=True))[0].__str__()


if __name__ == "__main__":
    save_file = (sys.argv[1] if len(sys.argv) > 1 else False) or get_latest_save()
    run(save_file, )
