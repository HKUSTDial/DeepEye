"""
Prompt 模块
"""

from .data_analyst import DATA_ANALYST_PROMPT, format_data_analyst_prompt
from .scene_designer import SCENE_DESIGNER_PROMPT, format_scene_designer_prompt
from .animation_coordinator import ANIMATION_COORDINATOR_PROMPT, format_animation_coordinator_prompt

__all__ = [
    'DATA_ANALYST_PROMPT',
    'SCENE_DESIGNER_PROMPT',
    'ANIMATION_COORDINATOR_PROMPT',
    'format_data_analyst_prompt',
    'format_scene_designer_prompt',
    'format_animation_coordinator_prompt',
]

