import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
from app.core.config import settings

@dataclass
class TextGenerationConfig:
    n: int = 1
    temperature: float = 0
    model: str | None = None
    use_cache: bool = False

class Goal:
    def __init__(self, question: str, visualization: str, rationale: str):
        self.question = question
        self.visualization = visualization
        self.rationale = rationale

class Chart:
    def __init__(self, code: str, raster: Optional[str] = None):
        self.code = code
        self.raster = raster

class Manager:
    def __init__(self, text_gen: str = "openai", llm_client: Any = None):
        self.llm_client = llm_client
        self.text_gen = text_gen

    @staticmethod
    def _resolve_model(textgen_config: Optional[TextGenerationConfig]) -> str:
        model = (
            (textgen_config.model if textgen_config else None)
            or settings.LLM_MODEL
            or os.getenv("DEEPEYE_LLM_MODEL")
            or os.getenv("LLM_MODEL")
            or ""
        ).strip()
        if not model:
            raise ValueError("LLM model is required for dashboard generation")
        return model

    def summarize(self, dataset_path: str, summary_method: str = "default") -> Dict[str, Any]:
        """Generate a more comprehensive summary of the dataset."""
        if os.path.exists(dataset_path):
            if os.path.getsize(dataset_path) == 0:
                print(f"Warning: Dataset file is empty: {dataset_path}")
                df = pd.DataFrame()
            else:
                try:
                    df = pd.read_csv(dataset_path)
                except pd.errors.EmptyDataError:
                    print(f"Warning: pandas EmptyDataError for file: {dataset_path}")
                    df = pd.DataFrame()
        else:
            # If path doesn't exist, try to treat it as CSV content
            import io
            try:
                if not dataset_path:
                    df = pd.DataFrame()
                else:
                    df = pd.read_csv(io.StringIO(dataset_path))
            except Exception as e:
                print(f"Error reading dataset from string: {e}")
                # Fallback to an empty dataframe or raise error
                df = pd.DataFrame()
                # raise FileNotFoundError(f"Dataset path not found and not valid CSV content: {dataset_path[:100]}...")

        summary = {
            "name": os.path.basename(dataset_path) if dataset_path and os.path.exists(dataset_path) else "dataset.csv",
            "file_name": os.path.basename(dataset_path) if dataset_path and os.path.exists(dataset_path) else "dataset.csv",
            "dataset_description": "",
            "fields": [],
            "field_names": df.columns.tolist() if not df.empty else [],
            "n_samples": len(df),
            "n_columns": len(df.columns)
        }
        
        for col in df.columns:
            # Basic type inference
            dtype = str(df[col].dtype)
            unique_values = df[col].dropna().unique()
            n_unique = len(unique_values)
            
            field_info = {
                "column": col,
                "properties": {
                    "dtype": dtype,
                    "samples": unique_values[:5].tolist(),
                    "num_unique_values": n_unique,
                    "semantic_type": "",
                    "description": ""
                }
            }
            
            # Additional stats for numerical columns
            if pd.api.types.is_numeric_dtype(df[col]):
                field_info["properties"].update({
                    "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                    "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                    "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None
                })
            
            summary["fields"].append(field_info)
            
        # For backward compatibility with some parts of LIDA logic that might expect "columns"
        summary["columns"] = summary["fields"]
        
        return summary

    def goals(self, summary: Dict[str, Any], n: int = 5, textgen_config: Optional[TextGenerationConfig] = None) -> List[Goal]:
        """Generate visualization goals."""
        from . import chart_prompts
        from ..llm_compat import Message
        
        prompt = chart_prompts.LIDA_LITE_GOAL_PROMPT.format(
            SUMMARY=json.dumps(summary, ensure_ascii=False, indent=2),
            QUESTION="Explore the dataset and find interesting insights.",
            N=n
        )
        
        messages = [Message(role="user", content=prompt)]
        response = self.llm_client.generate(
            messages=messages,
            model=self._resolve_model(textgen_config),
            temperature=textgen_config.temperature if textgen_config else 0.7
        )
        
        return self._parse_goals(response.content)

    def goals_with_focus_area(self, summary: Dict[str, Any], n: int = 5, textgen_config: Optional[TextGenerationConfig] = None, focus_area: str = "") -> List[Goal]:
        """Generate visualization goals with a focus area."""
        from . import chart_prompts
        from ..llm_compat import Message
        
        prompt = chart_prompts.LIDA_LITE_GOAL_PROMPT.format(
            SUMMARY=json.dumps(summary, ensure_ascii=False, indent=2),
            QUESTION=focus_area,
            N=n
        )
        
        messages = [Message(role="user", content=prompt)]
        response = self.llm_client.generate(
            messages=messages,
            model=self._resolve_model(textgen_config),
            temperature=textgen_config.temperature if textgen_config else 0.7
        )
        
        return self._parse_goals(response.content)

    def visualize_wo_excecute(self, summary: Dict[str, Any], goal: Any, textgen_config: Optional[TextGenerationConfig] = None, library: str = "echarts") -> List[Chart]:
        """Generate chart code without execution."""
        from . import chart_prompts
        from ..llm_compat import Message
        
        goal_str = goal.question if isinstance(goal, Goal) else str(goal)
        
        prompt = chart_prompts.LIDA_LITE_VISUALIZE_PROMPT.format(
            SUMMARY=json.dumps(summary, ensure_ascii=False, indent=2),
            GOAL=goal_str
        )
        
        messages = [Message(role="user", content=prompt)]
        response = self.llm_client.generate(
            messages=messages,
            model=self._resolve_model(textgen_config),
            temperature=textgen_config.temperature if textgen_config else 0
        )
        
        code = self._extract_code(response.content)
        return [Chart(code=code)]

    def _parse_goals(self, content: str) -> List[Goal]:
        """Parse goals from LLM response."""
        try:
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            goals_data = json.loads(content)
            return [Goal(**g) for g in goals_data]
        except Exception as e:
            print(f"Error parsing goals: {e}")
            return []

    def _extract_code(self, content: str) -> str:
        """Extract Python code from LLM response."""
        code_match = re.search(r"```python\s*(.*?)\s*```", content, re.DOTALL)
        if code_match:
            return code_match.group(1)
        return content

def llm(provider: str = "openai"):
    """Dummy llm function to mimic LIDA."""
    return provider

