# TRAVELS

Minimal travel gallery for GitHub Pages. No build tools required.

## Add a trip

1. Create a new folder, e.g. `photos/japan-2027/`.
2. Add your optimized images (`01.webp`, `02.webp`, etc.).
3. Add an album entry in `albums.json` with a unique `id`, `title`, `year`, `cover` and ordered `photos` list.
4. Run `python scripts/generate_covers.py` to generate cover thumbnails and update `coverThumbnail` in `albums.json`.
5. Commit the photos, thumbnails and `albums.json`, then push. GitHub Pages will publish the update.

To change a cover, update the album's `cover` path and rerun the thumbnail command. It creates an image up to 800px on its longest side, gives it a content-based filename to refresh browser caches, and removes outdated generated thumbnails. Full-size photos and their viewing order stay unchanged. Albums without `coverThumbnail` fall back to `cover`.

The gallery defaults to newest year first (YEAR ↓). Click the YEAR button to toggle to oldest year first (YEAR ↑); albums with the same year retain their JSON order in both directions. Changing sort order returns to page one.

The interface fits the viewport without page scrolling. Desktop pages show up to six albums (three columns, two rows), tablets up to four, and portrait phones up to two. Short windows use one row. Sparse collections are centered, and the last page keeps the same card sizes and empty slots.

Use the bottom arrows, keyboard left/right arrows, or horizontal swipes to change album pages. Open an album to view full, uncropped photos; Escape or the back button returns to its album page. Covers use a consistent 3:2 crop. Resizing preserves the current album in view.

## Preview locally

Because the site loads `albums.json` via `fetch`, opening `index.html` with `file://` is not supported.

Run from this folder:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/`.

## Deploy

GitHub Pages serves the repository root from `main`. Configure **Settings → Pages → Deploy from a branch → main / (root)**. The generated thumbnails are committed, so deployment needs no build step.

The site is published at `https://se-josh.github.io/travel/`.

## Development checks

Serving the site only needs Python. To regenerate thumbnails or run browser tests, use Python 3.12+ and install the development dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

The tests can also use an existing system `chromium`. Run from the repository root:

```bash
python scripts/generate_covers.py --check
python -m unittest discover -s tests -v
```

The browser tests exercise slow image loading, rapid navigation, returning to another album, and failed-image retries. They read album paths and photo counts from `albums.json`.

## Notes

- On iPhone, open the site in Safari, choose **Share → Add to Home Screen**, and use **Open as Web App** if that option appears. The home screen name is TRAVELS; the icon is a flat illustration of the Palo Alto clock tower. The gallery still loads its content over the network.
- If a previously added home screen icon stays cached, remove that shortcut and add it again after the site updates.
- Icon assets live in `assets/icons/`, including the 1024px master, an opaque 180px Apple touch icon, 192px/512px manifest icons and a 32px favicon. Keep icon URLs relative so they work under GitHub Pages' `/travel/` path; the OS applies the home screen corner mask.
- Images are separate files, not embedded in HTML.
- Keep album `id` values unique, use relative paths, and preserve JSON syntax.

## Typography and location labels

Album names and the TRAVELS heading use Fraunces; controls, country codes and years use DM Sans. WOFF2 fonts are served locally from `assets/fonts/`, with their SIL Open Font License files included. Font loading uses `swap` and Georgia / Arial fallbacks. Latin, extended Latin and Fraunces Vietnamese subsets are included; other scripts fall back to available system fonts.

Optional album fields `city` and `countryCode` enable compact labels such as `Los Angeles · US`. Use a two-letter ISO country code (for example `US`, `JP`, `TW`); lowercase is normalized. A region name may be used for trips spanning multiple cities. If `city` is missing or empty, the existing `title` is displayed. If the country code is missing or not two letters, the separator and code are omitted. Existing locations are never inferred from photos or generic album titles.

Example fields to add to an album (replace with the actual location):

```json
"city": "Los Angeles",
"countryCode": "US"
```
