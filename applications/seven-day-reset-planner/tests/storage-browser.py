"""Real Chromium checks; no account or external requests are required."""
import functools
import http.server
import json
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
DAILY = 'brooks-daily-planner-v2'
LEGACY = 'brooks-reset-planner-v1'
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=os.environ.get('PLANNER_TEST_DIST', str(ROOT / 'dist'))))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
results = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
        for name, options in [('desktop', {'viewport': {'width': 1440, 'height': 1000}}), ('mobile', p.devices['Pixel 7'])]:
            context = browser.new_context(**options)
            first, second = context.new_page(), context.new_page()
            first.goto(url); second.goto(url)
            first.locator('#daily-priorities').fill('Newer saved entry')
            saved = first.evaluate('(key) => localStorage.getItem(key)', DAILY)
            second.locator('#daily-priorities').fill('Stale unsaved entry')
            expect(second.locator('#daily-status')).to_contain_text('another tab')
            assert second.evaluate('(key) => localStorage.getItem(key)', DAILY) == saved
            expect(second.locator('#daily-priorities')).to_have_value('Stale unsaved entry')
            first.reload(); expect(first.locator('#daily-priorities')).to_have_value('Newer saved entry')
            first.locator('#reset-toggle').check(); second.reload()
            first.locator('#week_intention').fill('Newer worksheet')
            old_saved = first.evaluate('(key) => localStorage.getItem(key)', LEGACY)
            second.locator('#week_intention').fill('Stale worksheet')
            expect(second.locator('#status')).to_contain_text('another tab')
            assert second.evaluate('(key) => localStorage.getItem(key)', LEGACY) == old_saved
            context.close()

            context = browser.new_context(**options)
            page = context.new_page(); page.goto(url)
            page.evaluate('([key, raw]) => localStorage.setItem(key, raw)', [LEGACY, '{broken'])
            page.reload(); page.locator('#reset-toggle').check()
            page.locator('#week_intention').fill('Keep original corrupt file')
            expect(page.locator('#status')).to_contain_text('preserved')
            assert page.evaluate('(key) => localStorage.getItem(key)', LEGACY) == '{broken'
            page.evaluate('([key, raw]) => localStorage.setItem(key, raw)', [DAILY, '{broken'])
            page.reload(); page.locator('#daily-priorities').fill('Unsaved recovery note')
            expect(page.locator('#daily-status')).to_contain_text('could not be read')
            assert page.evaluate('(key) => localStorage.getItem(key)', DAILY) == '{broken'
            context.close()

            context = browser.new_context(**options)
            context.add_init_script("const originalSet = Storage.prototype.setItem; Storage.prototype.setItem = function(key, value) { if(key === 'brooks-daily-planner-v2') throw new DOMException('Full','QuotaExceededError'); return originalSet.call(this,key,value); };")
            page = context.new_page(); page.goto(url)
            page.locator('#daily-priorities').fill('Export me before closing')
            expect(page.locator('#daily-status')).to_contain_text('Unable to save')
            assert page.evaluate('(key) => localStorage.getItem(key)', DAILY) is None
            expect(page.locator('#daily-priorities')).to_have_value('Export me before closing')
            context.close()
            results.append({'profile': name, 'checks': ['daily stale-tab rejection', 'daily reload persistence', 'worksheet stale-tab rejection', 'corrupt worksheet preservation', 'corrupt daily preservation', 'quota feedback and memory retention'], 'passed': True})
        browser.close()
finally:
    server.shutdown(); server.server_close()
print(json.dumps(results, indent=2))
