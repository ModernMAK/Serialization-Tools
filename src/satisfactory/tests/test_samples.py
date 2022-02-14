import os
from os.path import splitext, join
from satisfactory.save import CompressedSave


def debug_test_samples():
    sample_root = r"../../../sample"
    for root, folder, files in os.walk(sample_root):
        for file in files:
            full_file = join(root, file)
            if splitext(full_file)[1] != ".sav":
                continue
            with open(full_file, "rb") as handle:
                cmp_save = CompressedSave.unpack(handle)
                dcmp_save = cmp_save.decompress()


if __name__ == '__main__':
    debug_test_samples()
