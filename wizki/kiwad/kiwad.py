import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, List
from mmap import mmap, ACCESS_READ
from io import BytesIO


_NO_COMPRESS = frozenset(
    (
        ".mp3",
        ".ogg",
    )
)


@dataclass
class KIWadFileInfo:
    name: str
    offset: int
    size: int
    zipped_size: int
    is_zip: bool
    crc: int


class KIWad:
    # TODO: allow for `file` that doesnt exist yet
    def __init__(self, file: Union[Path, str]):
        self.file_path = Path(file)
        self.name = self.file_path.stem

        self._file_map = {}
        self._file_pointer = None
        self._mmap = None

        self._refreshed_once = False

        self._size = None

    def __repr__(self):
        return f"<KIWad {self.name=}>"

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def size(self) -> int:
        """
        Total size of this wad
        """
        if not self._file_pointer:
            self._open()

        if self._size:
            return self._size

        self._size = sum(file.size for file in self._file_map.values())
        return self._size

    def name_list(self) -> List[str]:
        """
        List of all file names in this wad
        """
        if not self._file_pointer:
            self._open()

        return list(self._file_map.keys())

    def info_list(self) -> List[KIWadFileInfo]:
        """
        List of all KIWadFileInfo in this wad
        """
        if not self._file_pointer:
            self._open()

        return list(self._file_map.values())

    def _open(self):
        if self._file_pointer:
            raise RuntimeError("This KIWad is already opened")

        # noinspection PyTypeChecker
        self._file_pointer = open(self.file_path, "rb")
        self._mmap = mmap(self._file_pointer.fileno(), 0, access=ACCESS_READ)
        self._refresh_journal()

    def open(self, file_name: str) -> BytesIO:
        data = self.read(file_name)
        return BytesIO(data)

    def close(self):
        self._file_pointer.close()
        self._file_pointer = None

    # fmt: off
    def _read(self, start: int, size: int) -> bytes:
        return self._mmap[start: start + size]
    # fmt: on

    # fmt: off
    def _refresh_journal(self):
        if self._refreshed_once:
            return

        self._refreshed_once = True

        # KIWAD id string
        file_offset = 5

        version, file_num = struct.unpack(
            "<ll", self._mmap[file_offset: file_offset + 8]
        )

        file_offset += 8

        if version >= 2:
            file_offset += 1

        for _ in range(file_num):
            # no reason to use struct.calcsize
            offset, size, zipped_size, is_zip, crc, name_length = struct.unpack(
                "<lll?ll", self._mmap[file_offset: file_offset + 21]
            )

            # 21 is the size of all the data we just read
            file_offset += 21

            name = self._mmap[file_offset: file_offset + name_length].decode()
            name = name.rstrip("\x00")

            file_offset += name_length

            self._file_map[name] = KIWadFileInfo(
                name, offset, size, zipped_size, is_zip, crc
            )
    # fmt: on

    def read(self, name: str) -> Optional[bytes]:
        """
        Get the data contents of the named file
        Args:
            name: name of the file to get
        Returns:
            Bytes of the file or None for "unpatched" dummy files
        """
        if not self._file_pointer:
            self._open()

        target_file = self.get_info(name)

        if target_file.is_zip:
            data = self._read(target_file.offset, target_file.zipped_size)

        else:
            data = self._read(target_file.offset, target_file.size)

        # unpatched file
        if data[:4] == b"\x00\x00\x00\x00":
            return None

        if target_file.is_zip:
            data = zlib.decompress(data)

        return data

    # # TODO: finish
    # def write(self, name: str, data: str | bytes):
    #     if isinstance(data, str):
    #         data = data.encode()

    def get_info(self, name: str) -> KIWadFileInfo:
        """
        Gets a KIWadFileInfo for a named file
        Args:
            name: name of the file to get info on
        """
        if not self._file_pointer:
            self._open()

        try:
            target_file = self._file_map[name]
        except KeyError:
            raise ValueError(f"File {name} not found.")

        return target_file

    def extract_all(self, path: Union[Path, str]):
        """
        Unarchive a wad file into a directory
        Args:
            path: source_path to the directory to unpack the wad
        """
        path = Path(path)

        if not self._file_pointer:
            self._open()

        self._extract_all(path)

    # sync thread
    def _extract_all(self, path):
        with open(self.file_path, "rb") as fp:
            with mmap(fp.fileno(), 0, access=ACCESS_READ) as mm:
                for file in self._file_map.values():
                    file_path = path / file.name
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    # fmt: off
                    if file.is_zip:
                        data = mm[file.offset: file.offset + file.zipped_size]

                    else:
                        data = mm[file.offset: file.offset + file.size]
                    # fmt: on

                    # unpatched file
                    if data[:4] == b"\x00\x00\x00\x00":
                        file_path.touch()
                        continue

                    if file.is_zip:
                        data = zlib.decompress(data)

                    file_path.write_bytes(data)

    def insert_all(
        self,
        source_path: Union[Path, str],
        *,
        overwrite: bool = False,
    ):
        source_path = Path(source_path)
        output_path = Path(self.file_path)

        if not source_path.is_dir():
            if not source_path.exists():
                raise FileNotFoundError(source_path)

            raise ValueError(f"{source_path} is not a directory.")

        if not overwrite and output_path.exists():
            raise FileExistsError(f"{output_path} already exists.")

        self._insert_all(source_path, output_path)

    @staticmethod
    def _insert_all(
        source_path: Path,
        output_path: Path,
    ):
        to_write = [
            file.relative_to(source_path)
            for file in source_path.glob("**/*")
            if file.is_file()
        ]
        file_num = len(to_write)

        all_names_len = sum(len(str(file)) for file in to_write)

        # KIWAD + version + file_num + version 2 0x01 + journal header * file number
        # + file num for the null terminator
        journal_size = 14 + (21 * file_num) + all_names_len + file_num

        current_offset = journal_size
        data_blocks = []

        with open(output_path, "wb+") as fp:
            # magic bytes
            fp.write(b"KIWAD")

            fp.write(struct.pack("<ll", 2, file_num))

            # version 2 thing
            fp.write(b"\x01")

            for file in to_write:
                is_zip = file.suffix not in _NO_COMPRESS
                data = (source_path / file).read_bytes()
                crc = zlib.crc32(data)
                size = len(data)
                name = str(file)

                if is_zip:
                    compressed_data = zlib.compress(data)

                    # they still write the zipped size for optimized files
                    zipped_size = len(compressed_data)

                    # they optimize in these cases
                    if zipped_size >= len(data):
                        is_zip = False

                    else:
                        data = compressed_data
                else:
                    zipped_size = -1

                fp.write(
                    struct.pack(
                        "<lll?Ll",
                        current_offset,
                        size,
                        zipped_size,
                        is_zip,
                        crc,
                        len(name) + 1,
                    )
                )

                # only / paths are allowed
                fp.write(name.replace("\\", "/").encode() + b"\x00")

                current_offset += len(data)

                data_blocks.append(data)

            for data_block in data_blocks:
                fp.write(data_block)
