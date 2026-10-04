/* electron-plumber.com: four small behaviors. The site works without any of them. */
(function () {
  "use strict";

  // 1. Phone navigation.
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("nav");
  if (toggle && nav) {
    var close = function () {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    };
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && nav.classList.contains("is-open")) { close(); toggle.focus(); }
    });
    nav.addEventListener("focusout", function (event) {
      // relatedTarget is null when the whole window loses focus: leave the menu alone then.
      if (event.relatedTarget && !nav.contains(event.relatedTarget) && event.relatedTarget !== toggle) { close(); }
    });
  }

  // 2. Click-to-load video. Until the visitor asks for it, nothing is requested from YouTube;
  //    without JavaScript the play button is a plain link to the video.
  document.querySelectorAll(".card[data-youtube]").forEach(function (card) {
    var play = card.querySelector(".card__play");
    if (!play) { return; }
    play.addEventListener("click", function (event) {
      event.preventDefault();
      var frame = document.createElement("iframe");
      frame.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(card.dataset.youtube) + "?autoplay=1&rel=0";
      frame.title = card.dataset.title || "Video";
      frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      frame.allowFullscreen = true;
      card.textContent = "";
      card.appendChild(frame);
      frame.focus();
    });
  });

  // 3. Filters: the episode list by arc, the History timeline by era, subject and kind of event.
  //    The filter block ships hidden, so without JavaScript there are no dead buttons and every item shows.
  //    Each [data-filter="field"] group narrows on the items' data-field values (space-separated lists match
  //    any one value); the groups combine with AND.
  document.querySelectorAll("[data-filters]").forEach(function (box) {
    if (!box.dataset.items) { return; }
    var items = document.querySelectorAll(box.dataset.items);
    var status = box.querySelector("[role=status]");
    var groups = box.querySelectorAll("[data-filter]");
    var state = {};
    groups.forEach(function (group) { state[group.dataset.filter] = "all"; });
    var fields = Object.keys(state);

    var update = function () {
      var shown = 0;
      var filtered = fields.some(function (f) { return state[f] !== "all"; });
      items.forEach(function (item) {
        item.hidden = !fields.every(function (f) {
          return state[f] === "all" || (" " + item.dataset[f] + " ").indexOf(" " + state[f] + " ") >= 0;
        });
        if (!item.hidden) { shown += 1; }
      });
      if (status) {
        status.textContent = !filtered ? status.dataset.total + " " + status.dataset.noun
          : shown ? shown + " shown" : (box.dataset.empty || "Nothing matches.");
      }
      box.dispatchEvent(new CustomEvent("filters:change", { detail: { state: state, shown: shown } }));
    };

    groups.forEach(function (group) {
      var chips = group.querySelectorAll(".chip[data-value]");
      chips.forEach(function (chip) {
        chip.addEventListener("click", function () {
          state[group.dataset.filter] = chip.dataset.value;
          chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
          update();
        });
      });
    });
    box.hidden = false;
  });

  // 4. History: an era axis over the timeline, built from the list. The list entry is the detail view; the axis
  //    mirrors li.hidden and changes filters only through their chips, so era filter and zoom cannot disagree.
  const d = document, box = d.querySelector('[data-filters][data-items=".tl"]');
  const chips = box ? [...box.querySelectorAll('[data-filter="era"] .chip[data-from]')] : [];
  if (!chips.length) { return; }
  const make = (tag, cls, parent, text) => {
    const e = parent.appendChild(d.createElement(tag));
    e.className = cls && "tl-axis" + cls;
    if (text) { e.textContent = text; }
    if (tag === "button") { e.type = tag; }
    return e;
  };
  const on = (el, type, fn) => el.addEventListener(type, fn);
  const plural = (n) => n + (n === 1 ? " event" : " events");
  const pick = (f, v = "all") => box.querySelector(`[data-filter="${f}"] .chip[data-value="${v}"]`);
  const groups = [...box.querySelectorAll("[data-filter]")].map((g) => g.dataset.filter);
  const items = [...d.querySelectorAll(".tl[data-year]")];
  const status = box.querySelector("[role=status]");
  // Phones get no axis; the chips fold behind this button.
  const fold = make("button", "__filter chip", box.firstElementChild, "Filter");
  fold.parentNode.prepend(fold);
  fold.ariaExpanded = false;
  on(fold, "click", () => { fold.ariaExpanded = fold.ariaExpanded === "false"; });
  const eras = chips.map((chip, i) => {
    const to = chip.dataset.to;
    return { slug: chip.dataset.value, chip, i, label: chip.textContent, from: +chip.dataset.from,
      to: +to || new Date().getFullYear(), end: to || "present" };
  });
  const axis = d.createElement("nav"), inner = make("div", "", axis), bands = make("div", "__bands", inner);
  axis.className = "tl-axis";
  inner.className = "inner";
  axis.ariaLabel = "Timeline, " + eras[0].from + " to " + eras[eras.length - 1].end;
  const scroll = make("div", "__scroll", inner), track = make("div", "__track", scroll), tip = make("div", "__tip", inner);
  tip.ariaHidden = true;
  let zoom = null, stops = [], tipFor = null, armed = false, raf = 0;
  eras.forEach((e) => {
    e.band = make("button", "__band", bands);
    make("span", "__label", e.band, e.label);
    make("span", "__years", e.band, e.from + "\u2013" + e.end);
    e.count = make("span", "__count", e.band);
    on(e.band, "click", () => pick("era", e === zoom ? "all" : e.slug).click());
  });
  const full = make("button", "__band tl-axis__full", bands);
  make("span", "", full, "\u00d7").ariaHidden = true;
  full.append(" Full span");
  const zoomOut = () => {
    const was = zoom, here = d.activeElement === full;
    pick("era").click();
    if (here) { was.band.focus(); }
  };
  on(full, "click", zoomOut);
  const marks = items.map((li) => {
    const a = make("a", "__dot", track), m = { li, a, year: +li.dataset.year, era: eras.find((e) => e.slug === li.dataset.era) };
    [m.date, m.title] = [".tl__date", ".tl__title"].map((q) => li.querySelector(q).textContent.trim());
    a.href = "#" + li.id;
    a.tabIndex = -1;
    a.ariaLabel = m.date + ": " + m.title;
    a.mark = m;
    return m;
  });

  // Beside its dot, never down over the list: above in the first lane, below in the others.
  const showTip = (el) => {
    tipFor = el && el.mark ? el : null;
    tip.hidden = !tipFor;
    if (!tipFor) { return; }
    tip.textContent = "";
    make("b", "", tip, el.mark.date);
    make("span", "", tip, el.mark.title);
    const ib = inner.getBoundingClientRect(), r = el.getBoundingClientRect(), pad = parseFloat(getComputedStyle(inner).paddingLeft);
    const x = r.left + r.width / 2 - ib.left, w = tip.offsetWidth, left = Math.max(pad, Math.min(x - w / 2, ib.width - pad - w));
    tip.classList.toggle("tl-axis__tip--below", el.lane > 0);
    tip.style.cssText = `left:${left}px;top:${el.lane ? r.bottom - ib.top + 4 : r.top - ib.top - tip.offsetHeight - 4}px;--x:${x - left}px`;
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
    const place = (el, x, lane, era, at = x) => {
      el.style.cssText = `left:${x}px;top:${lane * hit}px;--off:${at - x}px`;
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
      const ends = [1e9, 1e9, 1e9], ms = marks.filter((m) => m.era === e && !m.li.hidden);
      // At most three lanes, the track only as tall as those used. Past that the full span merges the era into
      // one cluster; zoomed in, the last lane overlaps.
      const crowded = ms.reverse().some((m) => {
        m.x = px(m.year);
        // Hit areas stay apart but may sit left of their dots.
        m.lane = ends.findIndex((end) => end - hit >= Math.max(m.lo = m.x + 16 - hit, k * bw + hit / 2));
        if (m.lane < 0 && !zoom) { return true; }
        ends[m.lane < 0 ? (m.lane = 2) : m.lane] = m.hit = Math.max(m.lo, Math.min(m.x, ends[m.lane] - hit));
      });
      if (crowded) {
        const more = make("button", "__dot tl-axis__more", track, "+" + ms.length);
        more.ariaLabel = "Zoom to " + e.band.ariaLabel;
        on(more, "click", () => e.chip.click());
        place(more, k * bw + bw / 2, 0, e);
      } else {
        ms.forEach((m) => { m.a.hidden = false; place(m.a, Math.min(m.x, m.hit + hit / 2 - 7), m.lane, e, m.hit); });
      }
    });
    track.style.cssText = `width:${w}px;--lanes:${lanes}`;
    stops.sort((a, b) => a.x - b.x);
    const near = (s) => Math.abs(s.x - (was.x || 0));
    const keep = stops.includes(was) ? was : stops.reduce((best, s) => (best && near(best) <= near(s) ? best : s), null);
    rove(keep, f);
    showTip(f && keep);
  };

  const sync = () => {
    const was = zoom, shown = items.filter((li) => !li.hidden);
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
    if (li && li.hidden && a) {
      groups.forEach((f) => pick(f).click());
      li.scrollIntoView();
    }
    current(a && li);
    if (a && !a.hidden) {
      rove(a);
      scroll.scrollLeft = a.x - scroll.clientWidth / 2;
    }
  };

  on(track, "pointerdown", (ev) => { armed = ev.pointerType !== "touch" || tipFor === ev.target.closest(".tl-axis__dot"); });
  on(track, "click", (ev) => {
    const a = ev.target.closest("a.tl-axis__dot");
    if (!a) { return; }
    rove(a);
    // Touch has no hover: the first tap shows the tip, the second follows the link. Enter's click has detail 0.
    if (ev.detail && !armed) { ev.preventDefault(); showTip(a); return; }
    current(a.mark.li, true);
  });
  on(track, "focusin", (ev) => showTip(ev.target));
  on(track, "focusout", () => showTip(null));
  on(track, "mouseover", (ev) => showTip(ev.target.closest(".tl-axis__dot") || focused()));
  on(track, "mouseleave", () => showTip(focused()));
  on(scroll, "scroll", () => showTip(focused()));
  on(axis, "keydown", (ev) => {
    const i = stops.indexOf(d.activeElement), k = ev.key, last = stops.length - 1;
    const firsts = stops.map((s, j) => j).filter((j) => !j || stops[j].era !== stops[j - 1].era);
    const era = firsts.filter((j) => j <= i).length - 1 + (k === "PageDown") - (k === "PageUp");
    const page = firsts[Math.max(0, Math.min(firsts.length - 1, era))];
    const to = { ArrowLeft: i - 1, ArrowRight: i + 1, Home: 0, End: last, PageUp: page, PageDown: page }[k];
    if (k === "Escape" && (tipFor || zoom)) {
      if (tipFor) { showTip(null); } else { zoomOut(); }
    } else if (i < 0 || to === undefined) {
      return;
    } else {
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
