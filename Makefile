PY ?= python3
.PHONY: build drafts check test lint serve serve-drafts mark clean

build:            ## build the public site into _site/
	$(PY) build.py

drafts:           ## build with unpublished handouts from _private/drafts/ (local preview only)
	$(PY) build.py --drafts --out _site_drafts

check: build      ## build, then gate: links, anchors, titles, placeholders, standing rules
	$(PY) check.py _site

test:             ## unit tests
	$(PY) -m pytest -q

lint:
	ruff check .

serve: build      ## http://localhost:4173
	$(PY) -m http.server 4173 --directory _site

serve-drafts: drafts  ## http://localhost:4174
	$(PY) -m http.server 4174 --directory _site_drafts

mark:             ## regenerate the mark files and favicons (needs matplotlib)
	$(PY) design/make_mark.py

clean:
	rm -rf _site _site_drafts
