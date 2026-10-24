"""Run: python -m unittest discover -s tests -v

Requires Python Playwright and Chromium (system chromium or Playwright's browser).
"""
import asyncio
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
from threading import Thread
import unittest

from playwright.async_api import async_playwright, expect


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PhotoNavigationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        albums = json.loads((root / 'albums.json').read_text())['albums']
        cls.primary = next(album for album in albums if len(album['photos']) >= 4)
        cls.secondary = next(album for album in albums if album['id'] != cls.primary['id'])
        cls.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        executable = shutil.which('chromium')
        self.browser = await self.playwright.chromium.launch(
            **({'executable_path': executable} if executable else {}))

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def open_album(self, page):
        await page.goto(self.base + '/#' + self.primary['id'])
        await expect(page.locator('#count')).to_have_text(self.counter(1))
        await page.wait_for_function(
            'document.querySelector("#photo").complete && document.querySelector("#photo").naturalWidth > 0')

    def photo_path(self, number):
        return self.primary['photos'][number - 1]

    def counter(self, number, album=None):
        return f"{number:02} / {len((album or self.primary)['photos']):02}"

    async def test_slow_image_stays_visible_until_decoded(self):
        for viewport in ({'width': 1280, 'height': 800}, {'width': 390, 'height': 844}):
            for motion in ('no-preference', 'reduce'):
                with self.subTest(viewport=viewport, motion=motion):
                    page = await self.browser.new_page(viewport=viewport, reduced_motion=motion)
                    release = asyncio.Event()

                    async def hold(route):
                        await release.wait()
                        await route.continue_()

                    await page.route('**/' + self.photo_path(2), hold)
                    await self.open_album(page)
                    await page.locator('#next').click()
                    # Exceeds both the old 160 ms timer and the CSS fade duration.
                    await page.wait_for_timeout(650)
                    state = await page.locator('#photo').evaluate(
                        "el => ({src: el.getAttribute('src'), opacity: getComputedStyle(el).opacity, complete: el.complete})")
                    self.assertEqual(state['src'], self.photo_path(1))
                    self.assertEqual(state['opacity'], '1')
                    self.assertTrue(state['complete'])
                    await expect(page.locator('#count')).to_have_text(self.counter(1))
                    # Catch a premature reveal even within a single animation frame.
                    await page.evaluate('(path) => { window.pendingPhotoPath = path; }', self.photo_path(2))
                    await page.evaluate("""() => {
                        window.badFrames = [];
                        window.checkFrames = true;
                        function sample() {
                            const img = document.querySelector('#photo');
                            if (img.getAttribute('src') === window.pendingPhotoPath &&
                                (!img.complete || !img.naturalWidth)) window.badFrames.push('unready');
                            if (window.checkFrames) requestAnimationFrame(sample);
                        }
                        requestAnimationFrame(sample);
                    }""")
                    release.set()
                    await expect(page.locator('#count')).to_have_text(self.counter(2))
                    await expect(page.locator('#photo')).to_have_css('opacity', '1')
                    self.assertEqual(await page.evaluate('window.checkFrames = false; window.badFrames'), [])
                    await page.close()

    async def test_latest_navigation_wins_and_back_cancels_pending_load(self):
        page = await self.browser.new_page()
        release = asyncio.Event()

        async def hold(route):
            await release.wait()
            await route.continue_()

        await page.route('**/' + self.photo_path(2), hold)
        await self.open_album(page)
        await page.locator('#next').click()
        await page.keyboard.press('ArrowRight')
        await expect(page.locator('#count')).to_have_text(self.counter(3))
        release.set()
        await page.wait_for_timeout(500)
        await expect(page.locator('#photo')).to_have_attribute('src', self.photo_path(3))
        await expect(page.locator('#photo')).to_have_css('opacity', '1')
        # Start another delayed request, return, and open a different album.
        release.clear()
        await page.route('**/' + self.photo_path(4), hold)
        await page.locator('#next').click()
        await page.keyboard.press('Escape')
        other = page.locator(f'[data-album-id="{self.secondary["id"]}"]')
        while await other.count() == 0:
            await page.locator('#page-next').click()
        await other.click()
        await expect(page.locator('#count')).to_have_text(self.counter(1, self.secondary))
        release.set()
        await page.wait_for_timeout(500)
        await expect(page.locator('#photo')).to_have_attribute('src', self.secondary['photos'][0])
        await expect(page.locator('#photo')).to_have_css('opacity', '1')
        await page.close()

    async def test_failed_photo_keeps_current_image_and_can_retry(self):
        page = await self.browser.new_page()

        async def fail(route):
            await route.fulfill(status=404, body='missing')

        await page.route('**/' + self.photo_path(2), fail)
        await self.open_album(page)
        await page.locator('#next').click()
        await expect(page.locator('#photo-status')).to_contain_text('Could not load photo')
        await expect(page.locator('#photo')).to_have_attribute('src', self.photo_path(1))
        await expect(page.locator('#photo')).to_have_css('opacity', '1')
        await expect(page.locator('#count')).to_have_text(self.counter(1))
        await page.unroute('**/' + self.photo_path(2), fail)
        await page.locator('#next').click()
        await expect(page.locator('#count')).to_have_text(self.counter(2))
        await expect(page.locator('#photo-status')).to_be_empty()
        await page.close()


if __name__ == '__main__':
    unittest.main()
