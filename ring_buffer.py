
import msvcrt
import os
import struct

from shared_memory import SharedMemoryRegion, HEADER_SIZE
from order_protocol import ORDER_SIZE, pack_order


HEADER_FORMAT = "<8sIIQQ"


class RingBuffer:
    def __init__(self, path):
        self.path = path
        self.region = SharedMemoryRegion.open_existing(path)

        self.lock_path = path + ".lock"
        self.lock_file = open(self.lock_path, "a+b")

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
        values = struct.unpack(
            HEADER_FORMAT,
            self.region.memory_map[:HEADER_SIZE]
        )

        magic, version, capacity, read_seq, write_seq = values

        return {
            "magic": magic,
            "version": version,
            "capacity": capacity,
            "read_seq": read_seq,
            "write_seq": write_seq,
        }

    def _write_header_unlocked(self, header):
        packed = struct.pack(
            HEADER_FORMAT,
            header["magic"],
            header["version"],
            header["capacity"],
            header["read_seq"],
            header["write_seq"],
        )

        self.region.memory_map[:HEADER_SIZE] = packed

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

    def write_order(self, order_id, price, quantity):
        # Validate and encode the order before modifying shared memory.
        packed_order = pack_order(order_id, price, quantity)

        self._acquire_lock()
        try:
            header = self._read_header_unlocked()

            read_seq = header["read_seq"]
            write_seq = header["write_seq"]
            capacity = header["capacity"]

            if write_seq - read_seq >= capacity:
                raise BufferError("Ring buffer is full.")

            offset = self.slot_offset(write_seq)

            # Store the order before publishing the new write sequence.
            self.region.memory_map[
                offset:offset + ORDER_SIZE
            ] = packed_order

            header["write_seq"] = write_seq + 1
            self._write_header_unlocked(header)

            return write_seq

        finally:
            self._release_lock()

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
            sequence = buffer.write_order(1001, 12550, 10)
            print("Order written at sequence:", sequence)
            print("Header after write:", buffer.get_header())

    finally:
        if os.path.exists(path):
            os.remove(path)

        if os.path.exists(path + ".lock"):
            os.remove(path + ".lock")
