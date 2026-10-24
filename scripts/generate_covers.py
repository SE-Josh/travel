"""Generate lightweight gallery covers; full-size album photos stay unchanged."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image, ImageOps


def generate(root, check=False):
    root = Path(root).resolve()
    manifest = root / 'albums.json'
    data = json.loads(manifest.read_text())
    outputs = {}
    for album in data['albums']:
        if not re.fullmatch(r'[a-z0-9-]+', album['id']):
            raise ValueError(f"Unsupported album id: {album['id']}")
        source = (root / album['cover']).resolve()
        if not source.is_relative_to(root):
            raise ValueError('Cover path must stay inside the repository')
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((800, 800), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format='WEBP', quality=82, method=6)
        content = buffer.getvalue()
        digest = sha256(content).hexdigest()[:12]
        relative = f"assets/covers/{album['id']}-{digest}.webp"
        outputs[root / relative] = content
        album['coverThumbnail'] = relative

    directory = root / 'assets/covers'
    stale = [path for path in directory.glob('*.webp')
             if re.fullmatch(r'[a-z0-9-]+-[0-9a-f]{12}\.webp', path.name)
             and path not in outputs]
    updated = json.dumps(data, indent=2) + '\n'
    if check:
        if (manifest.read_text() != updated or stale or
                any(not path.is_file() or path.read_bytes() != content
                    for path, content in outputs.items())):
            raise SystemExit('Cover thumbnails are out of date. Run python scripts/generate_covers.py')
    else:
        directory.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            if not path.is_file() or path.read_bytes() != content:
                path.write_bytes(content)
        if manifest.read_text() != updated:
            manifest.write_text(updated)
        # Only remove files following this generator's naming convention.
        for path in stale:
            path.unlink()
    print(f"{'Checked' if check else 'Generated'} {len(outputs)} covers "
          f'({sum(map(len, outputs.values())) / 1024:.0f} KiB)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify without writing files')
    args = parser.parse_args()
    generate(Path(__file__).resolve().parents[1], check=args.check)
