/* electron-plumber.com: three small behaviors. The site works without any of them. */
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
})();
