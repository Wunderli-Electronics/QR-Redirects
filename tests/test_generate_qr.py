"""Protect printed short URLs across PDF uploads, updates and website migrations."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('generate_qr', Path(__file__).resolve().parents[1] / 'scripts/generate_qr.py')
qr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qr)


class QRPublishing(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.output = Path(self.temp.name) / 'download'
        self.site = self.root
        self.manual = self.root / '01/pdf/Kundenanleitung_Produkt1.pdf'
        self.manual.parent.mkdir(parents=True)
        self.manual.write_bytes(b'%PDF-1.4\nfirst version')
        (self.root / 'CNAME').write_text('qr.wue.ch')

    def mapping(self, value):
        (self.root / 'redirects.json').write_text(json.dumps(value))

    def images(self):
        return {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*')
                if p.suffix in ('.png', '.svg')}

    def test_upload_generates_short_redirect_and_both_qr_formats(self):
        self.assertEqual(qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True), 1)
        manifest = (self.output / 'links.tsv').read_text()
        self.assertIn('https://qr.wue.ch/01/produkt1\t', manifest)
        self.assertIn('01/pdf/Kundenanleitung_Produkt1.pdf', manifest)
        html = (self.site / '01/produkt1.html').read_text()
        self.assertIn('0; url=pdf/Kundenanleitung_Produkt1.pdf', html)
        self.assertIn('<a href="pdf/Kundenanleitung_Produkt1.pdf">', html)
        self.assertNotIn('<iframe', html)
        self.assertTrue((self.output / '01/produkt1.png').read_bytes().startswith(b'\x89PNG'))
        self.assertIn('<svg', (self.output / '01/produkt1.svg').read_text())
        self.assertEqual(self.manual.read_bytes(), (self.site / '01/pdf/Kundenanleitung_Produkt1.pdf').read_bytes())
        self.assertTrue((self.root / '01/produkt1.html').exists())

    def test_unicode_and_spaces_get_safe_short_name_and_encoded_target(self):
        self.manual.rename(self.manual.with_name('Kundenanleitung_Küche #1.pdf'))
        qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True)
        html = (self.site / '01/kueche-1.html').read_text()
        self.assertIn('pdf/Kundenanleitung_K%C3%BCche%20%231.pdf', html)

    def test_preview_uses_project_prefix_without_changing_source_domain(self):
        qr.generate(self.root, self.output, 'https://paul1404.github.io/QR-Redirects/', write_pages=True)
        self.assertIn('https://paul1404.github.io/QR-Redirects/01/produkt1', (self.output / 'links.tsv').read_text())
        self.assertEqual((self.root / 'CNAME').read_text(), 'qr.wue.ch')
        self.assertIn('url=pdf/', (self.site / '01/produkt1.html').read_text())

    def test_production_keeps_custom_domain(self):
        qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True)
        self.assertEqual((self.site / 'CNAME').read_text(), 'qr.wue.ch')

    def test_replacing_pdf_keeps_qr_identical(self):
        qr.generate(self.root, self.output, 'https://qr.wue.ch')
        before = self.images()
        self.manual.write_bytes(b'%PDF-1.7\nreplacement')
        qr.generate(self.root, self.output, 'https://qr.wue.ch')
        self.assertEqual(before, self.images())

    def test_moving_to_company_website_keeps_qr_identical(self):
        qr.generate(self.root, self.output, 'https://qr.wue.ch')
        before = self.images()
        self.mapping({'01/produkt1': 'https://wue.ch/anleitungen/produkt1?lang=de&v=2'})
        qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True)
        self.assertEqual(before, self.images())
        html = (self.site / '01/produkt1.html').read_text()
        self.assertIn('https://wue.ch/anleitungen/produkt1?lang=de&amp;v=2', html)
        self.assertNotIn('url=pdf/', html)

    def test_explicit_alias_survives_removing_migrated_pdf(self):
        self.mapping({'01/produkt1': 'https://wue.ch/anleitungen/produkt1'})
        self.manual.unlink()
        qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True)
        self.assertTrue((self.site / '01/produkt1.html').is_file())

    def test_explicit_old_short_name_can_point_to_a_renamed_pdf(self):
        self.manual.rename(self.manual.with_name('neuer-name.pdf'))
        self.mapping({'01/produkt1': '01/pdf/neuer-name.pdf'})
        qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True)
        self.assertIn('url=pdf/neuer-name.pdf', (self.site / '01/produkt1.html').read_text())

    def test_same_filename_in_different_product_folders_does_not_collide(self):
        second = self.root / '02/pdf' / self.manual.name
        second.parent.mkdir(parents=True)
        second.write_bytes(self.manual.read_bytes())
        self.assertEqual(qr.generate(self.root, self.output, 'https://qr.wue.ch'), 2)
        self.assertEqual(len(list(self.output.rglob('*.png'))), 2)

    def test_slug_collision_fails_instead_of_reassigning_printed_address(self):
        self.manual.with_name('produkt1.pdf').write_bytes(self.manual.read_bytes())
        with self.assertRaisesRegex(ValueError, 'duplicate short address'):
            qr.generate(self.root, self.output, 'https://qr.wue.ch')

    def test_invalid_base_addresses_are_rejected(self):
        for base in ('http://example.com', 'https://example.com/?x=1', 'https://example.com/#foo', 'https://user:pass@example.com', 'https:///missing-host'):
            with self.subTest(base=base), self.assertRaises(ValueError):
                qr.generate(self.root, self.output, base)

    def test_invalid_redirect_targets_and_paths_are_rejected(self):
        for route, target in [('01/produkt1', 'http://wue.ch/manual'), ('01/produkt1', 'https://user:password@wue.ch/manual'), ('../escape', 'https://wue.ch/manual'), ('01/produkt1', '../outside.pdf'), ('01/produkt1', '01/pdf/missing.pdf'), ('01/produkt1', 12), ('01/produkt1', 'https://wue.ch/\nmanual')]:
            with self.subTest(route=route, target=target), self.assertRaises(ValueError):
                self.mapping({route: target})
                qr.generate(self.root, self.output, 'https://qr.wue.ch')

    def test_duplicate_config_keys_are_rejected(self):
        (self.root / 'redirects.json').write_text('{"01/produkt1":"https://wue.ch/a","01/produkt1":"https://wue.ch/b"}')
        with self.assertRaisesRegex(ValueError, 'duplicate short address'):
            qr.generate(self.root, self.output, 'https://qr.wue.ch')

    def test_non_mapping_config_is_rejected(self):
        self.mapping([])
        with self.assertRaisesRegex(ValueError, 'must map'):
            qr.generate(self.root, self.output, 'https://qr.wue.ch')

    def test_no_manuals_or_redirects_is_an_error(self):
        self.manual.unlink()
        with self.assertRaisesRegex(ValueError, 'no manuals'):
            qr.generate(self.root, self.output, 'https://qr.wue.ch')

    def test_source_tree_is_not_an_output_directory(self):
        with self.assertRaisesRegex(ValueError, 'outside the source'):
            qr.generate(self.root, self.root / 'downloads', 'https://qr.wue.ch')

    def test_qr_only_mode_does_not_change_source_files(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        qr.generate(self.root, self.output, 'https://qr.wue.ch')
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_generated_pages_pass_static_checker(self):
        qr.generate(self.root, self.output, 'https://qr.wue.ch', write_pages=True)
        checker = Path(__file__).resolve().parents[1] / 'scripts/check.py'
        result = subprocess.run([sys.executable, str(checker), '--root', str(self.site)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
