from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
PYTHON_EXE = sys.executable

def run_step(script_name: str, args: list[str]) -> None:
    """Run a script from the scripts directory with the given arguments."""
    script_path = SCRIPTS_DIR / script_name
    cmd = [PYTHON_EXE, str(script_path)] + args
    print(f"Running: {script_name} {' '.join(args)}")
    try:
        subprocess.run(cmd, check=True, cwd=SKILL_DIR)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        sys.exit(1)

def main() -> None:
    parser = argparse.ArgumentParser(description="Process a single template file and generate artifacts in a dedicated folder.")
    parser.add_argument("--file", required=True, help="Path to the input idea JSON file.")
    parser.add_argument("--force-fetch-options", action="store_true", help="Force fetching new simulation options even if snapshot exists.")
    args = parser.parse_args()

    input_path = Path(args.file).resolve()
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # 1. Create output directory
    output_dir = SKILL_DIR / "processed_templates" / input_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # 2. Parse idea file
    idea_context_path = output_dir / "idea_context.json"
    run_step("parse_idea_file.py", ["--input", str(input_path), "--out", str(idea_context_path)])

    # 3. Handle Simulation Options
    # Strategy: Use shared snapshot in skill root if available to save time/network, unless forced.
    global_options_path = SKILL_DIR / "sim_options_snapshot.json"
    
    if args.force_fetch_options or not global_options_path.exists():
        print("Fetching simulation options (network required)...")
        run_step("fetch_sim_options.py", ["--out", str(global_options_path)])
    
    # Optional: Copy snapshot to output dir for full reproducibility? 
    # Let's verify if the user wants strictly isolated execution. 
    # For now, we pass the global path to resolve_settings.
    
    # 4. Resolve Candidates (Not final choice)
    candidates_path = output_dir / "settings_candidates.json"
    run_step("resolve_settings.py", [
        "--idea", str(idea_context_path),
        "--options", str(global_options_path),
        "--out", str(candidates_path)
    ])

    print("\n-------------------------------------------------------------")
    print("STEP 1 COMPLETE: Candidates Generated")
    print(f"Candidates file: {candidates_path}")
    print("-------------------------------------------------------------")
    print("ACTION REQUIRED FOR AI/AGENT:")
    print("1. Read 'idea_context.json' (for intent) and 'settings_candidates.json' (for valid options).")
    print("2. Decide on ONE OR MORE combinations of settings (Universe, Neutralization, Decay, NaN).")
    print("3. For EACH chosen setting combination, run 'build_alpha_list.py' directly with JSON string:")
    print(f"   python scripts/build_alpha_list.py --idea {idea_context_path} --out {output_dir}/alpha_list.json --settings_json '{{...json...}}'")
    print("   (The script will APPEND new alphas to alpha_list.json)")
    print("-------------------------------------------------------------")

    # Stop here to let AI decide.
    sys.exit(0)

if __name__ == "__main__":
    main()
