
import os
import tempfile
import unittest

from shared_memory import (
    HEADER_SIZE,
    MAGIC,
    VERSION,
    SharedMemoryRegion,
)


class TestSharedMemoryRegion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "test_shared.bin"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_region(self):
        with SharedMemoryRegion.create(self.path, 8) as region:
            self.assertEqual(region.capacity, 8)
            self.assertEqual(
                region.total_size,
                HEADER_SIZE + 8 * 20
            )
            self.assertTrue(os.path.exists(self.path))

    def test_initial_header(self):
        with SharedMemoryRegion.create(self.path, 8) as region:
            header = region.read_header()

            self.assertEqual(header["magic"], MAGIC)
            self.assertEqual(header["version"], VERSION)
            self.assertEqual(header["capacity"], 8)
            self.assertEqual(header["read_seq"], 0)
            self.assertEqual(header["write_seq"], 0)

    def test_open_existing_region(self):
        with SharedMemoryRegion.create(self.path, 8):
            pass

        with SharedMemoryRegion.open_existing(self.path) as region:
            self.assertEqual(region.capacity, 8)
            self.assertEqual(region.read_header()["write_seq"], 0)

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            SharedMemoryRegion.create(self.path, 0)

    def test_negative_capacity(self):
        with self.assertRaises(ValueError):
            SharedMemoryRegion.create(self.path, -1)

    def test_prevent_overwriting_existing_file(self):
        with SharedMemoryRegion.create(self.path, 8):
            with self.assertRaises(FileExistsError):
                SharedMemoryRegion.create(self.path, 4)

    def test_reject_invalid_header(self):
        with SharedMemoryRegion.create(self.path, 8) as region:
            region.memory_map[0:8] = b"BADMAGIC"
            region.memory_map.flush()

        with self.assertRaises(ValueError):
            SharedMemoryRegion.open_existing(self.path)

    def test_close_region(self):
        region = SharedMemoryRegion.create(self.path, 8)
        region.close()

        self.assertTrue(region.closed)

        with self.assertRaises(ValueError):
            region.read_header()


if __name__ == "__main__":
    unittest.main()
