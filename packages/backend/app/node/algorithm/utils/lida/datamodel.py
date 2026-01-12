# from dataclasses import dataclass
import base64
from dataclasses import field
from typing import Any, Dict, List, Optional, Union

from llmx import TextGenerationConfig
from pydantic.dataclasses import dataclass


@dataclass
class VizGeneratorConfig:
    """Configuration for a visualization generation"""

    hypothesis: str
    data_summary: Optional[str] = ""
    data_filename: Optional[str] = "cars.csv"


@dataclass
class CompletionResult:
    text: str
    logprobs: Optional[List[float]]
    prompt: str
    suffix: str



@dataclass
class Goal:
    """A visualization goal"""
    question: str
    visualization: str
    rationale: str
    index: Optional[int] = 0

    def _repr_markdown_(self):
        return f"""
### Goal {self.index}
---
**Question:** {self.question}

**Visualization:** `{self.visualization}`

**Rationale:** {self.rationale}
"""


@dataclass
class Summary:
    """A summary of a dataset"""

    name: str
    file_name: str
    dataset_description: str
    field_names: List[Any]
    fields: Optional[List[Any]] = None

    def _repr_markdown_(self):
        field_lines = "\n".join([f"- **{name}:** {field}" for name,
                                field in zip(self.field_names, self.fields)])
        return f"""
## Dataset Summary

---

**Name:** {self.name}

**File Name:** {self.file_name}

**Dataset Description:**

{self.dataset_description}

**Fields:**

{field_lines}
"""


@dataclass
class ChartExecutorResponse:
    """Response from a visualization execution"""

    spec: Optional[Union[str, Dict]]  # interactive specification e.g. vegalite
    status: bool  # True if successful
    raster: Optional[str]  # base64 encoded image
    code: str  # code used to generate the visualization
    library: str  # library used to generate the visualization
    error: Optional[Dict] = None  # error message if status is False

    def _repr_mimebundle_(self, include=None, exclude=None):
        bundle = {"text/plain": self.code}
        if self.raster is not None:
            bundle["image/png"] = self.raster
        if self.spec is not None:
            bundle["application/vnd.vegalite.v5+json"] = self.spec

        return bundle

    def savefig(self, path):
        """Save the raster image to a specified path if it exists"""
        if self.raster:
            with open(path, 'wb') as f:
                f.write(base64.b64decode(self.raster))
        else:
            raise FileNotFoundError("No raster image to save")
