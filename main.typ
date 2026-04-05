// =============================================================================
// PROJECT DASHBOARD — MAQUETTE v0.1 — SINGLE PAGE A3 LANDSCAPE
// =============================================================================

#set page(
  width: 420mm,
  height: 297mm,
  margin: (top: 10mm, bottom: 8mm, left: 10mm, right: 10mm),
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

// -- Helpers -----------------------------------------------------------------
#let card(width: 100%, height: auto, body) = block(
  width: width, height: height, fill: bg-card,
  radius: 6pt, stroke: 0.5pt + border, inset: 8pt, body,
)

#let badge(label, color) = box(
  fill: color.transparentize(85%), radius: 3pt,
  inset: (x: 5pt, y: 2pt),
  text(fill: color, weight: "semibold", size: 6.5pt, label),
)

#let stat-big(value, label, color: accent) = align(center)[
  #text(fill: color, weight: "bold", size: 18pt, value) \
  #text(fill: dimmed, size: 6pt, upper(label))
]

#let progress-bar(ratio, color: green, width: 100%) = block(
  width: width, height: 4pt, radius: 2pt, fill: border,
  block(width: ratio * 100%, height: 4pt, radius: 2pt, fill: color),
)

#let spark-bar(values, color: accent, bar-width: 4pt, height: 32pt) = {
  let max-val = calc.max(..values)
  let bars = values.map(v => {
    let h = if max-val > 0 { v / max-val * 100% } else { 0% }
    box(width: bar-width, height: height,
      align(bottom, block(width: 100%, height: h, fill: color, radius: 1.5pt)))
  })
  stack(dir: ltr, spacing: 2pt, ..bars)
}

#let dot(color) = box(circle(fill: color, radius: 3pt))

// -- Data --------------------------------------------------------------------
#let projects = (
  (name: "2113.ch Website",        status: "active",  progress: 0.72, tasks: (done: 18, total: 25), velocity: (3,5,4,7,6,8,5,9,7,6,8,10), backlog: 7,  in-progress: 3, review: 2, done: 18, due: "2026-05-15"),
  (name: "Infrastructure Ansible", status: "active",  progress: 0.45, tasks: (done: 9,  total: 20), velocity: (1,2,1,3,2,1,4,2,3,2,1,3),  backlog: 8,  in-progress: 2, review: 1, done: 9,  due: "2026-06-30"),
  (name: "Monitoring Stack",       status: "blocked", progress: 0.30, tasks: (done: 6,  total: 20), velocity: (2,3,1,0,0,1,2,0,1,0,2,1),  backlog: 10, in-progress: 1, review: 3, done: 6,  due: "2026-04-30"),
  (name: "SSL/PKI Renewal",        status: "active",  progress: 0.85, tasks: (done: 17, total: 20), velocity: (5,4,6,3,5,7,4,6,5,3,4,2),  backlog: 1,  in-progress: 1, review: 1, done: 17, due: "2026-04-20"),
  (name: "Kanban Dashboard",       status: "new",     progress: 0.05, tasks: (done: 1,  total: 20), velocity: (0,0,0,0,0,0,0,0,0,0,0,1),  backlog: 15, in-progress: 3, review: 1, done: 1,  due: "2026-07-01"),
  (name: "Backup Strategy",        status: "paused",  progress: 0.55, tasks: (done: 11, total: 20), velocity: (3,4,2,3,1,0,0,0,0,0,0,0),  backlog: 4,  in-progress: 0, review: 5, done: 11, due: "2026-08-01"),
)

#let status-color(s) = {
  if s == "active" { green } else if s == "blocked" { red }
  else if s == "paused" { orange } else if s == "new" { cyan } else { dimmed }
}

// =============================================================================
// HEADER (fixed ~22pt)
// =============================================================================
#grid(
  columns: (1fr, auto),
  align: (left + horizon, right + horizon),
  [
    #text(fill: white, weight: "bold", size: 16pt)[PROJECT DASHBOARD]
    #h(8pt)
    #text(fill: dimmed, size: 8pt)[6 projets — S15, 2026]
  ],
  [
    #text(fill: dimmed, size: 7pt)[2026-04-05 15:42 CET]
    #h(6pt)
    #badge("LIVE", green)
  ],
)

#v(5pt)

// =============================================================================
// ROW 1 — KPIs (fixed 42pt)
// =============================================================================
#grid(
  columns: (1fr,) * 6,
  column-gutter: 5pt,
  ..("6", "125", "62", "10", "13", "3").zip(
    ("Projets", "Taches", "Terminees", "En cours", "En revue", "Bloquees")
  ).zip(
    (accent, white, green, cyan, purple, red)
  ).map(((pair, color)) => {
    let (value, label) = pair
    card(height: 40pt)[#stat-big(value, label, color: color)]
  })
)

#v(5pt)

// =============================================================================
// ROW 2 — Graphs (fixed 80pt)
// =============================================================================
#grid(
  columns: (2fr, 2fr, 1fr),
  column-gutter: 5pt,

  card(height: 80pt)[
    #text(fill: dimmed, size: 6pt, weight: "semibold")[VELOCITY — 12 SEMAINES]
    #v(3pt)
    #align(center, spark-bar((14,18,14,13,13,17,15,17,16,11,15,17).map(v => float(v)), color: accent, bar-width: 18pt, height: 44pt))
    #v(2pt)
    #align(center, text(fill: dimmed, size: 5.5pt)[S4 #h(7pt) S5 #h(7pt) S6 #h(7pt) S7 #h(7pt) S8 #h(7pt) S9 #h(6pt) S10 #h(5pt) S11 #h(5pt) S12 #h(5pt) S13 #h(5pt) S14 #h(5pt) S15])
  ],

  card(height: 80pt)[
    #text(fill: dimmed, size: 6pt, weight: "semibold")[BURNDOWN GLOBAL]
    #v(3pt)
    #let ideal =  (125, 115, 104, 94, 83, 73, 62, 52, 42, 31, 21, 10, 0)
    #let actual = (125, 120, 112, 105, 95, 88, 78, 72, 68, 63, 60, 55, 50)
    #align(center, grid(
      columns: 13 * (1fr,), column-gutter: 2pt,
      ..ideal.zip(actual).map(pair => {
        let (i, a) = pair
        let max-h = 42
        let ih = int(i / 125 * max-h)
        let ah = int(a / 125 * max-h)
        stack(dir: ttb,
          v(float(max-h - calc.max(ih, ah)) * 1pt),
          if ih > ah { block(width: 100%, height: float(ih - ah) * 1pt, fill: green.transparentize(70%), radius: 1pt) },
          block(width: 100%, height: float(calc.min(ih, ah)) * 1pt, fill: red.transparentize(50%), radius: 1pt),
          if ah > ih { block(width: 100%, height: float(ah - ih) * 1pt, fill: red.transparentize(20%), radius: 1pt) },
        )
      })
    ))
    #v(2pt)
    #align(center, text(fill: dimmed, size: 5.5pt)[
      #box(block(width: 6pt, height: 6pt, fill: green.transparentize(70%), radius: 1pt)) Ideal
      #h(6pt)
      #box(block(width: 6pt, height: 6pt, fill: red.transparentize(50%), radius: 1pt)) Reel
      #h(6pt)
      #text(fill: red)[+50 en retard]
    ])
  ],

  card(height: 80pt)[
    #text(fill: dimmed, size: 6pt, weight: "semibold")[PAR STATUT]
    #v(4pt)
    #for (label, count, color) in (("Backlog", 45, dimmed), ("En cours", 10, cyan), ("Revue", 13, purple), ("Fait", 62, green)) {
      grid(
        columns: (38pt, 1fr, 18pt), column-gutter: 3pt,
        align: (left + horizon, left + horizon, right + horizon),
        text(fill: color, size: 6.5pt, label),
        progress-bar(count / 125, color: color),
        text(fill: white, size: 6.5pt, weight: "semibold", str(count)),
      )
      v(3pt)
    }
  ],
)

#v(5pt)

// =============================================================================
// ROW 3 — Project table (auto, ~120pt for 6 rows)
// =============================================================================
#card[
  #text(fill: dimmed, size: 6pt, weight: "semibold")[PROJETS]
  #v(3pt)
  #grid(
    columns: (10pt, 2fr, 50pt, 1.2fr, 36pt, 36pt, 36pt, 36pt, 1fr, 56pt),
    column-gutter: 5pt,
    align: (center, left, left, left, center, center, center, center, left, right),
    ..("", "PROJET", "STATUT", "PROGRESSION", "BACK", "WIP", "REV", "DONE", "VELOCITY", "ECHEANCE").map(h => text(fill: dimmed, size: 5.5pt, weight: "bold", h))
  )
  #v(1pt)
  #line(length: 100%, stroke: 0.3pt + border)
  #v(1pt)
  #for (i, p) in projects.enumerate() {
    let sc = status-color(p.status)
    grid(
      columns: (10pt, 2fr, 50pt, 1.2fr, 36pt, 36pt, 36pt, 36pt, 1fr, 56pt),
      column-gutter: 5pt,
      align: (center + horizon, left + horizon, left + horizon, left + horizon, center + horizon, center + horizon, center + horizon, center + horizon, center + horizon, right + horizon),
      dot(sc),
      text(fill: white, weight: "semibold", size: 7.5pt, p.name),
      badge(upper(p.status), sc),
      stack(dir: ttb, spacing: 1pt,
        progress-bar(p.progress, color: sc),
        text(fill: dimmed, size: 5.5pt)[#{str(int(p.progress * 100))}% — #{p.tasks.done}/#{p.tasks.total}],
      ),
      text(fill: dimmed, size: 7.5pt, weight: "semibold", str(p.backlog)),
      text(fill: cyan, size: 7.5pt, weight: "semibold", str(p.at("in-progress"))),
      text(fill: purple, size: 7.5pt, weight: "semibold", str(p.review)),
      text(fill: green, size: 7.5pt, weight: "semibold", str(p.done)),
      spark-bar(p.velocity.map(v => float(v)), color: sc, bar-width: 3pt, height: 14pt),
      { let c = if p.status == "blocked" { red } else if p.progress > 0.8 { green } else { dimmed }; text(fill: c, size: 7pt, p.due) },
    )
    v(2pt)
    if i < projects.len() - 1 { line(length: 100%, stroke: 0.2pt + border); v(1pt) }
  }
]

#v(5pt)

// =============================================================================
// ROW 4 — Mini Kanbans (fixed 58pt)
// =============================================================================
#grid(
  columns: (1fr,) * 6,
  column-gutter: 5pt,
  ..projects.map(p => {
    let sc = status-color(p.status)
    card(height: 58pt)[
      #grid(columns: (auto, 1fr), column-gutter: 4pt, align: horizon,
        dot(sc), text(fill: white, weight: "semibold", size: 7pt, p.name))
      #v(4pt)
      #grid(columns: (1fr,) * 4, column-gutter: 2pt,
        ..(("Back", p.backlog, dimmed), ("WIP", p.at("in-progress"), cyan), ("Rev", p.review, purple), ("Done", p.done, green)).map(((label, count, color)) =>
          block(width: 100%, fill: color.transparentize(90%), radius: 3pt, inset: 3pt, stroke: 0.5pt + color.transparentize(70%))[
            #align(center)[
              #text(fill: color, weight: "bold", size: 11pt, str(count)) \
              #text(fill: dimmed, size: 5pt, label)
            ]
          ]
        )
      )
    ]
  })
)

#v(5pt)

// =============================================================================
// ROW 5 — Heatmap + Tags + Deadlines (fixed 62pt)
// =============================================================================
#grid(
  columns: (2fr, 1fr, 1fr),
  column-gutter: 5pt,

  card(height: 62pt)[
    #text(fill: dimmed, size: 6pt, weight: "semibold")[ACTIVITE — 16 SEMAINES]
    #v(3pt)
    #let heat-color(v) = {
      if v == 0 { rgb("#161b22") } else if v <= 2 { rgb("#0e4429") }
      else if v <= 4 { rgb("#006d32") } else if v <= 6 { rgb("#26a641") } else { rgb("#39d353") }
    }
    #import calc: rem
    #let data = range(16 * 7).map(i => { let v = rem(i * 7 + 13, 11); if rem(i, 7) >= 5 { calc.min(v, 2) } else { v } })
    #grid(
      columns: (10pt,) + 16 * (1fr,), row-gutter: 1pt, column-gutter: 1pt,
      ..{
        let cells = ()
        for d in range(7) {
          cells.push(text(fill: dimmed, size: 4.5pt, ("L","M","M","J","V","S","D").at(d)))
          for w in range(16) { cells.push(block(width: 100%, height: 5.5pt, fill: heat-color(data.at(w * 7 + d)), radius: 1pt)) }
        }
        cells
      }
    )
  ],

  card(height: 62pt)[
    #text(fill: dimmed, size: 6pt, weight: "semibold")[TAGS]
    #v(4pt)
    #for (label, count, color) in (("infra",3,accent),("web",2,green),("security",1,red),("devops",1,orange),("monitoring",1,purple),("content",1,cyan),("tooling",1,dimmed),("data",1,orange)) {
      badge(label + " " + str(count), color); h(2pt)
    }
  ],

  card(height: 62pt)[
    #text(fill: dimmed, size: 6pt, weight: "semibold")[PROCHAINES ECHEANCES]
    #v(4pt)
    #for (name, date, color, progress) in (("SSL/PKI","20 avr",green,0.85),("Monitoring","30 avr",red,0.30),("2113.ch","15 mai",accent,0.72),("Ansible","30 juin",green,0.45)) {
      grid(columns: (46pt, 1fr, 32pt), column-gutter: 3pt,
        align: (left + horizon, left + horizon, right + horizon),
        text(fill: white, size: 6.5pt, name),
        progress-bar(progress, color: color),
        text(fill: color, size: 6.5pt, weight: "semibold", date))
      v(2pt)
    }
  ],
)
