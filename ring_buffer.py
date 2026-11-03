
import msvcrt
import os
import struct
import time

from shared_memory import SharedMemoryRegion, HEADER_SIZE
from order_protocol import ORDER_SIZE, pack_order, unpack_order


HEADER_FORMAT = "<8sIIQQ"
LOCK_RETRY_DELAY = 0.0005


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
        while True:
            try:
                self.lock_file.seek(0)

                msvcrt.locking(
                    self.lock_file.fileno(),
                    msvcrt.LK_NBLCK,
                    1
                )

                return

            except OSError:
                time.sleep(LOCK_RETRY_DELAY)

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
            "write_seq": write_seq
        }

    def _write_header_unlocked(self, header):
        packed = struct.pack(
            HEADER_FORMAT,
            header["magic"],
            header["version"],
            header["capacity"],
            header["read_seq"],
            header["write_seq"]
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
        return self.write_orders([
            (order_id, price, quantity)
        ])[0]

    def write_orders(self, orders):
        packed_orders = [
            pack_order(*order) for order in orders
        ]

        if not packed_orders:
            return []

        if len(packed_orders) > self.region.capacity:
            raise ValueError("Batch exceeds ring buffer capacity.")

        self._acquire_lock()

        try:
            header = self._read_header_unlocked()

            read_seq = header["read_seq"]
            write_seq = header["write_seq"]
            capacity = header["capacity"]

            available = capacity - (write_seq - read_seq)

            if len(packed_orders) > available:
                raise BufferError("Ring buffer is full.")

            sequences = []

            for packed_order in packed_orders:
                offset = self.slot_offset(write_seq)

                self.region.memory_map[
                    offset:offset + ORDER_SIZE
                ] = packed_order

                sequences.append(write_seq)
                write_seq += 1

            header["write_seq"] = write_seq
            self._write_header_unlocked(header)

            return sequences

        finally:
            self._release_lock()

    def read_order(self):
        orders = self.read_orders(1)

        if not orders:
            raise BufferError("Ring buffer is empty.")

        return orders[0]

    def read_orders(self, max_count):
        if not isinstance(max_count, int) or isinstance(max_count, bool):
            raise TypeError("max_count must be an integer.")

        if max_count < 0:
            raise ValueError("max_count cannot be negative.")

        if max_count == 0:
            return []

        orders = []

        self._acquire_lock()

        try:
            header = self._read_header_unlocked()

            read_seq = header["read_seq"]
            write_seq = header["write_seq"]

            available = write_seq - read_seq
            count = min(max_count, available)

            for unused in range(count):
                offset = self.slot_offset(read_seq)

                raw_order = self.region.memory_map[
                    offset:offset + ORDER_SIZE
                ]

                orders.append(unpack_order(raw_order))
                read_seq += 1

            if count:
                header["read_seq"] = read_seq
                self._write_header_unlocked(header)

            return orders

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
            buffer.write_orders([
                (1001, 12550, 10),
                (1002, 12560, 5)
            ])

            print("Batch written.")
            print("Orders read:", buffer.read_orders(2))
            print("Header:", buffer.get_header())

    finally:
        if os.path.exists(path):
            os.remove(path)

        if os.path.exists(path + ".lock"):
            os.remove(path + ".lock")
