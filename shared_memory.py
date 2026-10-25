
import mmap
import os
import struct
from order_protocol import ORDER_SIZE


# Shared-memory header:
# 8s = magic signature
# I  = protocol version
# I  = ring-buffer capacity
# Q  = read sequence number
# Q  = write sequence number

HEADER_FORMAT = "<8sIIQQ"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

MAGIC = b"CHRONOS1"
VERSION = 1

DEFAULT_CAPACITY = 1024



class SharedMemoryRegion:
    """Manage a file-backed mmap region for ChronosMatch."""

    def __init__(self, file_handle, memory_map, capacity):
        self.file_handle = file_handle
        self.memory_map = memory_map
        self.capacity = capacity
        self.closed = False

    @property
    def total_size(self):
        return HEADER_SIZE + self.capacity * ORDER_SIZE

    @classmethod
    def create(cls, path, capacity=DEFAULT_CAPACITY):
        """Create and initialize a new shared-memory file."""

        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError("capacity must be an integer")

        if capacity <= 0:
            raise ValueError("capacity must be positive")

        total_size = HEADER_SIZE + capacity * ORDER_SIZE

        # Exclusive creation prevents accidental overwriting
        # of an existing shared-memory file.
        file_handle = open(path, "x+b")

        try:
            file_handle.truncate(total_size)

            memory_map = mmap.mmap(
                file_handle.fileno(),
                total_size,
                access=mmap.ACCESS_WRITE
            )

            header = struct.pack(
                HEADER_FORMAT,
                MAGIC,
                VERSION,
                capacity,
                0,  # Initial read sequence
                0   # Initial write sequence
            )

            memory_map[:HEADER_SIZE] = header
            memory_map.flush()

            return cls(file_handle, memory_map, capacity)

        except Exception:
            file_handle.close()

            # Remove an incomplete file created by this call.
            try:
                os.remove(path)
            except OSError:
                pass

            raise

    @classmethod
    def open_existing(cls, path):
        """Open an existing region and validate its header."""

        file_handle = open(path, "r+b")

        try:
            file_size = os.path.getsize(path)

            if file_size < HEADER_SIZE:
                raise ValueError("Shared-memory file is too small")

            memory_map = mmap.mmap(
                file_handle.fileno(),
                file_size,
                access=mmap.ACCESS_WRITE
            )

            try:
                magic, version, capacity, read_seq, write_seq = (
                    struct.unpack(
                        HEADER_FORMAT,
                        memory_map[:HEADER_SIZE]
                    )
                )

                if magic != MAGIC:
                    raise ValueError("Invalid shared-memory signature")

                if version != VERSION:
                    raise ValueError("Unsupported protocol version")

                if capacity <= 0:
                    raise ValueError("Invalid ring-buffer capacity")

                expected_size = HEADER_SIZE + capacity * ORDER_SIZE

                if file_size != expected_size:
                    raise ValueError("Shared-memory file size mismatch")

                if read_seq > write_seq:
                    raise ValueError("Invalid sequence numbers")

                if write_seq - read_seq > capacity:
                    raise ValueError("Sequence numbers exceed capacity")

                return cls(file_handle, memory_map, capacity)

            except Exception:
                memory_map.close()
                raise

        except Exception:
            file_handle.close()
            raise

    def read_header(self):
        """Return validated header metadata."""

        if self.closed:
            raise ValueError("Shared-memory region is closed")

        magic, version, capacity, read_seq, write_seq = struct.unpack(
            HEADER_FORMAT,
            self.memory_map[:HEADER_SIZE]
        )

        if magic != MAGIC or version != VERSION:
            raise ValueError("Invalid shared-memory header")

        return {
            "magic": magic,
            "version": version,
            "capacity": capacity,
            "read_seq": read_seq,
            "write_seq": write_seq
        }

    def close(self):
        """Close the mapping and its backing file."""

        if not self.closed:
            self.memory_map.close()
            self.file_handle.close()
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if __name__ == "__main__":
    path = "chronosmatch_shared.bin"

    try:
        with SharedMemoryRegion.create(path, capacity=DEFAULT_CAPACITY) as region:
            print("Shared-memory region created.")
            print("Capacity:", region.capacity)
            print("Header size:", HEADER_SIZE, "bytes")
            print("Total size:", region.total_size, "bytes")
            print("Header:", region.read_header())
    finally:
        # Remove the demonstration file after the example finishes.
        if os.path.exists(path):
            os.remove(path)
