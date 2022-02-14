import os
from os.path import splitext, join
from ..save import CompressedSave


def debug_test_samples():
    sample_root = "../../sample"
    for root, folder, files in os.walk(sample_root):
        for file in files:
            full_file = join(root, file)
            if splitext(full_file)[1] != ".sav":
                continue
            with open(full_file, "rb") as file:
                cmp_save = CompressedSave.unpack(file)
                dcmp_save = cmp_save.decompress()


if __name__ == '__main__':
    debug_test_samples()
