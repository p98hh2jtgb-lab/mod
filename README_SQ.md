# 🚀 Gimmick Pad — **KMH FAMILY V15** (+ STEEL STUNT RAMP!)
> **V15:** Rampë stunt e vërtetë çeliku: 3 module (8°/18°/30°) me kalim të butë nga toka, sipërfaqe steel me vijë qendrore të bardhë, kornizë anësore me trarë + brace diagonale + pika saldimi, drita amber të animuara buzëve. Kolizioni 100% = pamja (nyjet në qepjet e moduleve).
> **V14:** MEGA RAMP 10×25m (~20°) me **mure anësore të animuara** (streaks magenta që vrapojnë sipër mureve) — stili Hyperjump X-Games.
> **V13:** U gjet bug-u i vërtetë i DAE-ve të gjeneruara (format i `<p>` indekseve) dhe u ndreq — tani të gjitha mesh-at e gjeneruara ndjekin konventën byte-për-byte të origjinalit.
> **V11:** të 5 pad-at tani janë **klone ekzakte të pad-it 500 km/h që të punon** — i njëjti trup 6×18m, i njëjta strukturë e provuar; ndryshojnë vetëm kmh, look-i dhe animacioni.

Bir, V10 😄 — tani modi ka **vetëm 5 pad-a: 100 / 200 / 300 / 500 / 1000 km/h**, secili me stil, madhësi e animacion të vetin!

## 🚀 JUMP Ramp (500km/h) — Hyperjump
- **Rampë FIZIKE 8×20m (~19°), më e madhe se pad-i 500** — hyn nga mbrapa, dash-i 500 km/h të ngjet nëpër të dhe **FLUTRON**
- Stil i re **Hyperjump magenta**: shigjeta dyfish lart, "JUMP", sparks + **animacion i re 2.0** (magenta flow)
- Rrezja 12m, rampa e nisjes 0.6s
- Bonus: edhe mesh-i bazë i pad-it 500 u ndregjua (përshkrimi më lart)

## 🛫 Boost (500km/h) — Ramp Launch
- **Klon i saktë i pad-it 500 që punon** (i njëjti trup, i njëjti skin, i njëjti animacion) — pa asnjë pjesë të re fizike
- "Rampa" = **këndi i lëshimit 14° lart** (funksionaliteti ekzistues `$verticalAngleDegree` i modit): makina qëllitet me 500 km/h drejt pjerrtë → **fluton ~800m!**
- Këndin e ndryshon brenda lojës: **Tuning → Vertical Angle** (0–90°, provo 30° për flutim vertikal!)

## 🎯 Lëshimi (rregulluar)
- Nuk është më "shumë i butë": **500 km/h tani 0.6s** (ishte 1.6s) — hov i shpejt por jo instant
- Secilit pad iu dha rampë sipas shpejtësisë: 100→0.45s, 200→0.5s, 300→0.55s, 500→0.6s, 1000→0.8s
- E rregullueshme: **Tuning → Launch Smoothness**

## 👨‍👩‍👧‍👦 Familja

| Pad | Stili | Madhësia | Animacioni | Ngjyra |
|---|---|---|---|---|
| **100** | Pulse | 2×3m | pulse bands që ecin ngadalë | 🟢 jeshile |
| **200** | Strike | 2.5×4.5m | rrjeka diagonale | 🟡 ambër |
| **300** | Afterburn | 3×6m | vija anash (sideways sweep) | 🔴 e kuqe |
| **500** | Cyber-Glass (**e paprekur**) | 6×18m | flow 1.5 drejt shigjetave | 🔵 cyan |
| **1000** | Warp | 8×24m GIGANTE | warp streaks 2.6 (më e shpejta!) | 🟣 vjollcë |

Secili ka dizajn të vetin (chuckrona, numra, motive) + teksturë animacioni unike + madhësi unike + rreze detektimi të përshtatme.

## 🧹 Fshirjet
- 27 configs të tjera u fshinë (jump, teleport, tornado, fireworks, random, etj...)
- skins-t e papërdorura, slope, UI app e Random — **131 files u fshinë**
- Kodi lua i motorrit mbeti i plotë (siguria e funksionimit)

## Instalimi
1. Fshij V9 nga `Documents/BeamNG.drive/mods/`
2. Vendos `dashplate_mathkuro_KMH_FAMILY_V15_STUNTRAMP.zip`
3. Spawn nga Props → Gimmick Pad: **Boost (100km/h) — Pulse**, **— Strike**, **— Afterburn**, **(500km/h) XL**, **(1000km/h) — Warp**

> Emrat në selector tani kanë stilin pas tyre — ashtu e di që V10 është live. Cache clear nëse loja të mban të vjetrin!

## Preview
`preview_pad_family_V10.gif` — të 5 pad-at animated krahas krahas.
