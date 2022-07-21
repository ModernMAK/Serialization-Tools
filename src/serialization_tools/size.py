_B:int = 1000
_iB:int = 1024

# For completeness, all standardized binary prefixes are present
#   I don't expect anything greater than Giga/Gibi to be used

B:int = 1

KB:int = _B
KiB:int = _iB

MB:int = _B ** 2
MiB:int = _iB ** 2

GB:int = _B ** 3
GiB:int = _iB ** 3

TB:int = _B ** 4
TiB:int = _iB ** 4

PB:int = _B ** 5
PiB:int = _iB ** 5

EB:int = _B ** 6
EiB:int = _iB ** 6

ZB:int = _B ** 7
ZiB:int = _iB ** 7

YB:int = _B ** 8
YiB:int = _iB ** 8

BinarySI = (B, KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB)
SI = (B, KB, MB, GB, TB, PB, EB, ZB, YB)
SI_Power = (0, 1, 2, 3, 4, 5, 6, 7, 8)

