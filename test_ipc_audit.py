
import unittest

from ipc_audit import run_audit


class TestIPCAudit(unittest.TestCase):

    def test_small_ipc_audit(self):
        result = run_audit(
            count=5000,
            start_id=1001,
            capacity=64
        )

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
