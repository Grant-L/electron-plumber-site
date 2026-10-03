# Licensing

This repository holds four kinds of material, and they are licensed differently.

| What | Where | License |
|---|---|---|
| **Code**: the generator, templates' markup and logic, checks, tests, CSS, JavaScript, workflows | `build.py`, `check.py`, `sitegen/`, `tools/`, `tests/`, `static/css/`, `static/js/`, `Makefile`, `.github/` | [MIT](LICENSE) |
| **Written content**: the site's copy, including the text inside the templates, and episode handouts | the prose in `sitegen/pages.py`, `content/` | [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/): share with attribution; no commercial use; no derivatives. The same license as the [notes repo](https://github.com/Grant-L/electron-plumber-notes). |
| **Fonts**: EP Serif and EP Mono, subset and renamed copies of Source Serif 4 (Adobe) and IBM Plex Mono (IBM) | `static/fonts/` | [SIL Open Font License 1.1](https://openfontlicense.org), as upstream. Renamed because each upstream font has a Reserved Font Name. The license and both copyright notices ship with the fonts in `static/fonts/OFL.txt`. Not covered by the MIT license above, and not part of the brand. |
| **Brand**: the name "The Electron Plumber", the mark (a Smith chart holding a trefoil) in every form, the banner image, the favicons and the social image | `design/`, `static/img/`, `static/favicon.*`, `static/apple-touch-icon.png` | All rights reserved. Not covered by the MIT license above. |

In short: reuse the code freely, quote and share the writing with attribution, use the fonts under their own license, and do not reuse the identity.

The research this site links to, Applied Vacuum Engineering, lives in its own repository under Apache-2.0.
