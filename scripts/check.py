#!/usr/bin/env python3
"""Validate published PDFs and static links without changing any files."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def local_target(page, url):
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or not parts.path:
        return None
    path = unquote(parts.path)
    target = (ROOT / path.lstrip('/') if path.startswith('/') else page.parent / path).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError(f'target outside repository: {url}')
    return target


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.anchors, self.redirects, self.errors = [], [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.links.extend(attrs[key] for key in ('href', 'src', 'data') if attrs.get(key))
        if tag == 'a' and attrs.get('href'):
            self.anchors.append(attrs['href'])
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh':
            match = re.fullmatch(r'\s*\d+\s*;\s*url\s*=\s*(.+?)\s*', attrs.get('content') or '', re.IGNORECASE)
            if match:
                self.redirects.append(match.group(1))
                self.links.append(match.group(1))
            else:
                self.errors.append('invalid refresh target')


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    ROOT = parser.parse_args().root.resolve()
    errors, pages, pdfs = [], 0, 0
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part.startswith('.') for part in relative.parts):
            continue
        try:
            if not path.resolve().is_relative_to(ROOT):
                raise ValueError('file points outside repository')
            if path.suffix.lower() == '.pdf':
                pdfs += 1
                with path.open('rb') as file:
                    if b'%PDF-' not in file.read(1024):
                        raise ValueError('file has no PDF header')
            if path.suffix.lower() not in ('.html', '.htm'):
                continue
            pages += 1
            parsed = Page()
            parsed.feed(path.read_text(encoding='utf-8'))
            errors.extend(f'{relative}: {error}' for error in parsed.errors)
            for url in parsed.links:
                target = local_target(path, url)
                if target is not None and not target.is_file():
                    errors.append(f'{relative}: missing target: {url}')
            for url in parsed.redirects:
                parts = urlsplit(url)
                if (parts.scheme or parts.netloc) and not (parts.scheme == 'https' and parts.netloc):
                    errors.append(f'{relative}: external redirect must use HTTPS')
                if url not in parsed.anchors:
                    errors.append(f'{relative}: redirect needs a matching visible link')
        except ValueError as error:
            errors.append(f'{relative}: {error}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Checked {pdfs} PDFs and {pages} HTML pages. Files and redirect links OK.')


if __name__ == '__main__':
    main()
