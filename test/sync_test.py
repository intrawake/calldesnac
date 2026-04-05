import unittest
import sys
import os

# Add src to path if needed, but here it is in the root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from calldesnac import parse_raw_id


class TestSync(unittest.TestCase):
    def test_parse_raw_id(self):
        self.assertEqual(parse_raw_id("<custom_token_10>"), 0)
        self.assertEqual(parse_raw_id(" <custom_token_11> "), 1)
        self.assertEqual(parse_raw_id("<custom_token_4106>"), 4096)
        self.assertIsNone(parse_raw_id("not a token"))

    def test_frame_logic_mock(self):
        # Simulation of the frame logic in main
        raw_ids = [0, 4096, 8192, 12288, 16384, 20480, 24576, 1, 4097]

        c0, c1, c2 = [], [], []
        current_frame = [0] * 7
        last_p = -1
        frame_count = 0

        for v in raw_ids:
            p = v // 4096
            val = v % 4096
            if p <= last_p:
                c0.append(current_frame[0])
                c1.extend([current_frame[1], current_frame[4]])
                c2.extend([current_frame[2], current_frame[3], current_frame[5], current_frame[6]])
                current_frame = [0] * 7
                frame_count += 1
            current_frame[p] = val
            last_p = p

        if any(x != 0 for x in current_frame):
            c0.append(current_frame[0])
            c1.extend([current_frame[1], current_frame[4]])
            c2.extend([current_frame[2], current_frame[3], current_frame[5], current_frame[6]])
            frame_count += 1

        self.assertEqual(frame_count, 2)
        self.assertEqual(c0, [0, 1])
        # Frame 1: p0=0, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0 (from 0, 4096, ...)
        # Wait, raw_ids [0, 4096, 8192, 12288, 16384, 20480, 24576]
        # map to positions [0, 1, 2, 3, 4, 5, 6] all with value 0.
        # Then raw_id 1 is p=0, value 1. p(0) <= last_p(6) is true. New frame.
        self.assertEqual(len(c0), 2)
        self.assertEqual(len(c1), 4)
        self.assertEqual(len(c2), 8)


if __name__ == "__main__":
    unittest.main()
