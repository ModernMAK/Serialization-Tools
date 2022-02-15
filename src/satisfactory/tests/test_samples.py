import os
from os.path import splitext, join
from pathlib import PurePath
from satisfactory.main import run

from satisfactory.save import CompressedSave

sample_root = PurePath(r"../../../sample")
update_5 = sample_root / "Update 5"
update_4 = sample_root / "Update 4"


def debug_test_samples(src: str):
    for root, folder, files in os.walk(src):
        for file in files:
            full_file = join(root, file)
            if splitext(full_file)[1] != ".sav":
                continue
            run(full_file, full_file + ".dump", redump=False, dump_json=False)


if __name__ == '__main__':
    debug_test_samples(update_4)
