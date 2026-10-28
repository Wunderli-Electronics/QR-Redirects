#!/usr/bin/env python3
"""Build short redirects and downloadable QR images for a static manuals site."""
import argparse
from html import escape
import json
from pathlib import Path
import posixpath
import re
import unicodedata
from urllib.parse import quote, unquote, urlsplit

import segno

ROOT = Path(__file__).resolve().parents[1]


def https_url(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username
            or parts.password or any(ord(c) < 32 for c in url)):
        raise ValueError('target must be an HTTPS address without credentials')
    return parts


def short_name(stem):
    stem = re.sub(r'^kundenanleitung[_ -]+', '', stem, flags=re.IGNORECASE)
    for source, target in [('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')]:
        stem = stem.lower().replace(source, target)
    stem = unicodedata.normalize('NFKD', stem).encode('ascii', 'ignore').decode()
    slug = re.sub(r'[^a-z0-9]+', '-', stem).strip('-')
    if not slug:
        raise ValueError('filename needs a readable product name')
    return slug


def local_pdf(root, target):
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or parts.query or parts.fragment or target.startswith('/'):
        raise ValueError(f'local target must be a repository-relative PDF path: {target}')
    file = root / unquote(parts.path)
    if not file.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'target outside repository: {target}')
    if not file.is_file() or file.suffix.lower() != '.pdf':
        raise ValueError(f'missing PDF target: {target}')
    return file


def routes(root):
    result = {}
    for pdf in sorted(root.glob('*/pdf/*')):
        if not pdf.is_file() or pdf.suffix.lower() != '.pdf':
            continue
        if not pdf.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'PDF points outside repository: {pdf}')
        route = f'{pdf.parent.parent.name}/{short_name(pdf.stem)}'
        if route in result:
            raise ValueError(f'duplicate short address: {route}')
        result[route] = quote(pdf.relative_to(root).as_posix(), safe='/')
    config = root / 'redirects.json'
    if config.exists():
        def unique(pairs):
            values = {}
            for key, value in pairs:
                if key in values:
                    raise ValueError(f'duplicate short address in redirects.json: {key}')
                values[key] = value
            return values
        overrides = json.loads(config.read_text(encoding='utf-8'), object_pairs_hook=unique)
        if not isinstance(overrides, dict):
            raise ValueError('redirects.json must map short addresses to targets')
        result.update(overrides)
    if not result:
        raise ValueError('no manuals or redirects found')
    for route, target in result.items():
        if not re.fullmatch(r'[a-z0-9_-]+/[a-z0-9]+(?:-[a-z0-9]+)*', route):
            raise ValueError(f'invalid short address: {route}')
        if not isinstance(target, str):
            raise ValueError(f'invalid target for {route}')
        if urlsplit(target).scheme or urlsplit(target).netloc:
            https_url(target)
        else:
            local_pdf(root, target)
    return dict(sorted(result.items()))


def redirect_html(route, target):
    if urlsplit(target).scheme:
        href = target
    else:
        # Relative links also work below a GitHub project Pages prefix.
        href = quote(posixpath.relpath(unquote(target), posixpath.dirname(route)), safe='/')
    href = escape(href, quote=True)
    return (f'<!DOCTYPE html>\n<html lang="de">\n<head>\n'
            '<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta http-equiv="refresh" content="0; url={href}">\n'
            '<title>Anleitung öffnen</title>\n</head>\n<body>\n'
            f'<p><a href="{href}">Anleitung öffnen</a></p>\n</body>\n</html>\n')


def generate(root, output, base_url, write_pages=False):
    parts = https_url(base_url)
    if parts.query or parts.fragment:
        raise ValueError('base URL must not contain a query or fragment')
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError('QR output must be outside the source repository')
    mapping = routes(root)
    if write_pages:
        for route, target in mapping.items():
            page = root / (route + '.html')
            if not page.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'redirect page outside repository: {route}')
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(redirect_html(route, target), encoding='utf-8')
    rows = ['SHORT_URL\tTARGET\tPNG\tSVG']
    for route, target in mapping.items():
        url = base_url.rstrip('/') + '/' + route
        image = output / route
        image.parent.mkdir(parents=True, exist_ok=True)
        qr = segno.make_qr(url, error='m')
        for kind in ('png', 'svg'):
            qr.save(str(image) + '.' + kind, scale=12, border=4, light='white', dark='black')
        rows.append(f'{url}\t{target}\t{route}.png\t{route}.svg')
    (output / 'links.tsv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    return len(mapping)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=None)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--write-pages', action='store_true', help='Write short HTML redirects into the repository')
    args = parser.parse_args()
    base = args.base_url or 'https://' + (ROOT / 'CNAME').read_text().strip()
    print(f'Generated {generate(ROOT, args.output, base, args.write_pages)} short addresses: {base}')


if __name__ == '__main__':
    main()
