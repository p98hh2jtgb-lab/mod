# 🚀 Pad 500 km/h — Cyber-Glass **V7 XL** (pad i madh + dizajn i ri + animacion ma i shpejtë)

Bir, ja V7 😄 — tani pad-i i 500km/h është bërë **pistë e vërtet**:

## Çfarë ndryshoi nga V6

### 📏 Madhësia & forma
- Nga katror 4×4m → **3m anash × 9m gjatë përpara** (format pistë, 1:3)
- Mesh i ri `dashplate_flat_body_xl` — pjesa tjetër e modit mbetet e paprekur
- **Rrezja e detektimit** u bë e rregullueshme për pad (`$dashplateTriggerRadius`, default 3m)
  - Pad-i 500km/h e ka **6m** që ta kapë makinën në çdo pikë të pistës 9m — pa mbetur "zonë të vdekura"
  - Edhe në Tuning menu tani e ka si slider (3–15m)!

### 🎨 Dizajni i ri modern
- Dizajn komplett i ri "runway cyber": **chuckrona neon** drejt përparit, **"500" segment-style** me glow,
  **km/h**, shina anash me energy-dashes, corner brackets HUD, micro-grid, launch bar përpara e entry bar pas
- Marginat jashtë frame-it janë transparente (look "qelq placi" si ai që të pëlqen)
- I përshtatur formatit të ri 1:3 — asgjë s'shtrejtohet

### ⚡ Animacioni
- Vija e energjisë rrjedh **30% ma shpejt** (`scrollSpeed` 0.5 → **0.65**) — ende smooth, tani ma dinamike

## Instalimi
1. Hiq V6 nga `Documents/BeamNG.drive/mods/`
2. Vendos `dashplate_mathkuro_500KMH_CYBER_GLASS_V7_XL_FLOW.zip`
3. Spawn **Boost (500km/h, 310mph)** — gjithçka e re del vetë (është në config default)

## Rregullime të shpejta
| Çfarë | Ku | Vlera |
|---|---|---|
| Shpejtësia e animacionit | `main.materials.json` → `scrollSpeed` | 0.65 (0.4 ngadalë / 1.0 furioze) |
| Rrezja e trigger-it | në lojë: **Tuning → Trigger Radius**, ose në `.pc` → `$dashplateTriggerRadius` | 6 m |
| Madhësia e pad-it | `dashplate_flat.jbeam` → `dashplate_flat_body_xl` nodes | X ±1.5, Y ±4.5 |

## Notë teknike
- Vetëm config-i **500km/h** merr trupin XL — pjesët tjera (100/200/300km/h etj.) mbeten 4×4m siç ishin.
- Nëse ndonjë version loje e injoron UV-animacionin, pad-i mbetet statik (prapë bukur) — asgjë nuk prishet.
