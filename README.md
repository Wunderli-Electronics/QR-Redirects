# Produktanleitungen per QR-Code

## Neue Anleitung

1. PDF in `01/pdf/` hochladen, zum Beispiel `Kundenanleitung_Produkt1.pdf`.
2. Die CI erzeugt automatisch `01/produkt1.html` und den QR-Code für
   **`https://qr.wue.ch/01/produkt1`**. Die HTML-Datei wird auf `main` gespeichert.
   GitHub Pages veröffentlicht weiterhin wie bisher aus diesem Branch.
3. Unter **Actions → Check static pages → erfolgreicher Lauf → Artifacts → qr-codes**
   PNG und SVG herunterladen. Nach der Pages-Veröffentlichung scannen und prüfen,
   dann drucken. Den weißen Rand um den QR-Code erhalten.

Die kurze Adresse bleibt auf dem Gerät. Dahinter liegt zunächst die PDF und
später bei Bedarf die Anleitung auf der Firmenwebsite. Eine HTML-Vorlage muss
nicht mehr kopiert werden. Die PDF wird nicht eingebettet, sondern direkt im
Browser geöffnet.

Für die kurze Adresse entfällt der Dateianfang `Kundenanleitung_`. Buchstaben
werden klein geschrieben, Umlaute als `ae`, `oe`, `ue` ausgeschrieben und
Leerzeichen durch Bindestriche ersetzt. Doppelte kurze Adressen melden einen Fehler.

Im Fork zeigen QR-Downloads auf dessen Vorschau und sind nur zum Testen bestimmt.
`links.tsv` im Download nennt kurze Adressen und Ziele. Downloads sind 90 Tage
verfügbar und lassen sich durch einen neuen Lauf erneut erzeugen.

## Anleitung aktualisieren oder später umziehen

Eine neue PDF-Fassung **unter demselben Namen im selben Ordner ersetzen**.
Die kurze Adresse und der gedruckte QR-Code bleiben gleich.

Für den späteren Website-Umzug das Ziel in `redirects.json` ändern:

```json
{
  "01/hy-alarm": "01/pdf/Kundenanleitung_HY_Alarm.pdf",
  "01/produkt1": "https://wue.ch/anleitungen/produkt1"
}
```

Die CI aktualisiert die HTML-Weiterleitung. **Der gedruckte Code bleibt identisch.**
Externe Ziele müssen HTTPS verwenden. Lokale Ziele sind Pfade ab dem Repository-Stamm.
Ziele in dieser Datei pflegen; automatisch erzeugte HTML-Dateien werden beim
nächsten Lauf daraus aktualisiert.

Vor dem Umbenennen, Verschieben oder Entfernen einer bereits verteilten PDF die
bisherige kurze Adresse mit ihrem neuen Ziel in `redirects.json` festhalten.
Gedruckte Adressen nicht löschen oder für ein anderes Produkt wiederverwenden.

Pages und Browser können kurz noch alte PDF-Fassungen oder Weiterleitungsziele
zwischenspeichern. Beim Umzug das alte Ziel bis zur Kontrolle erreichbar lassen.

## Bereits gedruckter HY-Alarm-Code

`01/qr_01_HY-Alarm.png` bleibt unverändert. Der Inhalt ist
`http://qr.wue.ch/01/hy-alarm`. Die bestehende HTTPS-Weiterleitung sowie
`01/hy-alarm` und `01/hy-alarm.html` bleiben erhalten. Dahinter öffnet sich die
PDF im Browser. Ein zusätzlicher Link erlaubt das manuelle Öffnen.
Domain, Original-PDF und PDF-Pfad werden nicht geändert.

## Bestehende Veröffentlichung bleibt bestehen

**Keine Änderung der Pages-Einstellungen erforderlich.** Quelle bleibt `main`,
Domain bleibt `qr.wue.ch`. Es gibt keinen zusätzlichen Deployment-Workflow.

Die CI prüft die Dateien und erzeugt Weiterleitungen und QR-Downloads.
Auf `main` speichert der Bot geänderte HTML-Dateien mit einem normalen Commit.
Danach fordert die CI einen Build der bestehenden Pages an, weil Bot-Commits
allein diesen Build nicht auslösen. Ohne geänderte HTML-Dateien ist kein
zusätzlicher Commit nötig. Pull Requests prüfen und erzeugen Downloads, schreiben
aber keine Dateien zurück. Es wird niemals mit Force-Push gearbeitet.

Dafür verwendet der Workflow das vorhandene GitHub-Token mit `contents: write`
und `pages: write`. Ein eigener Token, OIDC oder ein Deployment-Environment sind
nicht erforderlich. Die bisherige branchbasierte Veröffentlichung bleibt
bestehen und wird nicht zu einer Veröffentlichungssperre hinter den Tests umgebaut.

Segno 1.6.6 erzeugt die QR-Bilder ohne externe QR-API. Die Website bleibt statisch.
Die Startseite leitet weiterhin zu `https://wue.ch` weiter.

## Lokal prüfen

Python 3.9 oder neuer:

```sh
python3 -m pip install -r scripts/qr-requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/generate_qr.py --output /tmp/qr-codes --write-pages
python3 scripts/check.py
```

`--write-pages` schreibt die HTML-Weiterleitungen ins Repository. Ohne diese
Option entstehen nur die QR-Downloads. `--base-url` erlaubt eine andere
HTTPS-Basisadresse für eine Vorschau. Der QR-Ausgabeordner muss außerhalb des
Repositorys liegen. Für eine branchbasierte Fork-Vorschau keine fremde CNAME übernehmen.

`python3 -m http.server 8765 --bind 127.0.0.1` startet eine lokale Vorschau.
Dort `.html` an die kurze Adresse anhängen; anschließend mit Strg+C beenden.
Die Prüfung erkennt fehlende lokale Ziele, unpassende Links und PDF-Kennungen,
prüft aber nicht den vollständigen Inhalt der PDF.
