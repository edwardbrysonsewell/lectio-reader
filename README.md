# Lectio Reader

An offline Latin reader with a bundled library and Lewis & Short dictionary. Static HTML, CSS and JavaScript; no account or AI service is required to read. Personal imports, bookmarks and notes stay in the browser on each device.

## iPhone installation

Open the published GitHub Pages address in Safari. Choose Share, then Add to Home Screen. Open the new icon and use Offline downloads to save the collection. Keep the app open until saving completes. Browser storage can be removed by the device; export your personal reading data periodically.

## Publishing

GitHub Pages deploys `dist/` through the included workflow. Configure Pages to use GitHub Actions. After editing application assets, run `python3 scripts/finalize.py` to refresh offline hashes before committing.

## On the Mac

`Lectio Reader.app` on the Desktop opens `Open Lectio.command`, which serves this folder's `dist/` at http://localhost:8765/. Keep its Terminal window open while reading. This folder is the only official copy; the phone site is built from the same `dist/`.

## Rebuilding the texts

The raw archives live in `sources/` (not in Git; copies of the originals preserved in `~/Downloads/LatinReader/sources`).

- `python3 scripts/import-perseus.py` — re-converts the 345 Perseus editions to reading text (no apparatus, verse lines kept, book/line passage labels).
- `python3 scripts/typo-scan.py` — finds transcription errors in the Latin Library texts; writes `work/typo-candidates.tsv` and changes nothing.
- `python3 scripts/apply-typo-fixes.py` — applies only the corrections backed by an aligned Perseus edition and appends each change to `corrections/latin-library-edition-fixes.tsv`.
- Then `python3 scripts/finalize.py`, `node scripts/test-core.mjs` and `node scripts/test-library.mjs` before committing.

## Sources and limits

See `dist/licenses/ATTRIBUTIONS.txt` and the included dataset licenses. Source selections, fragments, and digitization errors may remain. The dictionary presents possible headwords rather than contextual grammatical analyses. No speech synthesis is included.
