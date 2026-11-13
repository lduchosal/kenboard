"""Client-side search script shipped as ``search.js`` by ``ken wiki build`` (#1178).

Pure data, no logic — sibling of ``wiki_css``. Vanilla JS, no dependency: it scans
``window.KEN_WIKI_INDEX`` (``search-index.js``, loaded by a plain ``<script>`` so the
page also works over ``file://``) linearly on every keystroke. Results are built with
``textContent`` only — never ``innerHTML`` — so task text cannot inject markup.
"""

_WIKI_SEARCH_JS = r"""(function () {
  "use strict";
  var MAX = 100;
  var index = window.KEN_WIKI_INDEX || [];
  var input = document.querySelector(".wiki-search input");
  var out = document.getElementById("wiki-search-results");
  if (!input || !out) return;

  // Case- and accent-insensitive key. The index text is NFC, so folding keeps
  // one char per char and match offsets stay valid in the original string.
  function fold(s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  index.forEach(function (e) {
    e.t = fold("#" + e.id + " " + e.title);
    e.b = fold(e.text);
  });

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  // Every word must match (AND). Title hits outrank body hits; an exact
  // "#123" / "123" query puts that task first.
  function search(q) {
    var words = fold(q).split(/\s+/).filter(Boolean);
    var idm = /^#?(\d+)$/.exec(q.trim());
    var hits = [];
    index.forEach(function (e) {
      var score = idm && String(e.id) === idm[1] ? 1000 : 0;
      for (var i = 0; i < words.length; i++) {
        if (e.t.indexOf(words[i]) !== -1) score += 10;
        else if (e.b.indexOf(words[i]) !== -1) score += 1;
        else return;
      }
      hits.push({ e: e, score: score });
    });
    hits.sort(function (a, b) {
      return b.score - a.score || b.e.id - a.e.id;
    });
    return { words: words, hits: hits };
  }

  // Append `text` to `parent`, wrapping each occurrence of a word in <mark>.
  function highlight(parent, text, words) {
    var folded = fold(text);
    var ranges = [];
    if (folded.length === text.length) {
      words.forEach(function (w) {
        for (var p = folded.indexOf(w); p !== -1; p = folded.indexOf(w, p + w.length)) {
          ranges.push([p, p + w.length]);
        }
      });
    }
    ranges.sort(function (a, b) {
      return a[0] - b[0];
    });
    var pos = 0;
    ranges.forEach(function (r) {
      if (r[0] < pos) return;
      parent.appendChild(document.createTextNode(text.slice(pos, r[0])));
      parent.appendChild(el("mark", "", text.slice(r[0], r[1])));
      pos = r[1];
    });
    parent.appendChild(document.createTextNode(text.slice(pos)));
  }

  function snippet(e, words) {
    var at = -1;
    for (var i = 0; i < words.length && at === -1; i++) at = e.b.indexOf(words[i]);
    if (at === -1) return null;
    var start = Math.max(0, at - 60);
    var end = Math.min(e.text.length, start + 220);
    var div = el("div", "wiki-search-snippet");
    highlight(
      div,
      (start ? "… " : "") + e.text.slice(start, end) + (end < e.text.length ? " …" : ""),
      words
    );
    return div;
  }

  function render() {
    var q = input.value;
    var res = search(q);
    var shown = res.words.length ? res.hits.slice(0, MAX) : res.hits;
    out.textContent = "";
    var count = res.hits.length + (res.words.length ? " résultat(s)" : " tâche(s)");
    if (shown.length < res.hits.length) count += " — " + MAX + " premiers affichés";
    out.appendChild(el("p", "wiki-search-count", count));
    var ul = el("ul", "wiki-search-list");
    shown.forEach(function (h) {
      var e = h.e;
      var li = el("li");
      var a = el("a");
      a.href = e.path;
      highlight(a, "#" + e.id + " — " + e.title, res.words);
      li.appendChild(a);
      li.appendChild(el("span", "wiki-search-section", e.section));
      var sn = res.words.length ? snippet(e, res.words) : null;
      if (sn) li.appendChild(sn);
      ul.appendChild(li);
    });
    out.appendChild(ul);
    try {
      history.replaceState(null, "", q ? "?q=" + encodeURIComponent(q) : location.pathname);
    } catch (_err) {
      // file:// — some browsers refuse replaceState; the search still works.
    }
  }

  input.value = new URLSearchParams(location.search).get("q") || "";
  input.addEventListener("input", render);
  input.focus();
  render();
})();
"""
