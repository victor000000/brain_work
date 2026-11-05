"""Pure static checks; no DB, SDK import or submitted-source execution."""

from pathlib import Path

import pytest

from runner.python_probe_source import validate_python_source

SOURCE = """from brain.alphas import alpha
import numpy as np
@alpha(data=["returns"], store=[])
def signal(data, store):
    return np.asarray(data.returns[-1], dtype=np.float32)
"""


def test_scoped_literal_source():
    assert validate_python_source(SOURCE, {"returns"}) == ("returns",)


@pytest.mark.parametrize("filename", ["pca_residual_reversal_candidate.py", "pca_no_component_control.py"])
def test_actual_pca_drafts(filename):
    source = (Path(__file__).parents[1] / "docs/research" / filename).read_text()
    assert validate_python_source(source, {"returns"}) == ("returns",)


@pytest.mark.parametrize(
    "source",
    [
        SOURCE.replace('data=["returns"]', 'data=["sales"]'),
        SOURCE.replace('data=["returns"]', 'data=["returns", "close"]'),
        SOURCE.replace('data=["returns"]', 'data=["returns", "returns"]'),
        SOURCE.replace("data.returns", "data.sales"),
        SOURCE.replace("data.returns", 'getattr(data, "returns")'),
        SOURCE.replace("return np.asarray", "alias = data\n    return np.asarray"),
        SOURCE.replace("store=[]", 'store=["state"]'),
        SOURCE.replace('data=["returns"]', 'data=list(["returns"])'),
        SOURCE.replace("import numpy as np", "import os"),
        SOURCE + '\nraise RuntimeError("must not execute")\n',
        SOURCE.replace("def signal(data, store):", 'def signal(data, store=print("bad")):'),
        SOURCE.replace("def signal(data, store):", "def signal(data, store):\n    import os"),
        SOURCE.replace("return np.asarray", "data.returns = 0\n    return np.asarray"),
        SOURCE.replace("def signal(data, store):", "def signal(data, store)"),
        SOURCE * 2,
    ],
)
def test_unsupported_sources_rejected_without_execution(source):
    with pytest.raises(ValueError):
        validate_python_source(source, {"returns", "close"})


def test_group_only_and_oversized_source_rejected():
    with pytest.raises(ValueError):
        validate_python_source(SOURCE.replace("returns", "industry"), {"returns"})
    with pytest.raises(ValueError):
        validate_python_source(SOURCE + "#" * 60000, {"returns"})
