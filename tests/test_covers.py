from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from scripts.generate_covers import generate


class CoverTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'photos').mkdir()
        self.source = self.root / 'photos/01.webp'
        Image.new('RGB', (1800, 1200), '#b89a70').save(self.source)
        self.data = {'albums': [{'id': 'trip-2026', 'title': 'TRIP', 'year': '2026',
                                 'cover': 'photos/01.webp', 'photos': ['photos/01.webp']}]}
        (self.root / 'albums.json').write_text(json.dumps(self.data, indent=2) + '\n')

    def run_generator(self, check=False):
        with redirect_stdout(StringIO()):
            generate(self.root, check=check)

    def manifest(self):
        return json.loads((self.root / 'albums.json').read_text())

    def test_generation_preserves_originals_and_is_repeatable(self):
        original = self.source.read_bytes()
        self.run_generator()
        data = self.manifest()
        thumbnail = self.root / data['albums'][0].pop('coverThumbnail')
        self.assertEqual(data, self.data)
        self.assertEqual(self.source.read_bytes(), original)
        with Image.open(thumbnail) as image:
            self.assertEqual(image.width, 800)
            self.assertLessEqual(image.height, 800)
            image.verify()
        snapshot = {p.relative_to(self.root): p.read_bytes()
                    for p in self.root.rglob('*') if p.is_file()}
        self.run_generator()
        self.run_generator(check=True)
        self.assertEqual(snapshot, {p.relative_to(self.root): p.read_bytes()
                                   for p in self.root.rglob('*') if p.is_file()})

    def test_changing_cover_refreshes_url_and_removes_only_stale_thumbnails(self):
        self.run_generator()
        previous = self.root / self.manifest()['albums'][0]['coverThumbnail']
        note = self.root / 'assets/covers/notes.txt'
        note.write_text('Keep this local file')
        Image.new('RGB', (1800, 1200), '#315c8c').save(self.root / 'photos/02.webp')
        data = self.manifest()
        data['albums'][0]['cover'] = 'photos/02.webp'
        (self.root / 'albums.json').write_text(json.dumps(data, indent=2) + '\n')
        with self.assertRaises(SystemExit):
            self.run_generator(check=True)
        self.assertTrue(previous.exists())
        self.run_generator()
        self.assertFalse(previous.exists())
        self.assertTrue((self.root / self.manifest()['albums'][0]['coverThumbnail']).is_file())
        self.assertTrue(self.source.exists())
        self.assertEqual(note.read_text(), 'Keep this local file')
        self.run_generator(check=True)

    def test_missing_thumbnail_is_detected_without_writing(self):
        with self.assertRaises(SystemExit):
            self.run_generator(check=True)
        self.assertFalse((self.root / 'assets').exists())
        self.assertEqual(self.manifest(), self.data)


if __name__ == '__main__':
    unittest.main()
