# trailSomeAlphas

This folder is the runnable pipeline hub for:
- idea generation (`run_pipeline.py`)
- template implementation to expressions (`implement_idea.py` via scripts)

It bundles `brain-data-feature-engineering` and `brain-feature-implementation` so idea generation and implementation can run end-to-end.

## Major Features

### 1) Pipeline generation (`run_pipeline.py`)
- Generate idea report markdown from dataset metadata
- Parse implementation examples and produce expression candidates
- Save final expressions under dataset folder

## Setup

1) Configure BRAIN credentials (for dataset fetch/rebuild when needed)
- `skills/brain-feature-implementation/config.json`

2) Set Moonshot API key (recommended via env)
- PowerShell:
  - `$Env:MOONSHOT_API_KEY = "YOUR_CREDENTIAL"`

Optional:
- `MOONSHOT_BASE_URL` (default: `https://api.moonshot.cn/v1`)
- `MOONSHOT_MODEL` (default from script)

## Run

From this folder (`untracked/skills/brain-makeSomeGem/trailSomeAlphas`):

### Pipeline mode
- Generate ideas + implement expressions:
  - `python run_pipeline.py --data-category analyst --region USA --delay 1 --dataset-id analyst45 --universe TOP3000 --instrument-type EQUITY --data-type MATRIX`
- Use existing ideas markdown:
  - `python run_pipeline.py --data-category analyst --region USA --delay 1 --dataset-id analyst45 --ideas-file <path_to_ideas.md> --universe TOP3000 --instrument-type EQUITY --data-type MATRIX`

## Validation Rules (implemented in flow)

- Input markdown must contain `**Concept**` blocks with `**Implementation Example**`
- `--dataset-id` is required
- `--data-type` accepts only `MATRIX` or `VECTOR`
- Dataset CSV is ensured/readable before implementation

## Output

### Pipeline outputs
- Ideas report:
  - `skills/brain-data-feature-engineering/output_report/{region}_delay{delay}_{datasetId}_ideas.md`
- Final expressions:
  - `skills/brain-feature-implementation/data/{datasetId}_{region}_delay{delay}/final_expressions.json`
