
import msvcrt
import os
import struct

from shared_memory import (
    SharedMemoryRegion,
    HEADER_SIZE,
)
from order_protocol import ORDER_SIZE


class RingBuffer:
    def __init__(self, path):
        self.path = path
        self.region = SharedMemoryRegion.open_existing(path)

        self.lock_path = path + ".lock"
        self.lock_file = open(self.lock_path, "a+b")

        # Ensure the lock file has at least one byte.
        self.lock_file.seek(0, os.SEEK_END)

        if self.lock_file.tell() == 0:
            self.lock_file.write(b"\0")
            self.lock_file.flush()

    def _acquire_lock(self):
        self.lock_file.seek(0)
        msvcrt.locking(
            self.lock_file.fileno(),
            msvcrt.LK_LOCK,
            1
        )

    def _release_lock(self):
        self.lock_file.seek(0)
        msvcrt.locking(
            self.lock_file.fileno(),
            msvcrt.LK_UNLCK,
            1
        )

    def _read_header_unlocked(self):
        data = self.region.memory_map[:HEADER_SIZE]

        magic, version, capacity, read_seq, write_seq = (
            struct.unpack("<8sIIQQ", data)
        )

        return {
            "magic": magic,
            "version": version,
            "capacity": capacity,
            "read_seq": read_seq,
            "write_seq": write_seq,
        }

    def get_header(self):
        self._acquire_lock()

        try:
            return self._read_header_unlocked()
        finally:
            self._release_lock()

    def slot_offset(self, sequence):
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise TypeError("Sequence must be an integer.")

        if sequence < 0:
            raise ValueError("Sequence cannot be negative.")

        slot = sequence % self.region.capacity

        return HEADER_SIZE + slot * ORDER_SIZE

    def close(self):
        self.lock_file.close()
        self.region.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if __name__ == "__main__":
    path = "chronosmatch_shared.bin"

    try:
        with SharedMemoryRegion.create(path, capacity=4):
            pass

        with RingBuffer(path) as buffer:
            print("Ring buffer initialized.")
            print("Header:", buffer.get_header())

            for sequence in range(8):
                print(
                    "Sequence:", sequence,
                    "Slot offset:", buffer.slot_offset(sequence)
                )

    finally:
        if os.path.exists(path):
            os.remove(path)

        if os.path.exists(path + ".lock"):
            os.remove(path + ".lock")
