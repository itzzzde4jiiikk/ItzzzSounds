import unittest
from itzzzsounds.lyrics.parser import LyricTrack, LyricLine


class TestLyricParser(unittest.TestCase):
    def test_basic_parsing(self):
        sample = """
        [ti:Test Title]
        [ar:Test Artist]
        [00:05.50]Line One
        [00:10.00]Line Two
        [00:15.25]Line Three
        """
        track = LyricTrack(sample)
        self.assertTrue(track.is_synced)
        self.assertEqual(len(track.lines), 3)
        self.assertEqual(track.lines[0].timestamp, 5.5)
        self.assertEqual(track.lines[0].text, "Line One")

    def test_time_lookup(self):
        sample = """
        [00:00.00]Intro
        [00:10.00]First Verse
        [00:20.00]Chorus
        """
        track = LyricTrack(sample)
        
        # At 5s: Intro
        curr, nxt, left = track.get_current_line(5.0)
        self.assertIsNotNone(curr)
        self.assertEqual(curr.text, "Intro")
        self.assertEqual(nxt.text, "First Verse")
        self.assertAlmostEqual(left, 5.0)

        # At 12s: First Verse
        curr, nxt, left = track.get_current_line(12.0)
        self.assertEqual(curr.text, "First Verse")
        self.assertEqual(nxt.text, "Chorus")
        self.assertAlmostEqual(left, 8.0)

        # At 25s: Chorus (no next line)
        curr, nxt, left = track.get_current_line(25.0)
        self.assertEqual(curr.text, "Chorus")
        self.assertIsNone(nxt)

    def test_instrumental_gap(self):
        sample = """
        [00:00.00]Intro
        [00:05.00]Verse 1
        [00:25.00]Verse 2
        """
        track = LyricTrack(sample)
        # At 15s: gap (20s) > 7s and elapsed (10s) > 5s -> pause detected
        curr, nxt, left = track.get_current_line(15.0)
        self.assertIn("Музыкальный проигрыш", curr.text)


if __name__ == "__main__":
    unittest.main()
