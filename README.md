# Lectio Reader

An offline Latin reader with a bundled library and Lewis & Short dictionary. Static HTML, CSS and JavaScript; no account or AI service is required to read. Personal imports, bookmarks and notes stay in the browser on each device.

## iPhone installation

Open the published GitHub Pages address in Safari. Choose Share, then Add to Home Screen. Open the new icon and use Offline downloads to save the collection. Keep the app open until saving completes. Browser storage can be removed by the device; export your personal reading data periodically.

## Publishing

GitHub Pages deploys `dist/` through the included workflow. Configure Pages to use GitHub Actions. After editing application assets, run `python3 scripts/finalize.py` to refresh offline hashes before committing.

## Sources and limits

See `dist/licenses/ATTRIBUTIONS.txt` and the included dataset licenses. Source selections, fragments, and digitization errors may remain. The dictionary presents possible headwords rather than contextual grammatical analyses. No speech synthesis is included.
