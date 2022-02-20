_B = 1000
_iB = 1024

# For completeness, all standardized binary prefixes are present
#   I don't expect anything greater than Giga/Gibi to be used

B = 1

KB = _B
KiB = _iB

MB = _B ** 2
MiB = _iB ** 2

GB = _B ** 3
GiB = _iB ** 3

TB = _B ** 4
TiB = _iB ** 4

PB = _B ** 5
PiB = _iB ** 5

EB = _B ** 6
EiB = _iB ** 6

ZB = _B ** 7
ZiB = _iB ** 7

YB = _B ** 8
YiB = _iB ** 8

BinarySI = (B, KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB)
SI = (B, KB, MB, GB, TB, PB, EB, ZB, YB)
SI_Power = (0, 1, 2, 3, 4, 5, 6, 7, 8)

