"""Protect PDF-only publishing and the addresses already printed on QR codes."""
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublishingChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        shutil.copy2(ROOT / 'scripts/check.py', self.root / 'scripts/check.py')
        (self.root / '01/pdf').mkdir(parents=True)
        self.pdf = self.root / '01/pdf/manual.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\nfixture\n%%EOF\n')
        self.page = self.root / '01/manual.html'
        self.valid = ('<meta http-equiv="refresh" content="0; url=pdf/manual.pdf">'
                      '<a href="pdf/manual.pdf">Open PDF</a>')
        self.page.write_text(self.valid)

    def check(self):
        return subprocess.run([sys.executable, 'scripts/check.py'], cwd=self.root,
                              capture_output=True, text=True)

    def reject(self, message):
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_existing_alias_is_valid(self):
        self.assertEqual(self.check().returncode, 0)

    def test_new_pdf_needs_no_html_page(self):
        before = self.page.read_bytes()
        self.pdf.with_name('new-product.pdf').write_bytes(b'%PDF-1.7\nnew manual\n%%EOF\n')
        self.assertEqual(self.check().returncode, 0)
        self.assertEqual(self.page.read_bytes(), before)
        self.assertEqual(len(list(self.root.rglob('*.html'))), 1)

    def test_replacing_pdf_needs_no_other_edits(self):
        before = self.page.read_bytes()
        self.pdf.write_bytes(b'%PDF-1.7\nupdated manual\n%%EOF\n')
        self.assertEqual(self.check().returncode, 0)
        self.assertEqual(self.page.read_bytes(), before)

    def test_missing_pdf_is_rejected(self):
        self.pdf.unlink()
        self.reject('missing target')

    def test_renamed_non_pdf_is_rejected(self):
        self.pdf.write_bytes(b'This is not a PDF export')
        self.reject('no PDF header')

    def test_redirect_link_must_match(self):
        self.page.write_text(self.valid.replace('href="pdf/manual.pdf"', 'href="https://example.com"'))
        self.reject('matching visible link')

    def test_external_redirect_requires_https(self):
        self.page.write_text(self.valid.replace('pdf/manual.pdf', 'http://example.com'))
        self.reject('must use HTTPS')
        self.page.write_text(self.valid.replace('pdf/manual.pdf', 'https://example.com'))
        self.assertEqual(self.check().returncode, 0)

    def test_redirect_target_must_be_valid(self):
        self.page.write_text('<meta http-equiv="refresh" content="0">')
        self.reject('invalid refresh target')

    def test_links_cannot_escape_repository(self):
        for url in ('../../../outside.pdf', '%2e%2e/%2e%2e/outside.pdf'):
            with self.subTest(url=url):
                self.page.write_text(f'<a href="{url}">Outside</a>')
                self.reject('target outside repository')

    def test_encoded_filename_is_supported(self):
        self.pdf.rename(self.pdf.with_name('manual de.pdf'))
        self.page.write_text(self.valid.replace('manual.pdf', 'manual%20de.pdf'))
        self.assertEqual(self.check().returncode, 0)


class PrintedQRContract(unittest.TestCase):
    def test_original_printed_qr_image_is_preserved(self):
        # Existing artwork encodes http://qr.wue.ch/01/hy-alarm.
        image = (ROOT / '01/qr_01_HY-Alarm.png').read_bytes()
        self.assertEqual(hashlib.sha256(image).hexdigest(), '5d3ff2dbcd9c8cbadde6098e593ce55c23e380e47e2a24e2491a1e095a17ab45')

    def test_hy_alarm_keeps_its_existing_address_and_pdf(self):
        class Redirect(HTMLParser):
            target = None
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'meta' and attrs.get('http-equiv') == 'refresh':
                    self.target = attrs['content']
        page = ROOT / '01/hy-alarm.html'
        parsed = Redirect()
        parsed.feed(page.read_text())
        self.assertEqual(parsed.target, '0; url=pdf/Kundenanleitung_HY_Alarm.pdf')
        self.assertTrue((ROOT / '01/pdf/Kundenanleitung_HY_Alarm.pdf').is_file())


if __name__ == '__main__':
    unittest.main()
