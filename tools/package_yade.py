"""Replace BOOT.ELF in a pinned YADE 3.02J ISO without relocating any sector.

Requires pycdlib (packaging dependency only). Input ELF must be stripped and
linked outside YADE's staging buffer; ordinary ELF linked at 1 MiB is rejected.
"""
import argparse
import hashlib
import io
from pathlib import Path
import struct

BASE_SHA256 = 'c62bd4b5bd42b6cb9200400adcc43385c5baf85a127dc981ef45eb716ff413aa'
BOOT_SECTOR, BOOT_CAPACITY = 516, 496052
SECTOR = 2048


def package(base_path, elf_path, output_path):
    import pycdlib
    base, elf = Path(base_path).read_bytes(), Path(elf_path).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA256:
        raise ValueError('expected official YADE v1.0.7 exploit_3.02J.iso')
    if not 52 <= len(elf) <= BOOT_CAPACITY or elf[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('ELF32 little-endian payload size/header')
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', elf)
    _, etype, machine, version, entry, phoff, _, _, ehsize, phsize, phnum, *_ = header
    if (etype, machine, version, ehsize, phsize) != (2, 8, 1, 52, 32):
        raise ValueError('expected executable MIPS ELF32')
    if not 0 < phnum <= 256 or phoff + phnum * 32 > len(elf):
        raise ValueError('program header bounds')
    executable_entry = False
    for i in range(phnum):
        ptype, off, addr, _, filesz, memsz, flags, _ = struct.unpack_from('<8I', elf, phoff+i*32)
        if ptype != 1:
            continue
        # Preserve staging area (1 MiB + 243 sectors), DVD helper functions
        # near 2.5 MiB, and YADE loader at 0x01ffe800.
        if not 0x00300000 <= addr < 0x01ffe800 or memsz > 0x01ffe800-addr:
            raise ValueError('LOAD overlaps staging/DVD helper/YADE loader memory')
        if filesz > memsz or off + filesz > len(elf):
            raise ValueError('LOAD file bounds')
        if flags & 1 and addr <= entry < addr + memsz:
            executable_entry = True
    if not executable_entry:
        raise ValueError('entry not inside executable LOAD')
    iso = pycdlib.PyCdlib()
    iso.open_fp(io.BytesIO(base))
    try:
        record = iso.get_record(iso_path='/BOOT.ELF;1')
        if (record.extent_location(), record.data_length) != (BOOT_SECTOR, BOOT_CAPACITY):
            raise ValueError('unexpected BOOT extent')
    finally:
        iso.close()
    start, end = BOOT_SECTOR*SECTOR, BOOT_SECTOR*SECTOR+BOOT_CAPACITY
    result = base[:start] + elf.ljust(BOOT_CAPACITY, b'\0') + base[end:]
    # Independently extract via the filesystem to verify the replacement.
    iso = pycdlib.PyCdlib()
    iso.open_fp(io.BytesIO(result))
    try:
        extracted = io.BytesIO()
        iso.get_file_from_iso_fp(extracted, iso_path='/BOOT.ELF;1')
        assert extracted.getvalue() == elf.ljust(BOOT_CAPACITY, b'\0')
    finally:
        iso.close()
    assert len(result) == len(base) and result[:start] == base[:start] and result[end:] == base[end:]
    with Path(output_path).open('xb') as stream:
        stream.write(result)
    return hashlib.sha256(result).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_iso', type=Path)
    parser.add_argument('payload_elf', type=Path)
    parser.add_argument('output_iso', type=Path)
    args = parser.parse_args()
    print(package(args.base_iso, args.payload_elf, args.output_iso))
