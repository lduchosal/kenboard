// =============================================================================
// PROJECT DASHBOARD — v0.2 — Burndown cards
// =============================================================================

#set page(
  width: 420mm,
  height: 297mm,
  margin: (top: 8mm, bottom: 8mm, left: 8mm, right: 8mm),
  fill: rgb("#0f1117"),
)

#set text(font: "Helvetica Neue", size: 8pt, fill: rgb("#c9d1d9"))

// -- Couleurs ----------------------------------------------------------------
#let bg-card = rgb("#161b22")
#let border  = rgb("#30363d")
#let accent  = rgb("#58a6ff")
#let green   = rgb("#3fb950")
#let orange  = rgb("#d29922")
#let red     = rgb("#f85149")
#let purple  = rgb("#bc8cff")
#let cyan    = rgb("#39d3f5")
#let dimmed  = rgb("#8b949e")
#let white   = rgb("#e6edf3")

// Couleurs catégories
#let cat-colors = (
  "immobilier": orange,
  "sante":      green,
  "technique":  accent,
  "famille":    purple,
)

// -- Helpers -----------------------------------------------------------------
#let card(width: 100%, height: auto, body) = block(
  width: width, height: height, fill: bg-card,
  radius: 6pt, stroke: 0.5pt + border, inset: 8pt, body,
)

#let badge(label, color) = box(
  fill: color.transparentize(85%), radius: 3pt,
  inset: (x: 5pt, y: 2pt),
  text(fill: color, weight: "semibold", size: 6pt, label),
)

#let progress-bar(ratio, color: green, width: 100%) = block(
  width: width, height: 3pt, radius: 1.5pt, fill: border,
  block(width: ratio * 100%, height: 3pt, radius: 1.5pt, fill: color),
)

// Burndown chart — barres ideal (vert) vs reel (rouge)
#let burndown-chart(ideal, actual, height: 40pt) = {
  let max-val = calc.max(..ideal)
  let n = ideal.len()
  align(center, grid(
    columns: n * (1fr,), column-gutter: 1.5pt,
    ..ideal.zip(actual).map(pair => {
      let (i, a) = pair
      let ch = 28
      let ih = int(i / max-val * ch)
      let ah = int(a / max-val * ch)
      stack(dir: ttb,
        v(float(ch - calc.max(ih, ah)) * 1pt),
        if ih > ah { block(width: 100%, height: float(ih - ah) * 1pt, fill: green.transparentize(60%), radius: 1pt) },
        block(width: 100%, height: float(calc.min(ih, ah)) * 1pt, fill: accent.transparentize(60%), radius: 1pt),
        if ah > ih { block(width: 100%, height: float(ah - ih) * 1pt, fill: red.transparentize(40%), radius: 1pt) },
      )
    })
  ))
}

// -- Données -----------------------------------------------------------------
#let projects = (
  // Immobilier
  (name: "Renovation appart",   cat: "immobilier", progress: 0.65, tasks: (done: 13, total: 20), due: "2026-06-15",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,19,17,15,14,12,10,9,8,7,7)),
  (name: "Recherche terrain",   cat: "immobilier", progress: 0.30, tasks: (done: 3,  total: 10), due: "2026-09-01",
   ideal: (10,9,8,7,6,5,4,3,2,1,0), actual: (10,10,9,9,8,8,7,7,7,7,7)),
  (name: "Dossier hypotheque",  cat: "immobilier", progress: 0.80, tasks: (done: 8,  total: 10), due: "2026-05-01",
   ideal: (10,9,8,7,6,5,4,3,2,1,0), actual: (10,9,7,6,5,4,3,3,2,2,2)),

  // Santé
  (name: "Bilan annuel",        cat: "sante",      progress: 0.50, tasks: (done: 3,  total: 6),  due: "2026-04-30",
   ideal: (6,5,4,4,3,2,1,1,0,0,0), actual: (6,6,5,5,4,4,3,3,3,3,3)),

  // Technique
  (name: "2113.ch Website",     cat: "technique",  progress: 0.72, tasks: (done: 18, total: 25), due: "2026-05-15",
   ideal: (25,23,20,18,15,13,10,8,5,3,0), actual: (25,24,22,20,18,15,13,10,9,7,7)),
  (name: "Infra Ansible",       cat: "technique",  progress: 0.45, tasks: (done: 9,  total: 20), due: "2026-06-30",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,19,18,17,16,14,13,12,11,11,11)),
  (name: "Monitoring Stack",    cat: "technique",  progress: 0.30, tasks: (done: 6,  total: 20), due: "2026-04-30",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,20,19,18,17,16,15,15,14,14,14)),
  (name: "SSL/PKI Renewal",     cat: "technique",  progress: 0.85, tasks: (done: 17, total: 20), due: "2026-04-20",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,18,15,12,10,8,6,5,4,3,3)),
  (name: "Kanban Dashboard",    cat: "technique",  progress: 0.05, tasks: (done: 1,  total: 20), due: "2026-07-01",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,20,20,20,20,20,20,20,20,19,19)),
  (name: "Backup Strategy",     cat: "technique",  progress: 0.55, tasks: (done: 11, total: 20), due: "2026-08-01",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,18,16,14,12,11,10,10,9,9,9)),
  (name: "Migration FreeBSD",   cat: "technique",  progress: 0.20, tasks: (done: 4,  total: 20), due: "2026-07-15",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,20,19,19,18,18,17,17,16,16,16)),
  (name: "CI/CD Pipeline",      cat: "technique",  progress: 0.10, tasks: (done: 2,  total: 20), due: "2026-08-15",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,20,20,20,19,19,19,18,18,18,18)),
  (name: "API v2",              cat: "technique",  progress: 0.60, tasks: (done: 12, total: 20), due: "2026-05-30",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,19,17,15,13,11,10,9,8,8,8)),
  (name: "Docs techniques",     cat: "technique",  progress: 0.40, tasks: (done: 8,  total: 20), due: "2026-06-15",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,19,18,17,16,14,13,13,12,12,12)),

  // Famille
  (name: "Vacances ete",        cat: "famille",    progress: 0.35, tasks: (done: 7,  total: 20), due: "2026-07-01",
   ideal: (20,18,16,14,12,10,8,6,4,2,0), actual: (20,19,18,17,16,15,14,13,13,13,13)),
)

// -- Health indicator --------------------------------------------------------
#let health(p) = {
  // Compare actual vs ideal at current point
  let last-ideal = p.ideal.last()
  let last-actual = p.actual.last()
  let total = p.tasks.total
  if last-actual <= last-ideal + 1 { (sym.arrow.t, green, "on track") }
  else if last-actual <= last-ideal + calc.round(total * 0.2) { (sym.arrow.tr, orange, "at risk") }
  else { (sym.arrow.b, red, "behind") }
}

// =============================================================================
// HEADER — une seule ligne
// =============================================================================
#grid(
  columns: (auto, 1fr, auto, auto, auto, auto, auto),
  column-gutter: 12pt,
  align: (left + horizon,) * 7,
  text(fill: white, weight: "bold", size: 14pt)[DASHBOARD],
  [],
  [#text(fill: dimmed, size: 7pt)[15 projets] #h(3pt) #badge("S15 — 2026", dimmed)],
  [#badge("IMMOBILIER", orange) #text(fill: dimmed, size: 7pt)[ 3]],
  [#badge("SANTE", green) #text(fill: dimmed, size: 7pt)[ 1]],
  [#badge("TECHNIQUE", accent) #text(fill: dimmed, size: 7pt)[ 10]],
  [#badge("FAMILLE", purple) #text(fill: dimmed, size: 7pt)[ 1]],
)

#v(6pt)

// =============================================================================
// PROJECT CARDS — 4 colonnes × 4 lignes
// =============================================================================

// Sort: by category order, then by progress descending
#let cat-order = ("immobilier", "sante", "technique", "famille")
#let sorted-projects = projects.sorted(key: p => {
  let ci = cat-order.position(c => c == p.cat)
  ci * 1000 - int(p.progress * 100)
})

// Pad to 16 if needed
#let padded = sorted-projects
#while padded.len() < 16 { padded.push(none) }

#let card-h = 65pt

#grid(
  columns: (1fr,) * 4,
  rows: (card-h,) * 4,
  column-gutter: 5pt,
  row-gutter: 5pt,
  ..padded.slice(0, 16).map(p => {
    if p == none {
      // Empty slot
      block(width: 100%, height: card-h, fill: bg-card.transparentize(50%), radius: 6pt, stroke: 0.3pt + border)
    } else {
      let cc = cat-colors.at(p.cat)
      let (arrow, hcolor, hlabel) = health(p)
      let remaining = p.tasks.total - p.tasks.done
      let due-soon = p.due < "2026-05-01"

      block(
        width: 100%, height: card-h, fill: bg-card, radius: 6pt,
        stroke: (left: 3pt + cc, top: 0.5pt + border, right: 0.5pt + border, bottom: 0.5pt + border),
        inset: (left: 10pt, top: 5pt, right: 6pt, bottom: 3pt),
        clip: true,
      )[
        // Row 1: name + health + due
        #grid(
          columns: (1fr, auto, auto),
          column-gutter: 3pt,
          align: (left + horizon, center + horizon, right + horizon),
          text(fill: white, weight: "semibold", size: 7.5pt, p.name),
          text(fill: hcolor, size: 7pt, arrow),
          { let dc = if due-soon { red } else { dimmed }; text(fill: dc, size: 6pt, p.due) },
        )
        #v(1pt)
        // Row 2: progress bar + fraction
        #grid(
          columns: (1fr, auto), column-gutter: 3pt,
          align: (left + horizon, right + horizon),
          progress-bar(p.progress, color: if p.progress > 0.7 { green } else if p.progress > 0.4 { accent } else { orange }),
          text(fill: dimmed, size: 5.5pt)[#{p.tasks.done}/#{p.tasks.total}],
        )
        #v(1pt)
        // Row 3: burndown
        #burndown-chart(p.ideal, p.actual, height: 28pt)
      ]
    }
  })
)
