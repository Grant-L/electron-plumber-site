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

  // 3. Filter the episode list by arc.
  var chips = document.querySelectorAll(".chip[data-arc]");
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var arc = chip.dataset.arc;
      chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
      var shown = 0;
      document.querySelectorAll(".ep-row[data-arc]").forEach(function (row) {
        row.hidden = arc !== "all" && row.dataset.arc !== arc;
        if (!row.hidden) { shown += 1; }
      });
      var status = document.querySelector(".filter [role=status]");
      if (status) {
        status.textContent = arc === "all" ? status.dataset.total + " published"
          : shown ? shown + " shown" : "Nothing in this arc yet.";
      }
    });
  });
})();
