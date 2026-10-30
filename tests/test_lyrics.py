import unittest
from itzzzsounds.lyrics.provider import clean_query


class TestLyricsProvider(unittest.TestCase):
    def test_clean_query(self):
        title, artist = clean_query("Кукла колдуна на Яндекс Музыке", "Король и Шут")
        self.assertEqual(title, "Кукла колдуна")
        self.assertEqual(artist, "Король и Шут")

        title, artist = clean_query("In The End (Remastered 2020)", "Linkin Park feat. Jay-Z")
        self.assertEqual(title, "In The End")
        self.assertEqual(artist, "Linkin Park")

        title, artist = clean_query("Song Name [Official Music Video]", "Artist")
        self.assertEqual(title, "Song Name")


if __name__ == "__main__":
    unittest.main()
