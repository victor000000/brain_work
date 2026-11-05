import json
import csv
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

DEFAULT_TEMPLATE_ENHANCE_DIR = BASE_DIR / "knowledge" / "template_final_enhance"
TEMPLATE_ENHANCE_DIR = Path(
	os.environ.get("TEMPLATE_ENHANCE_DIR", str(DEFAULT_TEMPLATE_ENHANCE_DIR))
).expanduser().resolve()

LOCAL_FEATURE_IMPLEMENTATION_DIR = (BASE_DIR / "brain-feature-implementation").resolve()
FALLBACK_FEATURE_IMPLEMENTATION_DIR = (BASE_DIR.parent / "brain-feature-implementation").resolve()
DEFAULT_FEATURE_IMPLEMENTATION_DIR = (
	LOCAL_FEATURE_IMPLEMENTATION_DIR
	if LOCAL_FEATURE_IMPLEMENTATION_DIR.exists()
	else FALLBACK_FEATURE_IMPLEMENTATION_DIR
)
FEATURE_IMPLEMENTATION_DIR = Path(
	os.environ.get("FEATURE_IMPLEMENTATION_DIR", str(DEFAULT_FEATURE_IMPLEMENTATION_DIR))
).expanduser().resolve()
DEFAULT_FEATURE_IMPLEMENTATION_DIR = FEATURE_IMPLEMENTATION_DIR
DEFAULT_FEATURE_IMPLEMENTATION_SCRIPTS = FEATURE_IMPLEMENTATION_DIR / "scripts"

DEFAULT_MOONSHOT_MODEL = os.environ.get("MOONSHOT_MODEL", "kimi-k2.6")

VECTOR_DATA_TYPE_HINT = (
	"since the data is vector type data, the data cannot be directly use. before you do any process, you should choose a vector operator to generate its statistical feature to use (if the current template did not do so or you think you can have a better choice of another vector operator). for example, if datafieldA and datafieldB are vector type data, you cannot use vec_avg(datafieldA) -  vec_avg(datafieldB). similarly, vector type operator can only be used on the vector type operator."
)

CROSS_PROMPT_STYLES = {
	"conservative",
	"balanced",
	"aggressive",
	"ultra-aggressive",
}


def build_cross_style_instruction(style: str) -> str:
	if style == "conservative":
		return (
			"Cross-enhance conservatively. Keep each base template skeleton mostly intact, "
			"and only transfer a few operators/structures from other input templates when "
			"economically consistent."
		)
	if style == "balanced":
		return (
			"Cross-enhance with balanced novelty and stability. Each output should blend useful "
			"operator ideas from at least two input templates while remaining implementable and interpretable."
		)
	if style == "aggressive":
		return (
			"Cross-enhance aggressively. Maximize creative recombination across inputs, including "
			"pipeline re-ordering, while keeping syntax valid and placeholders unchanged."
		)
	if style == "ultra-aggressive":
		return (
			"Cross-enhance with explicit operator pipeline transfer: preprocess -> transform/compare -> "
			"normalize/neutralize -> robustness. Explain the transfer logic in each idea."
		)
	return build_cross_style_instruction("balanced")


def find_latest_idea_json(feature_implementation_dir: Path) -> Path:
	data_root = feature_implementation_dir / "data"
	if not data_root.exists():
		raise FileNotFoundError(f"data folder not found: {data_root}")
	idea_files = list(data_root.glob("**/idea_*.json"))
	if not idea_files:
		raise FileNotFoundError(f"No idea_*.json found under: {data_root}")
	# Prefer newest by mtime
	return max(idea_files, key=lambda p: p.stat().st_mtime)


def parse_idea_json_list_env(raw: str) -> list[Path]:
	"""Parse IDEA_JSON_LIST from env.

	Accepted formats:
	- JSON array string: ["path1", "path2"]
	- Delimited string by ';' or ','
	"""
	raw = (raw or "").strip()
	if not raw:
		return []

	# Try JSON array first.
	try:
		parsed = json.loads(raw)
		if isinstance(parsed, list):
			paths = []
			for item in parsed:
				if isinstance(item, str) and item.strip():
					paths.append(Path(item).expanduser().resolve())
			return paths
	except Exception:
		pass

	# Fallback: delimiter split.
	sep = ";" if ";" in raw else ","
	parts = [p.strip() for p in raw.split(sep)]
	return [Path(p).expanduser().resolve() for p in parts if p]


def load_idea_payload(path: Path) -> tuple[str, str]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict):
		raise ValueError(f"idea json must be an object: {path}")
	if "template" not in payload:
		raise ValueError(f"idea json missing required field 'template': {path}")
	if "idea" not in payload:
		raise ValueError(f"idea json missing required field 'idea': {path}")

	template = str(payload.get("template") or "").strip()
	idea = str(payload.get("idea") or "").strip()
	if not template:
		raise ValueError(f"idea json field 'template' is empty: {path}")
	return template, idea


def read_text(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def call_moonshot(
	api_key: str,
	model: str,
	system_prompt: str,
	user_prompt: str,
	timeout_s: int = 180,
	retries: int = 2,
	backoff_s: float = 2.0,
) -> str:
	base_url = os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
	url = f"{base_url.rstrip('/')}/chat/completions"
	base_headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	base_payload = {
		"model": model,
		"messages": [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		"temperature": 1,
	}

	def _stream_sse_and_collect(resp: requests.Response) -> str:
		"""Read OpenAI-compatible SSE stream and print deltas live.

		Still returns the full accumulated assistant content so existing callers
		(which expect a string) keep working.
		"""

		content_parts: list[str] = []
		thinking = False

		for raw_line in resp.iter_lines(decode_unicode=True):
			if not raw_line:
				continue
			line = raw_line.strip()
			if not line.startswith("data:"):
				continue
			data_str = line[5:].strip()
			if data_str == "[DONE]":
				break

			try:
				event = json.loads(data_str)
			except Exception:
				continue

			choices = event.get("choices") or []
			if not choices:
				continue
			choice0 = choices[0] if isinstance(choices[0], dict) else None
			if not choice0:
				continue

			delta = choice0.get("delta") or {}
			if not isinstance(delta, dict):
				delta = {}

			# Moonshot/Kimi exposes reasoning tokens as `reasoning_content`.
			reasoning = delta.get("reasoning_content")
			if reasoning:
				if not thinking:
					thinking = True
					print("=============开始思考=============", flush=True)
				print(str(reasoning), end="", flush=True)

			piece = delta.get("content")
			if piece:
				if thinking:
					thinking = False
					print("\n=============思考结束=============", flush=True)
				content_parts.append(str(piece))
				print(str(piece), end="", flush=True)

			finish_reason = choice0.get("finish_reason")
			if finish_reason:
				break

		if thinking:
			print("\n=============思考结束=============", flush=True)

		return "".join(content_parts)

	def _request_once(*, stream_mode: bool, force_identity: bool) -> str:
		headers = dict(base_headers)
		if force_identity:
			headers["Accept-Encoding"] = "identity"

		payload = dict(base_payload)
		payload["stream"] = stream_mode

		resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s, stream=stream_mode)
		resp.encoding = "utf-8"
		if resp.status_code >= 300:
			raise RuntimeError(f"Moonshot API error {resp.status_code}: {resp.text}")

		if stream_mode:
			ctype = (resp.headers.get("Content-Type") or "").lower()
			if "text/event-stream" in ctype or payload.get("stream"):
				return _stream_sse_and_collect(resp)

		data = resp.json()
		return data["choices"][0]["message"]["content"]

	last_exc: Exception | None = None
	for attempt in range(retries + 1):
		try:
			return _request_once(stream_mode=True, force_identity=False)
		except requests.exceptions.ContentDecodingError as exc:
			last_exc = exc
			try:
				print("[warn] streaming decode failed; retrying with identity encoding...", flush=True)
				return _request_once(stream_mode=True, force_identity=True)
			except requests.exceptions.RequestException as retry_exc:
				last_exc = retry_exc
			except Exception as retry_exc:
				last_exc = retry_exc
			if attempt >= retries:
				break
			time.sleep(backoff_s * (2**attempt))
		except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
			last_exc = exc
			if attempt >= retries:
				raise
			time.sleep(backoff_s * (2**attempt))
		except requests.exceptions.RequestException as exc:
			last_exc = exc
			if attempt >= retries:
				raise
			time.sleep(backoff_s * (2**attempt))
		except Exception as exc:
			last_exc = exc
			if attempt >= retries:
				raise
			time.sleep(backoff_s * (2**attempt))

	# Final fallback: keep one non-stream request to avoid total failure in rare
	# environments where streaming transport repeatedly breaks.
	try:
		print("[warn] streaming retries exhausted; falling back to non-stream once...", flush=True)
		return _request_once(stream_mode=False, force_identity=True)
	except Exception as exc:
		last_exc = exc

	raise last_exc or RuntimeError("Moonshot request failed")


def _salvage_json_array(text: str):
	"""Try parse JSON, or salvage the first JSON array in a text blob."""

	try:
		return json.loads(text)
	except Exception:
		pass

	decoder = json.JSONDecoder()
	for marker in ("[", "{"):
		start = text.find(marker)
		while start != -1:
			try:
				parsed, _ = decoder.raw_decode(text[start:])
				return parsed
			except Exception:
				start = text.find(marker, start + 1)

	# Fallback regex extraction for array/object blocks.
	for pattern in (r"\[.*\]", r"\{.*\}"):
		m = re.search(pattern, text, flags=re.DOTALL)
		if not m:
			continue
		try:
			return json.loads(m.group(0))
		except Exception:
			continue

	return None


def _extract_items(parsed) -> list[dict]:
	"""Normalize common LLM JSON shapes to a list of dict items."""
	if isinstance(parsed, list):
		return [x for x in parsed if isinstance(x, dict)]
	if isinstance(parsed, dict):
		for key in ("items", "data", "result", "results", "templates", "output_format"):
			val = parsed.get(key)
			if isinstance(val, list):
				return [x for x in val if isinstance(x, dict)]
	return []


def run_implement_idea(
	feature_implementation_dir: Path,
	scripts_dir: Path,
	dataset_folder: str,
	template: str,
	idea: str,
) -> Path | None:
	"""Run implement_idea.py for one template.

	Returns the newly created idea_*.json path if detectable.
	"""

	impl = scripts_dir / "implement_idea.py"
	data_dir = feature_implementation_dir / "data" / dataset_folder

	before = set(data_dir.glob("*_idea_*.json")) if data_dir.exists() else set()

	args_list = [
		sys.executable,
		str(impl),
		"--template",
		template,
		"--dataset",
		dataset_folder,
	]
	args_with_idea = args_list + ["--idea", idea or ""]
	args_without_idea = list(args_list)

	result = subprocess.run(
		args_with_idea,
		cwd=scripts_dir,
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		stderr_txt = (result.stderr or "")
		stdout_txt = (result.stdout or "")
		if "unrecognized arguments: --idea" in stderr_txt or "unrecognized arguments: --idea" in stdout_txt:
			result = subprocess.run(
				args_without_idea,
				cwd=scripts_dir,
				capture_output=True,
				text=True,
			)
	if result.returncode != 0:
		raise RuntimeError(
			"Command failed: "
			+ " ".join(args_with_idea)
			+ f"\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
		)

	after = set(data_dir.glob("*_idea_*.json")) if data_dir.exists() else set()
	created = sorted(after - before)
	return created[-1] if created else None


def _extract_keys_from_template(template: str) -> list[str]:
	return re.findall(r"\{([A-Za-z0-9_]+)\}", template)


def _matches_metric(field_id: str, metric: str) -> bool:
	if len(metric) <= 3:
		return re.search(rf"(^|_){re.escape(metric)}(_|$)", field_id, flags=re.IGNORECASE) is not None
	return metric in field_id


def load_dataset_ids(dataset_csv: Path, max_rows: int = 200000) -> list[str]:
	ids: list[str] = []
	with dataset_csv.open("r", encoding="utf-8", newline="") as f:
		reader = csv.reader(f)
		header = next(reader, None)
		if not header:
			return ids
		try:
			id_idx = header.index("id")
		except ValueError:
			return ids
		for i, row in enumerate(reader):
			if i >= max_rows:
				break
			if id_idx < len(row):
				val = (row[id_idx] or "").strip()
				if val:
					ids.append(val)
	return ids


def parse_metadata_from_dataset_folder(dataset_folder: str) -> tuple[str, str, int]:
	"""Extract dataset_id, region, delay from folder name like:
	<dataset_id>_<region>_delay<delay>

	Returns (dataset_id, region, delay).
	"""
	name = (dataset_folder or "").strip()
	parts = name.split("_")
	if len(parts) < 3:
		raise ValueError(f"Invalid dataset folder name: {dataset_folder}")

	delay_part = parts[-1]
	m = re.fullmatch(r"delay(\d+)", delay_part)
	if not m:
		raise ValueError(f"Invalid dataset folder name (missing delay suffix): {dataset_folder}")
	delay = int(m.group(1))

	region = parts[-2]
	dataset_id = "_".join(parts[:-2])
	if not dataset_id:
		raise ValueError(f"Invalid dataset folder name (missing dataset id): {dataset_folder}")

	return dataset_id, region, delay


def _fetch_dataset_supports_data_type(fetch_script: Path) -> bool:
	"""Detect whether fetch_dataset.py supports --data-type argument."""
	try:
		result = subprocess.run(
			[sys.executable, str(fetch_script), "--help"],
			cwd=fetch_script.parent,
			capture_output=True,
			text=True,
			timeout=20,
		)
		help_text = f"{result.stdout or ''}\n{result.stderr or ''}"
		return "--data-type" in help_text or "--data_type" in help_text
	except Exception:
		try:
			content = fetch_script.read_text(encoding="utf-8", errors="ignore")
			return "--data-type" in content or "data_type" in content
		except Exception:
			return False


def _fetch_dataset_csv_direct(
	feature_implementation_dir: Path,
	scripts_dir: Path,
	dataset_folder: str,
	dataset_id: str,
	region: str,
	delay: int,
	universe: str,
	instrument_type: str,
	data_type: str | None = None,
) -> Path:
	"""Fetch dataset rows directly from BRAIN API and save CSV.

	This avoids compatibility issues from older fetch_dataset.py wrappers.
	"""
	if str(scripts_dir) not in sys.path:
		sys.path.insert(0, str(scripts_dir))

	try:
		import ace_lib  # type: ignore
	except Exception as exc:
		raise RuntimeError(f"Failed to import ace_lib from {scripts_dir}: {exc}")

	user = (os.environ.get("BRAIN_USERNAME") or os.environ.get("BRAIN_EMAIL") or "").strip()
	pwd = (os.environ.get("BRAIN_PASSWORD") or "").strip()
	if user and pwd:
		ace_lib.get_credentials = lambda: (user, pwd)

	session = ace_lib.start_session()
	base = (
		f"{ace_lib.brain_api_url}/data-fields"
		f"?instrumentType={instrument_type}"
		f"&region={region}"
		f"&delay={int(delay)}"
		f"&universe={universe}"
		f"&dataset.id={dataset_id}"
	)

	rows: list[dict] = []
	offset = 0
	total = None
	while True:
		url = f"{base}&limit=50&offset={offset}"
		resp = session.get(url)
		if resp.status_code >= 300:
			raise RuntimeError(f"Direct datafield fetch failed {resp.status_code}: {resp.text[:500]}")
		payload = resp.json()
		batch = payload.get("results", []) if isinstance(payload, dict) else []
		if not isinstance(batch, list):
			batch = []
		rows.extend([r for r in batch if isinstance(r, dict)])
		if total is None:
			try:
				total = int(payload.get("count", 0))
			except Exception:
				total = 0
		offset += 50
		if offset >= (total or 0):
			break

	if not rows:
		raise RuntimeError(f"No datafields fetched for dataset={dataset_id}, region={region}, delay={delay}")

	dt = (data_type or "").strip().upper()
	if dt in ("MATRIX", "VECTOR"):
		filtered = []
		for row in rows:
			row_type = str(row.get("type") or "").strip().upper()
			if row_type == dt:
				filtered.append(row)
		if filtered:
			rows = filtered
		else:
			print(f"Warning: direct fetch got no rows for data_type={dt}; keeping unfiltered rows.")

	data_dir = feature_implementation_dir / "data" / dataset_folder
	data_dir.mkdir(parents=True, exist_ok=True)
	dataset_csv = data_dir / f"{dataset_folder}.csv"

	headers: list[str] = []
	for row in rows:
		for key in row.keys():
			if key not in headers:
				headers.append(key)

	with dataset_csv.open("w", encoding="utf-8", newline="") as f:
		writer = csv.DictWriter(f, fieldnames=headers)
		writer.writeheader()
		for row in rows:
			writer.writerow(row)

	print(f"Direct fetch saved {len(rows)} rows to: {dataset_csv}")
	return dataset_csv


def ensure_dataset_csv_data_type(
	feature_implementation_dir: Path,
	scripts_dir: Path,
	dataset_folder: str,
	data_type: str,
) -> None:
	"""Ensure the dataset CSV corresponds to the requested data_type.

	For enhance flow, the goal is to constrain implement_idea.py placeholder matching.
	When data_type is VECTOR, rebuild the dataset folder by refetching CSV as VECTOR.
	"""
	data_type = (data_type or "MATRIX").strip().upper()
	if data_type != "VECTOR":
		return

	dataset_id, region, delay = parse_metadata_from_dataset_folder(dataset_folder)
	fetch_script = scripts_dir / "fetch_dataset.py"
	if not fetch_script.exists():
		raise FileNotFoundError(f"fetch_dataset.py not found: {fetch_script}")

	# IMPORTANT: do NOT delete the whole dataset folder.
	# That folder may contain idea_*.json, enhanced_*.json and other artifacts.
	# We only need to ensure the CSV is VECTOR-only.
	data_dir = feature_implementation_dir / "data" / dataset_folder
	dataset_csv = data_dir / f"{dataset_folder}.csv"
	backup_csv: Path | None = None
	if dataset_csv.exists():
		backup_csv = dataset_csv.with_suffix(dataset_csv.suffix + f".bak_{int(time.time())}")
		try:
			print(f"DATA_TYPE=VECTOR => backing up existing CSV: {dataset_csv} -> {backup_csv}")
			shutil.copy2(dataset_csv, backup_csv)
		except Exception:
			backup_csv = None

	# Keep defaults consistent with fetch_dataset.py unless explicitly overridden.
	universe = (os.environ.get("UNIVERSE") or "TOP3000").strip()
	instrument_type = (os.environ.get("INSTRUMENT_TYPE") or "EQUITY").strip()

	try:
		_fetch_dataset_csv_direct(
			feature_implementation_dir=feature_implementation_dir,
			scripts_dir=scripts_dir,
			dataset_folder=dataset_folder,
			dataset_id=dataset_id,
			region=region,
			delay=delay,
			universe=universe,
			instrument_type=instrument_type,
			data_type="VECTOR",
		)
		return
	except Exception as exc:
		print(f"Warning: direct VECTOR rebuild failed, falling back to fetch_dataset.py. Error: {exc}")

	cmd = [
		sys.executable,
		str(fetch_script),
		"--datasetid",
		dataset_id,
		"--region",
		region,
		"--delay",
		str(delay),
		"--universe",
		universe,
		"--instrument-type",
		instrument_type,
	]
	if _fetch_dataset_supports_data_type(fetch_script):
		cmd.extend(["--data-type", "VECTOR"])
	else:
		print("Warning: fetch_dataset.py does not support --data-type. VECTOR rebuild cannot be strictly enforced.")
	print(f"Rebuilding dataset CSV as VECTOR via: {' '.join(cmd)}")

	result = subprocess.run(
		cmd,
		cwd=scripts_dir,
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		# Roll back CSV if we backed it up.
		if backup_csv and backup_csv.exists():
			try:
				print("VECTOR rebuild failed; restoring previous CSV backup.")
				shutil.copy2(backup_csv, dataset_csv)
			except Exception:
				pass
		raise RuntimeError(
			"VECTOR dataset rebuild failed: "
			+ " ".join(cmd)
			+ f"\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
		)
	if result.stdout.strip():
		print(result.stdout)
	if result.stderr.strip():
		print(result.stderr, file=sys.stderr)
	if not dataset_csv.exists():
		raise FileNotFoundError(f"VECTOR dataset rebuild succeeded but CSV not found: {dataset_csv}")


def ensure_dataset_csv_exists(
	feature_implementation_dir: Path,
	scripts_dir: Path,
	dataset_folder: str,
	data_type: str,
) -> Path:
	"""Ensure dataset CSV exists for the dataset_folder.

	If missing, auto-fetch it via fetch_dataset.py using BRAIN credentials from env/config.
	Returns the expected dataset CSV path.
	"""
	data_type = (data_type or "MATRIX").strip().upper()
	if data_type not in ("MATRIX", "VECTOR"):
		data_type = "MATRIX"

	data_dir = feature_implementation_dir / "data" / dataset_folder
	dataset_csv = data_dir / f"{dataset_folder}.csv"
	if dataset_csv.exists():
		return dataset_csv

	# Attempt to fetch missing CSV.
	dataset_id, region, delay = parse_metadata_from_dataset_folder(dataset_folder)
	fetch_script = scripts_dir / "fetch_dataset.py"
	if not fetch_script.exists():
		raise FileNotFoundError(f"fetch_dataset.py not found: {fetch_script}")

	universe = (os.environ.get("UNIVERSE") or "TOP3000").strip()
	instrument_type = (os.environ.get("INSTRUMENT_TYPE") or "EQUITY").strip()

	try:
		return _fetch_dataset_csv_direct(
			feature_implementation_dir=feature_implementation_dir,
			scripts_dir=scripts_dir,
			dataset_folder=dataset_folder,
			dataset_id=dataset_id,
			region=region,
			delay=delay,
			universe=universe,
			instrument_type=instrument_type,
			data_type=data_type,
		)
	except Exception as exc:
		print(f"Warning: direct dataset fetch failed, falling back to fetch_dataset.py. Error: {exc}")

	cmd = [
		sys.executable,
		str(fetch_script),
		"--datasetid",
		dataset_id,
		"--region",
		region,
		"--delay",
		str(delay),
		"--universe",
		universe,
		"--instrument-type",
		instrument_type,
	]
	if _fetch_dataset_supports_data_type(fetch_script):
		cmd.extend(["--data-type", data_type])
	else:
		print("Warning: fetch_dataset.py does not support --data-type. Skipping data type constraint during auto-fetch.")
	print(f"Dataset CSV missing. Auto-fetching via: {' '.join(cmd)}")

	result = subprocess.run(
		cmd,
		cwd=scripts_dir,
		capture_output=True,
		text=True,
	)
	if result.stdout.strip():
		print(result.stdout)
	if result.stderr.strip():
		print(result.stderr, file=sys.stderr)
	if result.returncode != 0:
		raise RuntimeError(
			"Auto-fetch dataset CSV failed: "
			+ " ".join(cmd)
			+ f"\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
		)

	# fetch_dataset.py writes to <feature_implementation_dir>/data/<dataset_folder>/<dataset_folder>.csv
	if not dataset_csv.exists():
		raise FileNotFoundError(f"Auto-fetch reported success but CSV still not found: {dataset_csv}")
	return dataset_csv


def normalize_for_validator(expression: str) -> str:
	"""Normalize expressions to satisfy validator rules (e.g., winsorize std=).

	Currently converts winsorize(x, N) -> winsorize(x, std=N)
	when the second argument is positional and not named.
	"""

	def _rewrite_func(expr: str, func_name: str, param_name: str) -> str:
		out = []
		i = 0
		func_token = f"{func_name}("
		while i < len(expr):
			idx = expr.find(func_token, i)
			if idx == -1:
				out.append(expr[i:])
				break
			out.append(expr[i:idx])
			j = idx + len(func_token)
			depth = 1
			args_start = j
			while j < len(expr) and depth > 0:
				ch = expr[j]
				if ch == '(':
					depth += 1
				elif ch == ')':
					depth -= 1
				j += 1
			args_str = expr[args_start : j - 1]
			# split top-level args
			args = []
			buf = []
			depth2 = 0
			for ch in args_str:
				if ch == '(':
					depth2 += 1
				elif ch == ')':
					depth2 -= 1
				if ch == ',' and depth2 == 0:
					args.append("".join(buf).strip())
					buf = []
				else:
					buf.append(ch)
			if buf:
				args.append("".join(buf).strip())

			if len(args) >= 2 and '=' not in args[1]:
				args[1] = f"{param_name}={args[1]}"
			new_args = ", ".join(args)
			out.append(f"{func_name}({new_args})")
			i = j
		return "".join(out)

	normalized = expression
	normalized = _rewrite_func(normalized, "winsorize", "std")
	return normalized


def parse_metadata_from_filename(path: Path) -> tuple[str, str, int] | None:
	"""Extract dataset_id, region, delay from filename like:
	<dataset>_<region>_<delay>_idea_<timestamp>.json

	Returns (dataset_id, region, delay) or None.
	"""
	name = path.name
	parts = name.split("_")
	if len(parts) < 5:
		return None
	if parts[-2] != "idea":
		return None
	region = parts[-4]
	delay_str = parts[-3]
	if not delay_str.isdigit():
		return None
	dataset_id = "_".join(parts[:-4])
	if not dataset_id:
		return None
	return dataset_id, region, int(delay_str)


def main():
	"""Zero-arg entrypoint.

	Inputs:
	- Single-input mode: IDEA_JSON (env), fallback to newest idea_*.json
	- Multi-input mode: IDEA_JSON_LIST (env; JSON array or ';'/' ,' separated paths)
	- Idea JSON payload must contain: {"template": str, "idea": str}
	- DATA_TYPE controls dataset CSV preparation (MATRIX or VECTOR)
	- MOONSHOT_API_KEY is required for LLM enhancement

	Processing:
	- In single mode, enhance one template; in multi mode, cross-enhance multiple templates
	- Ensure dataset CSV is present and compatible with DATA_TYPE when implement stage is enabled
	- Call Moonshot to produce enhanced templates
	- Optionally invoke implement_idea.py to generate expressions
	- Merge, deduplicate, normalize, and validator-filter final expressions

	Outputs:
	- Write enhanced_templates_<ts>.json into the same folder as IDEA_JSON
	- Write enhanced_final_expressions_<ts>.json into the same folder as IDEA_JSON
	- May also create/update artifacts under brain-feature-implementation/data/**
	  through fetch_dataset.py and implement_idea.py

	Optional env overrides:
	- IDEA_JSON: absolute/relative path to a specific idea_*.json
	- IDEA_JSON_LIST: multiple idea json paths (for cross-enhance)
	- MOONSHOT_API_KEY / MOONSHOT_BASE_URL / MOONSHOT_MODEL
	- CROSS_PROMPT_STYLE: conservative | balanced | aggressive | ultra-aggressive
	"""

	idea_json_list_env = os.environ.get("IDEA_JSON_LIST", "").strip()
	idea_json_env = os.environ.get("IDEA_JSON", "").strip()

	idea_json_paths = parse_idea_json_list_env(idea_json_list_env)
	if not idea_json_paths:
		if idea_json_env:
			idea_json_paths = [Path(idea_json_env).expanduser().resolve()]
		else:
			idea_json_paths = [find_latest_idea_json(DEFAULT_FEATURE_IMPLEMENTATION_DIR).resolve()]

	for p in idea_json_paths:
		if not p.exists():
			raise FileNotFoundError(f"idea json not found: {p}")

	is_cross_mode = len(idea_json_paths) >= 2
	primary_idea_json_path = idea_json_paths[0]
	print(f"Using {len(idea_json_paths)} idea json(s). Primary: {primary_idea_json_path}")

	idea_inputs = []
	for p in idea_json_paths:
		template, idea = load_idea_payload(p)
		idea_inputs.append(
			{
				"path": p,
				"template": template,
				"idea": idea,
			}
		)

	if is_cross_mode:
		# Cross preflight checks: filename metadata parse + consistency
		parsed_metas: list[tuple[str, str, int]] = []
		for item in idea_inputs:
			parsed = parse_metadata_from_filename(item["path"])
			if not parsed:
				raise ValueError(
					f"Cross mode requires filename format <dataset>_<region>_<delay>_idea_<ts>.json: {item['path'].name}"
				)
			parsed_metas.append(parsed)

		meta_set = set(parsed_metas)
		if len(meta_set) != 1:
			raise ValueError(
				"Cross mode requires all input idea filenames to share the same dataset/region/delay metadata"
			)

	raw_template = idea_inputs[0]["template"]
	raw_idea = idea_inputs[0]["idea"]

	# Infer feature-implementation location from the idea json path when possible:
	# <...>/brain-feature-implementation/data/<dataset_folder>/idea_*.json
	feature_implementation_dir = DEFAULT_FEATURE_IMPLEMENTATION_DIR
	scripts_dir = DEFAULT_FEATURE_IMPLEMENTATION_SCRIPTS
	try:
		if primary_idea_json_path.parent.parent.name.lower() == "data":
			feature_implementation_dir = primary_idea_json_path.parent.parent.parent
			scripts_dir = feature_implementation_dir / "scripts"
	except Exception:
		pass

	if not scripts_dir.exists():
		raise FileNotFoundError(f"implement scripts folder not found: {scripts_dir}")

	if primary_idea_json_path.parent.parent.name.lower() == "data":
		dataset_folder = primary_idea_json_path.parent.name
	else:
		parsed = parse_metadata_from_filename(primary_idea_json_path)
		if not parsed:
			raise ValueError(
				"idea json filename must be like <dataset>_<region>_<delay>_idea_<ts>.json "
				"when not located under brain-feature-implementation/data/<dataset_folder>/"
			)
		dataset_id_from_name, region_from_name, delay_from_name = parsed
		dataset_folder = f"{dataset_id_from_name}_{region_from_name}_delay{delay_from_name}"

	data_type = (os.environ.get("DATA_TYPE") or "MATRIX").strip().upper()
	if data_type not in ("MATRIX", "VECTOR"):
		data_type = "MATRIX"

	dataset_ids: list[str] = []
	# Guarantee implement_idea sees only VECTOR ids by rebuilding the dataset CSV as VECTOR.
	ensure_dataset_csv_data_type(
		feature_implementation_dir=feature_implementation_dir,
		scripts_dir=scripts_dir,
		dataset_folder=dataset_folder,
		data_type=data_type,
	)

	# Ensure dataset CSV exists (auto-fetch if missing) so implement_idea can parse placeholders.
	dataset_csv = ensure_dataset_csv_exists(
		feature_implementation_dir=feature_implementation_dir,
		scripts_dir=scripts_dir,
		dataset_folder=dataset_folder,
		data_type=data_type,
	)
	print(f"Using dataset CSV: {dataset_csv}")
	try:
		with dataset_csv.open("r", encoding="utf-8", newline="") as f:
			reader = csv.reader(f)
			header = next(reader, None)
			row_count = 0
			for _ in reader:
				row_count += 1
				if row_count >= 5:
					break
		if not header:
			raise ValueError("Dataset CSV missing header row")
		if row_count == 0:
			raise ValueError("Dataset CSV has no data rows")
		print(f"Dataset CSV header columns: {len(header)}; sample rows: {row_count}")
	except Exception as e:
		raise RuntimeError(f"Failed to read dataset CSV: {e}")

	dataset_ids = load_dataset_ids(dataset_csv)
	if not dataset_ids:
		print("Warning: Could not load dataset ids from CSV 'id' column.")

	guide1_path = TEMPLATE_ENHANCE_DIR / "单因子思考逻辑链.md"
	guide2_path = TEMPLATE_ENHANCE_DIR / "op总结.md"
	if not guide1_path.exists():
		raise FileNotFoundError(f"Missing guidance file: {guide1_path}")
	if not guide2_path.exists():
		raise FileNotFoundError(f"Missing guidance file: {guide2_path}")

	guide1 = read_text(guide1_path)
	guide2 = read_text(guide2_path)

	system_prompt = "\n\n".join(
		[
			"An alpha template is a reusable recipe that captures an economic idea and leaves “slots” (data fields, operators, groups, decay, neutralization choices, etc.) to instantiate many candidate alphas. Typical structure: clean data (backfill, winsorize) → transform/compare across time or peers → rank/neutralize → (optionally) decay/turnover tune. Templates encourage systematic search, reuse, and diversification while keeping an explicit economic rationale.",
			"",
			"Some Example Templates and rationales to help you understand the format",
			"",
			"CAPM residual (market/sector-neutral return): ts_regression(returns, group_mean(returns, log(ts_mean(cap,21)), sector), 252, rettype=0) after backfill+winsorize. Rationale: strip market/sector beta to isolate idiosyncratic alpha; sector-weighted by smoothed log-cap to reduce large-cap dominance.",
			"CAPM beta (slope) template: same regression with rettype=2; pre-clean target/market (ts_backfill(...,63) + winsorize(std=4)). Rationale: rank stocks by relative risk within sector; long low-β, short high-β, or study β dispersion across groups.",
			"CAPM generalized to any feature: data = winsorize(ts_backfill({data},63),std=4); data_gpm = group_mean(data, log(ts_mean(cap,21)), sector); resid = ts_regression(data, data_gpm, 252, rettype=0). Rationale: pull out the component unexplained by group average of same feature; reduces common-mode exposure.",
			"Actual vs estimate spread (analyst): group_zscore( group_zscore({act}, industry) – group_zscore({est}, industry), industry ) or the abstracted group_compare(diff(group_compare(act,...), group_compare(est,...)), ...). Rationale: surprise/beat-miss signal within industry, normalized to peers to avoid level bias.",
			"Analyst term-structure (fp1 vs fy1/fp2/fy2): group_zscore( group_zscore({mean_eps_period1}, industry) – group_zscore({mean_eps_period2}, industry), industry ) with operator/group slots. Rationale: cross-period expectation steepness; rising near-term vs long-term forecasts can flag momentum/inflection.",
			"Option Greeks net spread: group_operator({put_greek} - {call_greek}, {grouping_data}) over industry/sector (Delta/Gamma/Vega/Theta). Rationale: options-implied sentiment/convexity skew vs peers; outlier net Greeks may precede spot moves; extend with multi-Greek composites or time-series deltas.",
			"",
			"based on the following guidance of how to make a data collation template into a signal, and guidance on how to utilize the best of operators.",
			"",
			"guidance of how to make a data collation template into a signal",
			"--------------",
			guide1,
			"--------------",
			"guidance on how to use the best of operators",
			"--------------",
			guide2,
			"--------------",
			"",
			VECTOR_DATA_TYPE_HINT if data_type == "VECTOR" else "",
			"",
			"Return ONLY valid JSON (no markdown / no code fences).",
		]
	)

	cross_prompt_style = (os.environ.get("CROSS_PROMPT_STYLE") or "balanced").strip().lower()
	if cross_prompt_style not in CROSS_PROMPT_STYLES:
		cross_prompt_style = "balanced"

	if is_cross_mode:
		user_prompt_obj = {
			"mode": "cross_enhance",
			"style": cross_prompt_style,
			"instruction": build_cross_style_instruction(cross_prompt_style),
			"objective": "Use all input templates and ideas to perform cross-enhancement with cross-applied operators and structures.",
			"constraints": [
				"Keep { } placeholders unchanged.",
				"Do not invent new placeholders.",
				"Each output should integrate transferable logic from multiple sources.",
				"Return at least 8 enhanced templates.",
			],
			"inputs": [
				{
					"source": str(item["path"].name),
					"template": item["template"],
					"idea": item["idea"],
				}
				for item in idea_inputs
			],
			"output_format": [
				{"enhanced_template": "", "idea": ""},
				{"enhanced_template": "", "idea": ""},
			],
			"idea_answer_in": "Chinese",
		}
	else:
		user_prompt_obj = {
			"instruction": "Improve the following raw template. Keep { } placeholders unchanged (they represent datafields). Return at least 5 diverse and complicate enhanced templates as possible.",
			"input": {
				"template": raw_template,
				"idea": raw_idea,
			},
			"output_format": [
				{"enhanced_template": "", "idea": ""},
				{"enhanced_template": "", "idea": ""},
			],
			"idea_answer_in": "Chinese",
		}

	api_key = os.environ.get("MOONSHOT_API_KEY")
	if not api_key:
		raise ValueError("Missing Moonshot API key. Set MOONSHOT_API_KEY")

	raw = call_moonshot(
		api_key=api_key,
		model=DEFAULT_MOONSHOT_MODEL,
		system_prompt=system_prompt,
		user_prompt=json.dumps(user_prompt_obj, ensure_ascii=False, indent=2),
		timeout_s=600,
		retries=2,
		backoff_s=2.0,
	)

	parsed = _salvage_json_array(raw)
	items = _extract_items(parsed)
	if not items:
		raise RuntimeError(f"LLM output did not contain a usable JSON array. Raw output:\n{raw}")

	enhanced = []
	for item in items:
		t = str(item.get("enhanced_template") or item.get("template") or "").strip()
		idea = str(item.get("idea") or "").strip()
		if not t:
			continue
		enhanced.append({"template": t, "idea": idea})
		# Do NOT truncate here; keep all returned templates.

	if not enhanced:
		raise RuntimeError(f"No enhanced templates parsed from LLM output. Raw output:\n{raw}")

	out_dir = primary_idea_json_path.parent
	ts = int(time.time())
	enhanced_path = out_dir / f"enhanced_templates_{ts}.json"
	enhanced_path.write_text(json.dumps(enhanced, ensure_ascii=False, indent=2), encoding="utf-8")
	print(f"Enhanced templates saved to: {enhanced_path}")

	# Implement each enhanced template and merge expressions for this run only.
	all_exprs = []
	created_files = []

	for idx, item in enumerate(enhanced, start=1):
		t = item.get("template")
		if not t:
			continue
		idea = item.get("idea") or ""
		if dataset_ids:
			metrics = _extract_keys_from_template(t)
			missing = [m for m in metrics if not any(_matches_metric(fid, m) for fid in dataset_ids)]
			if missing:
				print(f"Template {idx} missing metrics in CSV id list: {missing}")
		print(f"\n[{idx}/{len(enhanced)}] Implementing enhanced_template: {t}")
		try:
			created = run_implement_idea(
				feature_implementation_dir=feature_implementation_dir,
				scripts_dir=scripts_dir,
				dataset_folder=dataset_folder,
				template=t,
				idea=idea,
			)
		except Exception as e:
			print(f"Template {idx} implementation failed: {e}")
			continue
		if created:
			created_files.append(created)

	for jf in created_files:
		try:
			data = json.loads(jf.read_text(encoding="utf-8"))
			exprs = data.get("expression_list", [])
			if exprs:
				all_exprs.extend([str(x) for x in exprs])
		except Exception:
			pass

	unique = []
	seen = set()
	for ex in all_exprs:
		norm_ex = normalize_for_validator(ex)
		if norm_ex not in seen:
			unique.append(norm_ex)
			seen.add(norm_ex)

	# Validate expressions and keep only valid ones
	try:
		if str(scripts_dir) not in sys.path:
			sys.path.insert(0, str(scripts_dir))
		from validator import ExpressionValidator  # type: ignore
		validator = ExpressionValidator()
		validated = []
		for expr in unique:
			result = validator.check_expression(expr)
			if result.get("valid"):
				validated.append(expr)
			else:
				print(f"Invalid expression filtered: {expr}")
		unique = validated
		print(f"Validation kept {len(unique)} expressions")
	except BaseException as e:
		print(f"Warning: validator failed, keeping unvalidated expressions. Error: {e}")

	merged_path = out_dir / f"enhanced_final_expressions_{ts}.json"
	merged_path.write_text(json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")
	print(f"\nMerged {len(unique)} unique expressions to: {merged_path}")


if __name__ == "__main__":
	main()