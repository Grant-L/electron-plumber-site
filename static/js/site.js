/* electron-plumber.com: four small behaviors. The site works without any of them. */
(() => {
  "use strict";
  const d = document;
  const on = (el, type, fn) => el.addEventListener(type, fn);

  // 1. Phone navigation.
  const toggle = d.querySelector(".nav-toggle"), nav = d.getElementById("nav");
  if (toggle && nav) {
    const show = (open) => { nav.classList.toggle("is-open", open); toggle.ariaExpanded = open; };
    on(toggle, "click", () => show(!nav.classList.contains("is-open")));
    on(d, "keydown", (ev) => {
      if (ev.key === "Escape" && nav.classList.contains("is-open")) { show(false); toggle.focus(); }
    });
    // relatedTarget is null when the whole window loses focus: leave the menu alone then.
    on(nav, "focusout", (ev) => {
      const to = ev.relatedTarget;
      if (to && !nav.contains(to) && to !== toggle) { show(false); }
    });
  }

  // 2. Click-to-load video. Until the visitor asks for it, nothing is requested from YouTube;
  //    without JavaScript the play button is a plain link to the video.
  d.querySelectorAll(".card[data-youtube]").forEach((card) => {
    const play = card.querySelector(".card__play");
    if (!play) { return; }
    on(play, "click", (ev) => {
      ev.preventDefault();
      const frame = d.createElement("iframe");
      frame.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(card.dataset.youtube) + "?autoplay=1&rel=0";
      frame.title = card.dataset.title || "Video";
      frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      frame.allowFullscreen = true;
      card.replaceChildren(frame);
      frame.focus();
    });
  });

  // 3. Filters: the episode list by arc, the History timeline by era, subject and kind of event.
  //    The filter block ships hidden, so without JavaScript there are no dead buttons and every item shows.
  //    Each [data-filter="field"] group narrows on the items' data-field values (space-separated lists match
  //    any one value); the groups combine with AND.
  d.querySelectorAll("[data-filters][data-items]").forEach((box) => {
    const items = d.querySelectorAll(box.dataset.items), status = box.querySelector("[role=status]"), state = {};
    box.querySelectorAll("[data-filter]").forEach((group) => {
      const f = group.dataset.filter, chips = group.querySelectorAll(".chip[data-value]");
      state[f] = "all";
      chips.forEach((chip) => on(chip, "click", () => {
        state[f] = chip.dataset.value;
        chips.forEach((c) => { c.ariaPressed = c === chip; });
        let shown = 0;
        items.forEach((item) => {
          item.hidden = !Object.keys(state).every((k) => state[k] === "all" || item.dataset[k].split(" ").includes(state[k]));
          shown += !item.hidden;
        });
        if (status) {
          status.textContent = Object.values(state).every((v) => v === "all") ? status.dataset.total + " " + status.dataset.noun
            : shown ? shown + " shown" : box.dataset.empty || "Nothing matches.";
        }
        box.dispatchEvent(new CustomEvent("filters:change"));
      }));
    });
    box.hidden = false;
  });

  // 4. History: an era axis over the timeline, built from the list. The list entry is the detail view; the axis
  //    mirrors li.hidden and changes filters only through their chips, so era filter and zoom cannot disagree.
  //    A dot opens a preview card copied from its entry, so the card cannot drift from the list.
  const box = d.querySelector('[data-filters][data-items=".tl"]');
  const chips = box ? [...box.querySelectorAll('[data-filter="era"] .chip[data-from]')] : [];
  if (!chips.length) { return; }
  const make = (tag, cls, parent, text) => {
    const e = d.createElement(tag);
    e.className = cls.startsWith("__") ? "tl-axis" + cls : cls;
    if (text) { e.textContent = text; }
    if (tag === "button") { e.type = tag; }
    parent?.append(e);
    return e;
  };
  const arrow = (el, text, before) => el[before ? "prepend" : "append"](Object.assign(make("span", "", null, text), { ariaHidden: true }));
  const plural = (n) => n + (n === 1 ? " event" : " events");
  const pick = (f, v = "all") => box.querySelector(`[data-filter="${f}"] .chip[data-value="${v}"]`);
  const groups = [...box.querySelectorAll("[data-filter]")];
  const items = [...d.querySelectorAll(".tl[data-year]")];
  const status = box.querySelector("[role=status]");
  // Phones get no axis; the chips fold behind this button.
  const fold = make("button", "__filter chip", null, "Filter");
  box.firstElementChild.prepend(fold);
  groups.forEach((g) => { g.id = "tl-filter-" + g.dataset.filter; });
  fold.setAttribute("aria-controls", groups.map((g) => g.id).join(" "));
  fold.ariaExpanded = false;
  on(fold, "click", () => { fold.ariaExpanded = fold.ariaExpanded === "false"; });
  const eras = chips.map((chip, i) => {
    const to = chip.dataset.to;
    return { slug: chip.dataset.value, chip, i, label: chip.textContent, from: +chip.dataset.from,
      to: +to || new Date().getFullYear(), end: to || "present" };
  });
  const axis = make("nav", "tl-axis"), inner = make("div", "inner", axis), bands = make("div", "__bands", inner);
  axis.ariaLabel = "Timeline, " + eras[0].from + " to " + eras[eras.length - 1].end;
  const scroll = make("div", "__scroll", inner), track = make("div", "__track", scroll);

  const card = make("section", "tl-card", inner), head = make("div", "tl-card__head", card);
  Object.assign(card, { id: "tl-card", role: "group", tabIndex: -1, hidden: true });
  card.setAttribute("aria-labelledby", "tl-card-title");
  const shut = make("button", "tl-card__close", head, "Close");
  shut.ariaLabel = "Close preview";
  const date = make("p", "mono tl-card__date", head), title = make("p", "tl-card__title", card);
  title.id = "tl-card-title";
  const line = make("p", "small tl-card__line", card), source = make("p", "mono small tl-card__source", card);
  const read = make("a", "tl-card__read", card, "Read entry ");
  arrow(read, "\u2193");
  const back = make("button", "chip tl__back", null, " Back to timeline");
  arrow(back, "\u2191", true);

  const tip = make("div", "__tip", inner);
  tip.ariaHidden = true;
  let zoom = null, stops = [], tipFor = null, open = null, saved = null, raf = 0;
  eras.forEach((e) => {
    e.band = make("button", "__band", bands);
    make("span", "__label", e.band, e.label);
    make("span", "__years", e.band, e.from + "\u2013" + e.end);
    e.count = make("span", "__count", e.band);
    on(e.band, "click", () => (e === zoom ? pick("era") : e.chip).click());
  });
  const full = make("button", "__band tl-axis__full", bands, " Full span");
  arrow(full, "\u00d7", true);
  const zoomOut = () => {
    const was = zoom, here = d.activeElement === full;
    pick("era").click();
    if (here) { was.band.focus(); }
  };
  on(full, "click", zoomOut);
  const marks = items.map((li) => {
    const a = make("a", "__dot", track), m = { li, a, year: +li.dataset.year, era: eras.find((e) => e.slug === li.dataset.era) };
    [m.date, m.title] = [".tl__date", ".tl__title"].map((q) => li.querySelector(q).textContent.trim());
    Object.assign(a, { href: "#" + li.id, tabIndex: -1, ariaLabel: m.date + ": " + m.title, ariaExpanded: false, mark: m });
    a.setAttribute("aria-controls", card.id);
    return m;
  });

  // Centred on el, clamped `edge` px inside .inner.
  const beside = (el, panel, edge) => {
    const ib = inner.getBoundingClientRect(), r = el.getBoundingClientRect(), w = panel.offsetWidth;
    const x = r.left + r.width / 2 - ib.left;
    return { ib, r, w, x, left: Math.max(edge, Math.min(x - w / 2, ib.width - edge - w)) };
  };
  // Beside its dot and inside the axis, so never over the filters: below only for a lower lane that has room.
  // Not while the card is open, and not for a tapped dot (focused without :focus-visible).
  const showTip = (el) => {
    tipFor = el && el.mark && !open && (el !== d.activeElement || el.matches(":focus-visible")) ? el : null;
    tip.hidden = !tipFor;
    if (!tipFor) { return; }
    tip.replaceChildren();
    make("b", "", tip, el.mark.date);
    make("span", "", tip, el.mark.title);
    const { ib, r, x, left } = beside(el, tip, parseFloat(getComputedStyle(inner).paddingLeft)), h = tip.offsetHeight;
    const below = r.bottom - ib.top + 4, under = el.lane > 0 && below + h <= ib.height;
    tip.classList.toggle("tl-axis__tip--below", under);
    tip.style.cssText = `left:${left}px;top:${under ? below : r.top - ib.top - h - 4}px;--x:${x - left}px`;
  };
  // Under the track, on the open dot.
  const pin = () => {
    if (!open) { return; }
    const { ib, w, x, left } = beside(open, card, 8);
    card.style.cssText = `left:${left}px;top:${scroll.getBoundingClientRect().bottom - ib.top + 8}px;--x:${x - left}px`;
    card.classList.toggle("tl-card--far", Math.abs(x - left - w / 2) > 0.4 * w);
  };
  const close = (refocus) => {
    if (!open) { return; }
    card.hidden = true;
    open.ariaExpanded = false;
    if (refocus) { open.focus(); }
    open = null;
  };
  const preview = (a) => {
    const was = open, li = a.mark.li, cites = [...li.querySelectorAll(".tl__sources > li")];
    close(was === a);
    if (was === a) { return; }
    open = a;
    rove(a);
    showTip(null);
    date.textContent = a.mark.date;
    title.textContent = a.mark.title;
    line.textContent = li.dataset.oneliner || "";
    line.hidden = !li.dataset.oneliner;
    const cite = cites.find((c) => c.querySelector(".mono").textContent === "Primary") || cites[0];
    source.hidden = !cite;
    if (cite) {
      const copy = cite.cloneNode(true);
      copy.querySelectorAll("a, .mono").forEach((n) => n.remove());
      source.replaceChildren("Source: ", ...copy.childNodes);
    }
    read.href = "#" + li.id;
    a.ariaExpanded = true;
    card.hidden = false;
    pin();
    card.focus({ preventScroll: true });
    if (card.getBoundingClientRect().bottom > innerHeight) { card.scrollIntoView({ block: "nearest" }); }
  };
  const focused = () => (stops.includes(d.activeElement) ? d.activeElement : null);
  const current = (li, focus) => {
    marks.forEach((m) => {
      m.li.classList.toggle("tl--current", m.li === li);
      m.a.ariaCurrent = m.li === li ? "true" : null;
    });
    // After the link's own fragment navigation, which would otherwise reset focus.
    if (focus) { setTimeout(() => li.querySelector(".tl__title a").focus({ preventScroll: true })); }
  };
  const rove = (el, focus) => {
    stops.forEach((s) => { s.tabIndex = s === el ? 0 : -1; });
    if (focus && el) { el.focus(); }
  };

  const layout = () => {
    const hit = parseFloat(getComputedStyle(axis).getPropertyValue("--hit")), shown = zoom ? [zoom] : eras;
    const f = focused(), was = f || stops.find((s) => s.tabIndex === 0) || {};
    const w = zoom ? Math.max(scroll.clientWidth, (zoom.to - zoom.from + 1) * 12) : scroll.clientWidth, bw = w / shown.length;
    let lanes = 1;
    [...track.children].forEach((n) => n.mark || n.remove());
    marks.forEach((m) => { m.a.hidden = true; });
    stops = [];
    const place = (el, x, lane, era) => {
      el.style.cssText = `left:${x}px;top:${lane * hit}px`;
      Object.assign(el, { x, lane, era });
      stops.push(el);
      lanes = Math.max(lanes, lane + 1);
    };
    shown.forEach((e, k) => {
      const px = (y) => Math.max(hit / 2, Math.min(bw - hit / 2, (y - e.from) / (e.to - e.from + 1) * bw)) + k * bw;
      make("span", "__zone" + (e.i % 2 ? " tl-axis__zone--alt" : ""), track).style.cssText = `left:${k * bw}px;width:${bw}px`;
      for (let y = Math.ceil(e.from / 10) * 10, last = -1e9; y <= e.to; y += 10) {
        const tick = make("span", "__tick", track);
        tick.style.left = px(y) + "px";
        if (px(y) - last >= 40) { tick.textContent = y; last = px(y); }
      }
      const ends = [-1e9, -1e9, -1e9], ms = marks.filter((m) => m.era === e && !m.li.hidden);
      // At most three lanes, the track only as tall as those used. Past that the full span merges the era into
      // one cluster; zoomed in, the last lane overlaps.
      const crowded = ms.some((m) => {
        m.x = px(m.year);
        m.lane = ends.findIndex((end) => m.x - end >= hit);
        if (m.lane < 0 && !zoom) { return true; }
        ends[m.lane < 0 ? (m.lane = 2) : m.lane] = m.x;
      });
      if (crowded) {
        // The name starts with the visible "+N", so voice control users can say what they see.
        const more = make("button", "__dot tl-axis__more", track, "+" + ms.length);
        more.ariaLabel = `+${plural(ms.length)}, zoom to ${e.label} ${e.from}\u2013${e.end}`;
        on(more, "click", () => e.chip.click());
        place(more, k * bw + bw / 2, 0, e);
      } else {
        ms.forEach((m) => { m.a.hidden = false; place(m.a, m.x, m.lane, e); });
      }
    });
    track.style.cssText = `width:${w}px;--lanes:${lanes}`;
    stops.sort((a, b) => a.x - b.x);
    const near = (s) => Math.abs(s.x - (was.x || 0));
    const keep = stops.includes(was) ? was : stops.reduce((best, s) => (best && near(best) <= near(s) ? best : s), null);
    rove(keep, f);
    showTip(f && keep);
    if (open?.hidden) { close(); }
    pin();
  };

  const sync = () => {
    const was = zoom, shown = items.filter((li) => !li.hidden);
    close();
    zoom = eras.find((e) => e.chip.ariaPressed === "true") || null;
    full.hidden = !zoom;
    // Zoomed, the row holds only that era's band, so no label sits over another era's years.
    eras.forEach((e) => {
      const n = shown.filter((li) => li.dataset.era === e.slug).length;
      e.band.hidden = !!zoom && e !== zoom;
      e.count.textContent = n;
      e.band.ariaLabel = `${e.label} ${e.from}\u2013${e.end}, ${plural(n)}`;
      e.band.ariaPressed = e === zoom;
    });
    if (zoom !== was) { scroll.scrollLeft = 0; }
    layout();
    if (zoom && shown.length && status) { status.textContent = `${zoom.label}, ${zoom.from} to ${zoom.end}: ${plural(shown.length)}`; }
  };

  const fromHash = () => {
    const li = d.getElementById(location.hash.slice(1)), i = items.indexOf(li), a = i < 0 ? null : marks[i].a;
    close();
    if (li && li.hidden && a) {
      groups.forEach((g) => pick(g.dataset.filter).click());
      li.scrollIntoView();
    }
    current(a && li);
    if (a && !a.hidden) {
      rove(a);
      scroll.scrollLeft = a.x - scroll.clientWidth / 2;
    }
  };

  // Modified clicks keep the link's own behaviour (new tab, new window).
  const plain = (ev) => !(ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey);
  on(track, "click", (ev) => {
    const a = ev.target.closest("a.tl-axis__dot");
    if (a && plain(ev)) { ev.preventDefault(); preview(a); }
  });
  on(shut, "click", () => close(true));
  on(d, "click", (ev) => { if (!axis.contains(ev.target)) { close(); } });
  // The card covers the filters, so focus there closes it. Null: a window blur, or a click (handled above).
  on(axis, "focusout", (ev) => { if (ev.relatedTarget && !axis.contains(ev.relatedTarget)) { close(); } });
  on(read, "click", (ev) => {
    if (!plain(ev)) { return; }
    const li = open.mark.li;
    saved = { a: open, chips: groups.map((g) => g.querySelector("[aria-pressed=true]")) };
    close();
    current(li, true);
    li.firstElementChild.append(back);
  });
  on(back, "click", () => {
    const { a, chips } = saved;
    chips.forEach((c) => c.ariaPressed === "true" || c.click());
    back.remove();
    axis.scrollIntoView();
    const dot = stops.includes(a) ? a : stops[0];
    rove(dot);
    scroll.scrollLeft = dot.x - scroll.clientWidth / 2;
    dot.focus({ preventScroll: true });
  });
  on(track, "focusin", (ev) => showTip(ev.target));
  on(track, "focusout", () => showTip(null));
  // Touch has no hover, so only a mouse shows the tip by pointing.
  on(track, "pointerover", (ev) => ev.pointerType === "mouse" && showTip(ev.target.closest(".tl-axis__dot") || focused()));
  on(track, "mouseleave", () => showTip(focused()));
  on(scroll, "scroll", () => { showTip(focused()); pin(); });
  on(axis, "keydown", (ev) => {
    const i = stops.indexOf(d.activeElement), k = ev.key, last = stops.length - 1;
    const firsts = stops.map((s, j) => j).filter((j) => !j || stops[j].era !== stops[j - 1].era);
    const era = firsts.filter((j) => j <= i).length - 1 + (k === "PageDown") - (k === "PageUp");
    const page = firsts[Math.max(0, Math.min(firsts.length - 1, era))];
    const to = { ArrowLeft: i - 1, ArrowRight: i + 1, Home: 0, End: last, PageUp: page, PageDown: page }[k];
    if (k === "Escape" && (open || tipFor || zoom)) {
      if (open) { close(true); } else if (tipFor) { showTip(null); } else { zoomOut(); }
    } else if (i >= 0 && stops[i].mark && (k === "Enter" || k === " ")) {
      preview(stops[i]);
    } else if (i < 0 || to === undefined) {
      return;
    } else {
      close();
      rove(stops[Math.max(0, Math.min(last, to))], true);
    }
    ev.preventDefault();
  });
  on(box, "filters:change", sync);
  on(window, "hashchange", fromHash);
  on(window, "resize", () => { raf = raf || requestAnimationFrame(() => { raf = 0; layout(); }); });
  box.before(axis);
  sync();
  fromHash();
})();
