# 🚀 Pad 500 km/h — Cyber-Glass V6 "Flow FX" (animacioni i butë)

Bir, ja çfarë të bëra 😄 — modit tënd **Gimmick Pad (Dashplate) i mathkuro** i shtova një
**animacion të butë (smooth) "energy flow"** vetëm në pad-in **500 km/h Cyber-Glass** që ti e ke me teksturë të re.

## Çfarë është shtuar

Një **shtresë e re shkëlqimi** mbi qelqin cyber: vija energjie cian/jeshile që **rrjedhin butësisht e pa ndalim**
drejt drejtimit përpara të pad-it (si tunele shpejtësie), gjithmonë në loop — pa kërc, pa ndërprerje, 60fps smooth.
Tekstura është **seamless** (tile 1024×1024 e ndërtuar apposht që loop-i të jetë i padukshëm).

- Si duket: shiko `preview_500kmh_flow_fx.gif` 🎬
- Stilistikisht ndjek paletën tënde cyber-glass (cyan / electric blue / ice white) dhe nuk e mbulon pamjen ekzistuese — vetëm shton dritë që lëviz.

## Skedarët

| Skedari | Ndryshimi |
|---|---|
| `vehicles/dashplate_mathkuro/skins/dashplate_flat_500kmh_cyberglass_flow_b.color.png` | **I RI** — tekstura seamless e vijave të energjisë (RGBA) |
| `vehicles/dashplate_mathkuro/dashplate_flat_500kmh_cyberglass_flow.dae` | **I RI** — quad shtresa 5mm mbi qelq |
| `vehicles/dashplate_mathkuro/main.materials.json` | **+1 material** `dashplate_flat_500kmh_cyberglass_flow` (version 1, `animFlags: scroll`, `scrollSpeed: 0.5`) |
| `vehicles/dashplate_mathkuro/dashplate_flat.jbeam` | shtresa e re e lidhur në mesh-slotin `dashplate_flat_mesh_500kmh_cyberglass` |

Gjithçka tjetër mbeti **identike bajt me bajt** me V5 — tekstura jote e qelqit s'ka prekur fare.

## Instalimi

1. Hiq zip-in e vjetër (`..._V5_UV_FIXED.zip`) nga `Documents/BeamNG.drive/mods/`
2. Vendos `dashplate_mathkuro_500KMH_CYBER_GLASS_V6_FLOW_FX.zip` aty
3. Spawn **Boost (500km/h, 310mph)** si zakonisht — FX-i shfaqet vetë (është në config default)

## Si ta rregullosh shpejtësinë

Në `vehicles/dashplate_mathkuro/main.materials.json` → materiali `dashplate_flat_500kmh_cyberglass_flow`:

- **Shpejtësia e rrjedhës**: `"scrollSpeed": 0.5` → 0.3 = më ngadalë/e qetë, 0.8 = më aggressive
- **Drejtimi**: `"scrollDir": [0, 1]` → `[0, -1]` e kthen përmbys (nëse të pëlqen më shumë kundër)

Shpejtësia 0.5 = një kalim i plotë përtej pad-it çdo 2 sekonda.

## Notë teknike (sinqerisht)

Animacioni përdor sistemin e vjetër (material **version 1**, `animFlags` scroll) — i njëjti sistem që
BeamNG e mban në Material Editor ("Animation Properties"). Nëse ndonjë version i lojës e injoron
animacionin në flexbody, pad-i thjesht mbetet siç është tani (shtresa statike e vijave — prapë bukur):
**nuk ka asnjë mënyrë që të prishet ndonjë gjë**, modi funksionon normal.
