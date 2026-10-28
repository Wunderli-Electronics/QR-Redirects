# Repository guidance

- Keep the existing static GitHub Pages publication from main. Do not introduce
  a separate site export, Pages artifact deployment, OIDC or a Pages source change.
- Printed QR codes use permanent short addresses, not PDF filenames. The short
  HTML page opens the PDF in the browser reader without embedding it.
- scripts/generate_qr.py derives short addresses from */pdf/*.pdf and applies
  redirects.json overrides. --write-pages writes those HTML files into source;
  QR PNG/SVG and links.tsv go to an output directory outside the repository.
- CI tests, generates and checks. On main only, it commits changed generated HTML
  and requests the existing Pages build via POST /repos/{owner}/{repo}/pages/builds.
  A GITHUB_TOKEN commit alone does not trigger branch-based Pages publishing.
  Pull requests never push. No force pushes. No custom token is needed.
- contents: write and pages: write support that existing branch-based flow.
  The workflow is not a new deployment gate for other main changes.
- Preserve published short addresses. Before removing or renaming a PDF, pin the
  old short address to its new PDF or HTTPS website target in redirects.json.
  Generated pages are not automatically deleted. Never reuse printed addresses.
- Preserve CNAME, the original HY-Alarm PDF/path, /01/hy-alarm and its .html form.
  Preserve 01/qr_01_HY-Alarm.png byte-for-byte; it contains the printed HTTP URL.
  QR downloads are separate files and must not overwrite that artwork.
- PDF updates retain their filename. Pages/browser caches can retain old content
  or destinations briefly. Keep old destinations reachable through migration checks.
- QR tooling uses pinned Segno. Run unit tests, generate with --write-pages, then
  run scripts/check.py. No framework, server, database or external QR API.
- Fork QR downloads use the project Pages URL. Fork publishing branches must not
  contain another repository's CNAME. Source CNAME is never rewritten by the tool.
- Local Python HTTP previews need .html URLs. Use an isolated port and stop afterward.
- iOS simulator harnesses remain on fork-only test branches. Do not add them to
  this PR or rerun them for changes limited to publishing and documentation.
