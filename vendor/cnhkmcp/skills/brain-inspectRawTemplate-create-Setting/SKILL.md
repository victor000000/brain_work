---
name: brain-inspectRawTemplate-create-setting
description: >-
  This skill is to inspect raw BRAIN template only, it has nothing to do with enhanced templates. do not use it for enhanced templates.
  Reads a BRAIN template/idea JSON (template/idea/expression_list) like
  fundamental28_GLB_1_idea_<timestamp>.json, fetches valid simulation setting options
  via ace_lib.get_instrument_type_region_delay, resolves region/delay/universe/neutralization,
  and builds an Alpha list JSON (one Alpha per expression) using ace_lib.generate_alpha.
  Use when user asks to inspect template files, attach settings, create alpha list, or validate settings.
user-invocable: true
---

# brain-inspectRawTemplate-create-Setting

This skill is designed for *stable, repeatable runs*.

## Deterministic vs AI responsibilities

Deterministic (scripts):
- **Entry Point**: `scripts/process_template.py` handles the initial flow (Part 1).
- **Part 1 Output**: `settings_candidates.json` containing valid platform options for the detected Region/Delay.
- **Part 2 Output**: `alpha_list.json` (generated iteratively by AI).

AI reasoning (Critical Step):
- **Input**: The AI must read `idea_context.json` (to understand intent) AND `settings_candidates.json` (to see valid options).
- **Loop**: The AI can decide on **multiple** setting combinations if the idea is ambiguous or worth testing broadly.
  - e.g., Run 1: `Universe=TOP3000`, `Neutralization=INDUSTRY`
  - e.g., Run 2: `Universe=TOPDIV3000`, `Neutralization=MARKET`
- **Context**: There are two kinds of Netralization in BRAIN:
  - `Market Investment Neutralization`: Neutralizes to make a net-zero investment within a market peers, or industry peers, or subindustry peers, or exchanges peers.
  - `Risk Neutralization`: Neutralizes against predefined risk factors in BRAIN, such as Barra 'SLOW' factors, Barra 'FAST' factors, 'CROWDING' factors, ect. that you can choose from the `settings_candidates.json`.
  - You can not set neutralization as None even though some templates may look like they do not require neutralization. You must always choose a valid neutralization option, in such a cases, you can use a proper Risk Neutralization setting.
  - `Decay`: This is a time linear decay apply to your Alpha signals, it can smooth out short-term fluctuations but may also reduce responsiveness to market changes.
  - You should choose wisesly based on the template's idea and intent.
- **Action**: For EACH chosen setting, call `scripts/build_alpha_list.py` passing the settings as a JSON string.
  - The script will **APPEND** to `alpha_list.json`, allowing comprehensive test coverage.

## Config / credentials check (startup)

To connect to BRAIN API (only needed for fetching sim options), provide credentials via one of:
1) Environment variables: `BRAIN_USERNAME` (or `BRAIN_EMAIL`) and `BRAIN_PASSWORD`
2) `config.json` next to this file (see `config.example.json`)
3) `~/secrets/platform-brain.json` (keys: `email`/`password`)

Never commit real credentials. Keep `config.json` local.

## Run steps

**Important**: Always navigate to the skill directory first, as scripts rely on relative paths.

### One-click Processing (Recommended)
1. **Navigate to skill folder**:
   `cd "path/to/brain-inspectTemplate-create-Setting"`

2. **Run wrapper script**:
   Use the wrapper script to generate all artifacts in a dedicated folder (e.g., `processed_templates/<filename>/`).

   `C:/Python313/python.exe scripts/process_template.py --file <absolute_path_to_input_json>`

   *Example*:
   `C:/Python313/python.exe scripts/process_template.py --file "C:/Users/user/Downloads/fundamental28_GLB_1_idea_...json"`

This will:
1. Parse the idea file.
2. Fetch simulation options (if `sim_options_snapshot.json` missing in root).
3. Resolve settings.
4. Generate the Alpha list.

### Manual Steps (Debug)

From this folder:

1) Parse idea JSON
- `C:/Python313/python.exe scripts/parse_idea_file.py --input fundamental28_GLB_1_idea_1769874845978315000.json --out idea_context.json`

2) Fetch sim options snapshot (requires credentials)
- `C:/Python313/python.exe scripts/fetch_sim_options.py --out sim_options_snapshot.json`

3) Resolve settings
- `C:/Python313/python.exe scripts/resolve_settings.py --idea idea_context.json --options sim_options_snapshot.json --out resolved_settings.json`

4) Build alpha list
- `C:/Python313/python.exe scripts/build_alpha_list.py --idea idea_context.json --settings resolved_settings.json --out alpha_list.json`
