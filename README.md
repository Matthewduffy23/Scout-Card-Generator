# Scouting Card Generator

Generates a 1920×1080 player scouting card matching the Canva template.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage

1. Place your season CSVs in the same folder (e.g. `2025-26WORLDFULL.csv`)
2. Select the CSV from the dropdown
3. Fill in the player form (auto-fills percentile bars from CSV)
4. Upload a position diagram image per position
5. Click **Generate Card** → Download PNG

## Auto-filled from CSV
- All Feature F bar chart percentile ranks (vs same league pool)

## Manually entered per player
- Key Attributes, Development Areas, Scout View
- Physical dots (Pace/Power/Fitness 1–5)
- Form colours (W/D/L)
- Role scores
- Current/Potential level + stars
- Club colour hex (for header gradient)
- Position diagram image
