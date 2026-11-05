---
name: brain-feature-implementation
description: Implements WorldQuant Brain features from an idea markdown file. Downloads dataset and generates alpha expressions defined in the idea.
allowed-tools:
  - Read
  - RunTerminal
  - ManageTodoList
---

# Brain Feature Implementation

## Description
This skill automates the process of converting a WorldQuant Brain idea document (Markdown) into actionable Alpha expressions. It handles dataset downloading and code generation for each distinct idea pattern.

## Scope of Work
*   This skill operates exclusively by manipulating local CSV files using the provided Python scripts.
*   **Do NOT use any WorldQuant Brain MCP tools** (e.g., `brain-api`).
*   **Do NOT write custom Python scripts** (e.g. `python -c ...` or new `.py` files) to check data or generate expressions. You MUST use the `scripts/implement_idea.py` tool.
*   Do not attempt to submit alphas or run simulations on the platform. Focus only on generating the expression files locally.

## Instructions

1.  **Analyze the Idea Document**
    *   Read the provided markdown file.
    *   Extract the following metadata:
        *   **Dataset ID** (e.g., `analyst15`)
        *   **Region** (e.g., `GLB`)
        *   **Delay** (e.g., `1` or `0`)
    *   *If any metadata is missing, ask the user to clarify.*

2.  **Download Dataset**
    *   Execute the fetch script using the extracted parameters.
    *   **Locate Scripts**:
        *   Check your current working directory (`ls -R` or `Get-ChildItem -Recurse`).
        *   Find the path to `fetch_dataset.py`. It is likely in `brain-feature-implementation/scripts` or `scripts`.
    *   **Run Command**:
        *   Change directory to the folder containing the script before running it.
        *   Command:
            ```bash
            cd <PATH_TO_SCRIPTS_FOLDER> && python fetch_dataset.py --datasetid <ID> --region <REGION> --delay <DELAY>
            ```
    *   Wait for the download to complete. The script will create a folder in `../data/`.

3.  **Plan Implementation**
    *   Scan the markdown file for **Feature Definitions** or **Formulas**.
    *   Look for patterns like `Definition: <formula>` or code blocks describing math.
    *   Use the `manage_todo_list` tool to create a plan with one entry for each unique idea/formula found.
        *   *Title*: The Idea Name or ID (e.g., "3.1.1 Estimate Stability Score").
        *   *Description*: The specific template formula (e.g., `template: "{st_dev} / abs({mean})"`).

4.  **Execute Implementation**
    *   For each item in the Todo List:
        *   **Construct the Template**:
            *   Use Python format string syntax `{variable}`.
            *   The `{variable}` must match the **suffix** of the fields in the dataset (e.g., `mean`, `st_dev`, `gro`).
            *   **CRITICAL**: Do NOT include the full prefix or horizon in the template. The script auto-detects these.
            *   *Correct Example*: For `anl15_gr_12_m_gro / anl15_gr_12_m_pe`, use template: `{gro} / {pe}`.
            *   *Incorrect Example*: `{anl15_gr_12_m_gro} / {pe}` (Includes prefix).
            *   *Incorrect Example*: `${gro} / ${pe}` (Shell syntax).
        *   **Determine Dataset Folder**: `{ID}_{REGION}_delay{DELAY}` (e.g., `analyst10_GLB_delay1`).
        *   **Run Script**:
            *   Navigate to the folder containing `implement_idea.py` (as identified in step 2).
            *   Command:
                ```bash
                cd <PATH_TO_SCRIPTS_FOLDER> && python implement_idea.py --template "<TEMPLATE_STRING>" --dataset "<DATASET_FOLDER_NAME>"
                ```
            *   *Note*: The script ONLY accepts `--template` and `--dataset`. Do not pass any other arguments like `--filters` or `--groupby`.
            *   **Strict Rule**: Do NOT use `python -c` or create temporary scripts to verify or process results. Trust the output of `implement_idea.py`.
        *   Verify the output (number of expressions generated).
        *   Mark the Todo item as completed.

5.  **Finalize Output**
    *   After all Todo items are completed, merge all generated expressions into a single file.
    *   **Run Merge Script**:
        *   Navigate to the folder containing scripts.
        *   Command:
            ```bash
            cd <PATH_TO_SCRIPTS_FOLDER> && python merge_expression_list.py --dataset "<DATASET_FOLDER_NAME>"
            ```
    *   This will create `final_expressions.json` in the dataset directory.
    *   Report the total number of unique expressions and the path to the final file to the user.

## Script Dependencies
This skill relies on the following scripts in its `scripts/` directory:
- `fetch_dataset.py`: Downloads data from Brain API.
- `implement_idea.py`: Generates alpha expressions from templates.
- `ace_lib.py` & `helpful_functions.py`: Support libraries.
