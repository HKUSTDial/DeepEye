"""
Simplified Config Generator - Two-Phase Generation
1. Data Analyst: Extract insights
2. Scene Designer: Generate complete config (without timing)
"""

import functools
import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple

import pandas as pd

from app.core.config import settings

from .data_utils import accumulate_token_usage, dataframe_to_list, list_to_dataframe
from .prompts import (
    format_data_analyst_prompt,
    format_scene_designer_prompt,
    format_scene_designer_subquery_prompt,
    format_data_transform_planner_prompt,
    format_data_transform_planner_prompt_batch,
    format_data_transform_planner_direct_prompt,
    format_video_director_prompt,
    format_opening_closing_generator_prompt,
    format_visual_designer_prompt,
    format_visual_designer_batch_prompt,
    format_narrative_director_prompt,
    format_scene_planner_prompt,
    format_scene_animation_generator_prompt
)
from .response_parser import parse_llm_json_response
from .retry import calculate_retry_wait_time, should_retry_on_error

# Force all print statements to flush immediately for real-time logging
print = functools.partial(print, flush=True)


# MAX_TOKENS: from env/config LLM_MAX_TOKENS
MAX_TOKENS = settings.LLM_MAX_TOKENS

# ============================================================================
# Custom Exceptions for Fatal Errors
# ============================================================================

class FatalGenerationError(Exception):
    """Base class for fatal errors that should stop the generation process"""
    pass


class TokenLimitError(FatalGenerationError):
    """Raised when LLM output is truncated due to token limit"""
    pass


class ScenePlanningError(FatalGenerationError):
    """Raised when scene planning fails critically"""
    pass


class DataPreparationError(FatalGenerationError):
    """Raised when critical data preparation fails"""
    pass


class TransformationExecutionError(Exception):
    """Raised when transformation execution fails (可重试，非致命错误)
    
    这类错误通常是 LLM 规划不完整导致的，可以通过重试修复。
    例如：缺少 derived_fields 定义、字段名错误等。
    """
    pass


class LLMClient:
    """LLM API Client"""
    
    def __init__(self, api_base: str, api_key: str, model: str | None = None, debug_prompts: bool = False):
        resolved_model = (model or settings.LLM_MODEL or "").strip()
        if not resolved_model:
            raise ValueError("LLM_MODEL is required for video generation")
        self.api_base = api_base
        self.api_key = api_key
        self.model = resolved_model
        self.debug_prompts = debug_prompts
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        # 使用 Session 连接池，提高性能
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _chat_completions_url(self) -> str:
        """构建 chat/completions 的 URL，避免 api_base 已含 /v1 时出现 /v1/v1/"""
        base = (self.api_base or "").rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"
    
    def call(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = MAX_TOKENS,
        verbose: bool = True
    ) -> Tuple[str, Dict]:
        """Call LLM API
        
        Returns:
            Tuple[str, Dict]: (content, usage) where usage contains token information
        """
        # Output full prompt if debug_prompts is enabled
        if self.debug_prompts:
            print("\n" + "="*80)
            print("📝 FULL PROMPT:")
            print(f"Prompt length: {len(prompt)} characters (~{len(prompt) // 4} tokens estimated)")
            print("="*80)
            print(prompt)
            print("="*80)
            print()
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # 智能重试配置
        max_general_retries = 10  # 普通错误最多重试10次
        start_time = time.time()
        attempt = 0
        
        while True:
            attempt += 1
            elapsed_time = time.time() - start_time
            try:
                if verbose:
                    if attempt > 1:
                        print(f"   🔄 重试请求 (尝试 {attempt})...")
                    else:
                        print(f"   📡 Sending request to API...")
                request_start = time.time()
                
                response = self.session.post(
                    self._chat_completions_url(),
                    json=payload,
                    timeout=180  # 3分钟超时（通常足够）
                )
                
                if verbose:
                    request_elapsed = time.time() - request_start
                    print(f"   ⏱️  Request completed in {request_elapsed:.1f}s")
                
                # 检查 HTTP 状态码，提供更详细的错误信息
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_body = response.text[:500]  # 限制错误信息长度
                        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
                        if error_data:
                            error_detail = error_data.get('error', {})
                            if isinstance(error_detail, dict):
                                error_msg = error_detail.get('message', error_msg)
                            elif isinstance(error_detail, str):
                                error_msg = error_detail
                        else:
                            error_msg = f"{error_msg}: {error_body}"
                    except:
                        error_msg = f"{error_msg}: {response.text[:200]}"
                    
                    # 根据状态码提供具体的错误说明
                    if response.status_code == 403:
                        raise RuntimeError(
                            f"LLM API call failed: 403 Forbidden - {error_msg}\n"
                            f"可能的原因：\n"
                            f"  1. API 密钥无效或已过期\n"
                            f"  2. API 密钥没有权限访问模型 '{self.model}'\n"
                            f"  3. 模型 '{self.model}' 不存在或不被支持\n"
                            f"  4. API 配额已用完\n"
                            f"建议：检查 API 密钥和模型名称是否正确"
                        )
                    elif response.status_code == 401:
                        raise RuntimeError(
                            f"LLM API call failed: 401 Unauthorized - {error_msg}\n"
                            f"API 密钥无效或格式错误"
                        )
                    elif response.status_code == 429:
                        # 429 错误可以重试，抛出 HTTPError（带特殊标记）
                        http_error = requests.exceptions.HTTPError(f"429 Rate limit exceeded: {error_msg}")
                        http_error.response = response
                        raise http_error
                    elif response.status_code == 400:
                        # 检查是否是 context length exceeded 错误
                        error_lower = error_msg.lower()
                        if any(keyword in error_lower for keyword in ['context length', 'maximum context', 'exceeded', '128000']):
                            # Context length exceeded：直接失败，不重试（避免浪费 token）
                            raise RuntimeError(
                                f"LLM API call failed: HTTP 400 - Context length exceeded\n"
                                f"{error_msg}\n"
                                f"⚠️  提示：Prompt 太长，重试只会浪费 token。建议减少 prompt 长度或使用更短的上下文。"
                            )
                        else:
                            # 其他 400 错误
                            raise RuntimeError(f"LLM API call failed: HTTP {response.status_code} - {error_msg}")
                    else:
                        raise RuntimeError(f"LLM API call failed: HTTP {response.status_code} - {error_msg}")
                
                # 如果状态码是 200，解析响应
                data = response.json()

                # Validate response shape early to avoid silent empty content
                choices = data.get("choices", None)
                if not isinstance(choices, list) or len(choices) == 0:
                    body_preview = json.dumps(data, ensure_ascii=False)[:1200]
                    raise RuntimeError(
                        f"LLM API response missing/empty 'choices'. model={self.model}. "
                        f"response_json_preview={body_preview}"
                    )

                message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
                content = message.get("content", "")
                if content is None:
                    content = ""
                # Support both string and array content (e.g. [{"type":"text","text":"..."}] from some APIs)
                if isinstance(content, list):
                    text_parts = [
                        p.get("text", "") for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    ]
                    content = "".join(text_parts) if text_parts else ""
                if not isinstance(content, str):
                    content = str(content)

                # Check finish_reason for fatal errors
                finish_reason = choices[0].get("finish_reason", "")
                if finish_reason == "length":
                    body_preview = json.dumps(data, ensure_ascii=False)[:1200]
                    raise TokenLimitError(
                        f"LLM output was truncated due to token limit. model={self.model}. "
                        f"finish_reason=length. This indicates the prompt is too long or the response is too verbose. "
                        f"response_json_preview={body_preview}"
                    )

                if content.strip() == "":
                    body_preview = json.dumps(data, ensure_ascii=False)[:1200]
                    raise RuntimeError(
                        f"LLM API returned empty message content. model={self.model}. "
                        f"response_json_preview={body_preview}"
                    )
                # 提取 token 使用信息
                usage = data.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                })
                
                # Output full response if debug_prompts is enabled
                if self.debug_prompts:
                    print("\n" + "="*80)
                    print("📤 API RESPONSE:")
                    print("="*80)
                    print(content)
                    print("="*80)
                    print(f"Response length: {len(content)} characters (~{len(content) // 4} tokens estimated)")
                    print(f"Token usage: {usage.get('prompt_tokens', 0)} prompt + {usage.get('completion_tokens', 0)} completion = {usage.get('total_tokens', 0)} total\n")
                
                return content.strip(), usage
                
            except requests.exceptions.HTTPError as e:
                # HTTP 错误处理
                error_msg = str(e)
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                
                if status_code == 429:
                    # 429 Rate Limit：使用智能重试判断
                    should_retry, reason = should_retry_on_error(error_msg, attempt, elapsed_time, max_general_retries)
                    
                    if should_retry:
                        wait_time = calculate_retry_wait_time(error_msg, attempt)
                        if verbose:
                            print(f"   ⚠️  限流错误 (429)，{wait_time}秒后重试... (尝试 {attempt})")
                        time.sleep(wait_time)
                        continue
                    else:
                        if verbose:
                            print(f"   ❌ 停止重试: {reason}")
                        raise RuntimeError(f"LLM API rate limit exceeded: {reason}")
                else:
                    # 其他 HTTP 错误（401, 403等）：检查是否应该重试
                    should_retry, reason = should_retry_on_error(error_msg, attempt, elapsed_time, max_general_retries)
                    
                    if not should_retry:
                        # 永久性错误，不重试
                        raise
                    # 否则不会到这里（因为401/403等都是永久性错误）
                    raise
                    
            except (requests.exceptions.SSLError, 
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                # 网络错误：使用智能重试判断
                error_msg = str(e)
                should_retry, reason = should_retry_on_error(error_msg, attempt, elapsed_time, max_general_retries)
                
                if should_retry:
                    wait_time = calculate_retry_wait_time(error_msg, attempt)
                    if verbose:
                        error_type = "SSL/连接错误" if isinstance(e, (requests.exceptions.SSLError, requests.exceptions.ConnectionError)) else "超时错误"
                        print(f"   ⚠️  {error_type}，{wait_time}秒后重试... (尝试 {attempt})")
                    time.sleep(wait_time)
                    
                    # 重新创建 session 以重置连接（对于 SSL 错误特别重要）
                    if isinstance(e, requests.exceptions.SSLError):
                        self.session = requests.Session()
                        self.session.headers.update(self.headers)
                    continue
                else:
                    if verbose:
                        print(f"   ❌ 停止重试: {reason}")
                    if isinstance(e, requests.exceptions.Timeout):
                        raise RuntimeError(f"LLM API call timed out after 180 seconds: {reason}")
                    else:
                        raise RuntimeError(f"LLM API call failed: {reason}")
                        
            except Exception as e:
                # 其他错误（如 TokenLimitError）：检查是否应该重试
                error_msg = str(e)
                
                # TokenLimitError 和其他致命错误不重试
                if isinstance(e, (TokenLimitError, FatalGenerationError)):
                    raise
                
                should_retry, reason = should_retry_on_error(error_msg, attempt, elapsed_time, max_general_retries)
                
                if should_retry:
                    wait_time = calculate_retry_wait_time(error_msg, attempt)
                    if verbose:
                        print(f"   ⚠️  API 错误，{wait_time}秒后重试... (尝试 {attempt})")
                        print(f"   错误: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    if verbose:
                        print(f"   ❌ 停止重试: {reason}")
                    raise RuntimeError(f"LLM API call failed: {e}")
    
    def call_with_json_mode(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = MAX_TOKENS,
        verbose: bool = True
    ) -> Tuple[Dict, Dict]:
        """Call LLM and parse JSON response
        
        Returns:
            Tuple[Dict, Dict]: (parsed_json, usage) where usage contains token information
        """
        response, usage = self.call(prompt, temperature, max_tokens, verbose=verbose)
        return parse_llm_json_response(response, usage, model=self.model, verbose=verbose)


class SimpleConfigGenerator:
    """Simplified Config Generator"""
    
    def __init__(
        self, 
        api_base: str,
        api_key: str,
        model: str | None = None,
        debug_prompts: bool = False
    ):
        self.client = LLMClient(api_base, api_key, model, debug_prompts=debug_prompts)

    def generate(self, query: str, data: List[Dict], language: str = "English", verbose: bool = True, skip_animations: bool = False, skip_orchestration: bool = False, skip_decomposition: bool = False, progress_callback=None) -> Dict[str, Any]:
        """Generate video config (Storyboard-driven)
        
        Args:
            skip_orchestration: If True, skip narrative orchestration (for ablation study)
                               - Phase 1 generates scenes with independent narrations
                               - Phase 2 uses simple priority-based ordering
                               - No intelligent scene selection or unified narrative generation
            skip_decomposition: If True, skip scene decomposition (for ablation study: w/o Decomposition)
                               - Skip Phase 0 (Scene Planner)
                               - Data Transform Planner works directly from original query
                               - Visual Designer generates all scenes at once
        
        Raises:
            TokenLimitError: When LLM output is truncated due to token limit
            ScenePlanningError: When scene planning fails critically
            DataPreparationError: When data preparation failure rate is too high (>80%)
            FatalGenerationError: Base class for other critical errors
        """
        
        if verbose:
            print("\n" + "="*60)
            if skip_decomposition:
                print("🎬 Starting video config generation (w/o Decomposition Mode)")
            else:
                print("🎬 Starting video config generation (Storyboard Mode)")
            print("="*60)
            print("")
        
        # 初始化 token 使用统计
        total_token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        # 初始化各阶段 token 使用统计
        phase_token_usage = {
            "phase_0_scene_planning": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "phase_0_5_data_preparation": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "phase_1_visual_generation": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "phase_2_narrative_generation": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "phase_4_animation": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        
        # Metadata extraction
        metadata = self._get_data_metadata(data)
        
        # Check if we should skip decomposition
        if skip_decomposition:
            return self._generate_without_decomposition(
                query, data, metadata, language, verbose, skip_orchestration, 
                total_token_usage, phase_token_usage, progress_callback
            )
        
        # Phase 0: Scene Planning
        if verbose:
            print(f"🔍 Phase 0: Scene Planning...")
        if progress_callback:
            progress_callback('planning', 10)
            
        scene_plans = self._plan_scenes(query, metadata, language, verbose, phase_token_usage["phase_0_scene_planning"])
        # 累计到总统计
        accumulate_token_usage(phase_token_usage["phase_0_scene_planning"], total_token_usage)
        
        # Filter out stat_cards scenes - they will be generated in Phase 2
        # Only process chart scenes in Phase 0-1
        data_scenes = [s for s in scene_plans if s.get('type') == 'chart']
        
        if verbose:
            stat_cards_count = len([s for s in scene_plans if s.get('type') == 'stat_cards'])
            if stat_cards_count > 0:
                print(f"   ℹ️  Filtered out {stat_cards_count} stat_cards scene(s) - will be generated in Phase 2")
        
        # All scenes are chart scenes (no opening/closing/stat_cards at this stage)
        
        # Phase 0.5: Data Preparation (for data scenes)
        if verbose:
            print("\n🔧 Phase 0.5: Data Preparation for Scenes...")
        if progress_callback:
            progress_callback('processing', 20)
            
        # Batch processing optimization
        filtered_data_list = []
        
        if data_scenes:
            # Step 1: Batch plan all transformations in a single LLM call
            # This sends metadata ONCE for all scenes instead of repeating for each scene
            try:
                transformation_plans = self._plan_data_transformations_batch(
                    data_scenes,
                    metadata,
                    language,
                    verbose=verbose,
                    phase_token_usage=phase_token_usage["phase_0_5_data_preparation"]
                )
            except Exception as e:
                if verbose:
                    print(f"   ❌ Batch transformation planning failed: {e}")
                raise DataPreparationError(f"Failed to plan data transformations for scenes: {e}")
            
            # Step 2: Execute transformations in parallel (using pre-planned transformations)
            def process_data_wrapper(scene):
                try:
                    scene_id = scene.get('id', 'unknown')
                    # Get pre-planned transformation for this scene
                    transformation_plan = transformation_plans.get(scene_id)
                    if transformation_plan is None:
                        raise DataPreparationError(f"No transformation plan found for scene {scene_id}")
                    
                    # Execute transformation with pre-planned plan (no LLM call needed)
                    return self._filter_data_for_subquery(
                        scene, 
                        data, 
                        metadata, 
                        language, 
                        verbose=verbose,
                        phase_token_usage=None,  # Token already counted in batch planning
                        transformation_plan=transformation_plan  # Use pre-planned transformation
                    )
                except FatalGenerationError:
                    # Re-raise fatal errors to stop the entire process
                    raise
                except Exception as e:
                    if verbose:
                        print(f"   ❌ Data preparation failed for {scene.get('id', 'unknown')}: {str(e)}")
                    return []
            
            # Parallel execution of data transformations
            with ThreadPoolExecutor(max_workers=min(len(data_scenes) + 1, 5)) as executor:
                futures = {executor.submit(process_data_wrapper, scene): scene for scene in data_scenes}
                results_map = {}
                for future in as_completed(futures):
                    scene = futures[future]
                    try:
                        result = future.result()
                        results_map[scene['id']] = result
                        if verbose:
                            if result:
                                print(f"   ✅ Data prepared for {scene['id']}: {len(result)} records")
                            else:
                                print(f"   ⚠️  Data preparation for {scene['id']}: No data returned (empty result)")
                    except FatalGenerationError:
                        # Re-raise fatal errors to stop the entire process
                        raise
                    except Exception as e:
                        if verbose:
                            print(f"   ❌ Data preparation exception for {scene['id']}: {str(e)}")
                        results_map[scene['id']] = []
                
                filtered_data_list = [results_map.get(scene['id'], []) for scene in data_scenes]
        
        # 累计 Phase 0.5 的 token 到总统计
        accumulate_token_usage(phase_token_usage["phase_0_5_data_preparation"], total_token_usage)

        # Check data preparation failure rate - if too high, stop
        if data_scenes:
            empty_data_count = sum(1 for data in filtered_data_list if not data)
            total_scenes = len(data_scenes)
            failure_rate = empty_data_count / total_scenes if total_scenes > 0 else 0
            
            if verbose:
                print(f"\n📊 Data Preparation Summary:")
                print(f"   Total scenes: {total_scenes}")
                print(f"   Successful: {total_scenes - empty_data_count}")
                print(f"   Failed: {empty_data_count}")
                print(f"   Failure rate: {failure_rate*100:.1f}%")
            
            # Stop if failure rate is too high (>80% for critical, 100% for absolute)
            if empty_data_count == total_scenes:
                error_msg = (
                    f"❌ FATAL: All data preparation failed ({empty_data_count}/{total_scenes} scenes). "
                    f"Cannot proceed without any valid data. Please check:\n"
                    f"  1. CSV file format and content\n"
                    f"  2. Query requirements vs available fields\n"
                    f"  3. LLM API responses and token limits"
                )
                if verbose:
                    print(f"\n{error_msg}")
                raise DataPreparationError(error_msg)
            elif failure_rate > 0.8:
                error_msg = (
                    f"❌ FATAL: Data preparation failure rate too high ({empty_data_count}/{total_scenes} = {failure_rate*100:.1f}%). "
                    f"Cannot proceed with most scenes having no data."
                )
                if verbose:
                    print(f"\n{error_msg}")
                raise DataPreparationError(error_msg)

        # Phase 1: Visual Scene Generation (No Narration)
        if verbose:
            print("\n🎨 Phase 1: Generating Visual Configs (Charts Only)...")
            if not filtered_data_list or all(not data for data in filtered_data_list):
                print("   ⚠️  WARNING: No data available for any scene! Charts cannot be generated.")
        if progress_callback:
            progress_callback('designing', 40)
            
        generated_scenes_map = {}
        
        # 1. Generate Data Scenes (Parallel) - Visual Only
        def generate_visual_wrapper(args):
            i, scene_plan, visual_data = args
            try:
                if not visual_data:
                    if verbose:
                        print(f"   ⚠️  Skipping {scene_plan['id']}: No data available")
                    return (scene_plan['id'], None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
                
                # 创建一个临时的 token_usage 来累计这个任务的 token
                task_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                scene_config = self._design_visual_only(
                    scene_plan,
                    visual_data,
                    language,
                    verbose=False,
                    token_usage=task_token_usage,
                    include_narration=skip_orchestration  # Pass through for ablation study
                )
                # 累计到阶段统计
                accumulate_token_usage(task_token_usage, phase_token_usage["phase_1_visual_generation"])
                if scene_config:
                    scene_config['id'] = scene_plan.get('id')
                    # Store narrative goal and priority from scene plan
                    scene_config['narrative_goal'] = scene_plan.get('context', '')
                    scene_config['priority'] = scene_plan.get('priority', 0.5)
                    # Ensure type matches scene plan (if specified)
                    planned_type = scene_plan.get('type')
                    if planned_type and scene_config.get('type') != planned_type:
                        if verbose:
                            print(f"   ⚠️  Scene {scene_plan['id']}: Type mismatch (planned: {planned_type}, generated: {scene_config.get('type')})")
                    return (scene_plan['id'], scene_config, task_token_usage)
                if verbose:
                    print(f"   ⚠️  Failed to generate config for {scene_plan['id']}: _design_visual_only returned None")
                return (scene_plan['id'], None, task_token_usage)
            except Exception as e:
                if verbose:
                    print(f"   ❌ Exception generating visual for {scene_plan['id']}: {str(e)}")
                return (scene_plan['id'], None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

        if data_scenes:
            scene_args = [(i, scene, f_data) for i, (scene, f_data) in enumerate(zip(data_scenes, filtered_data_list))]
            with ThreadPoolExecutor(max_workers=min(len(data_scenes) + 1, 5)) as executor:
                futures = [executor.submit(generate_visual_wrapper, args) for args in scene_args]
                for future in as_completed(futures):
                    sid, config, usage = future.result()
                    # 累计 token 使用量（已经在 _design_visual_only 中累计到阶段统计了）
                    accumulate_token_usage(usage, total_token_usage)
                    if config:
                        generated_scenes_map[sid] = config
                        if verbose:
                            s_type = config.get('type', 'unknown').upper()
                            title = config.get('content', {}).get('title', 'Untitled')
                            insight = config.get('insight_summary', 'N/A')[:60]
                            print(f"   ✅ Generated [{s_type}] {title}")
                            print(f"      💡 Insight: {insight}...")

        # Phase 1b: Prepare Scenes for Narrative Director
        if verbose:
            print("\n📋 Phase 1b: Preparing Scenes for Narrative Director...")
        
        # IMPORTANT: Preserve scene_plans order (not generated_scenes_map order which is random)
        # This ensures ablation study uses original Scene Planner order, not random completion order
        scenes_for_narrative = []
        for scene_plan in data_scenes:
            sid = scene_plan['id']
            if sid in generated_scenes_map:
                scene = generated_scenes_map[sid]
                # 直接传递 scene，只过滤掉视觉相关的字段（style, layout）
                scene_copy = self._filter_visual_fields(scene)
                scenes_for_narrative.append(scene_copy)
        
        if verbose:
            if len(scenes_for_narrative) == 0:
                print(f"   ⚠️  WARNING: Prepared 0 scenes (with full data)! No chart scenes were generated.")
                print(f"      This means no visualizations can be created. The video will only have opening and closing scenes.")
            else:
                print(f"   ✅ Prepared {len(scenes_for_narrative)} scenes (preserving Scene Planner order)")

        # Phase 2: Unified Narrative Generation & Scene Ordering
        if skip_orchestration:
            # ===== Ablation Study Mode: Skip Orchestration =====
            if verbose:
                print("\n⏭️  Phase 2: Skipping Orchestration (Ablation Mode)...")
                print("   📊 Using simple priority-based ordering")
                print("   💬 Scenes already have independent narrations from Phase 1")
            if progress_callback:
                progress_callback('generating_narrative', 60)
            
            # Simple ordering and template-based opening/closing (no LLM call)
            narrative_result = self._simple_narrative_assembly(
                query=query,
                scenes_info=scenes_for_narrative,
                generated_scenes_map=generated_scenes_map,
                verbose=verbose
            )
            # Note: No token usage in ablation mode (no LLM call)
            
        else:
            # ===== Normal Mode: Intelligent Orchestration =====
            if verbose:
                print("\n🎬 Phase 2: Generating Unified Narration & Ordering Scenes...")
            if progress_callback:
                progress_callback('generating_narrative', 60)
            
            # Generate unified narration and scene order (no references needed)
            narrative_result = self._generate_unified_narrative(
                query=query,
                scenes_info=scenes_for_narrative,
                opening_ref=None,
                closing_ref=None,
                language=language,
                verbose=verbose,
                token_usage=phase_token_usage["phase_2_narrative_generation"]
            )
            # 累计到总统计
            accumulate_token_usage(phase_token_usage["phase_2_narrative_generation"], total_token_usage)
        
        # Apply narrations to scenes
        if narrative_result:
            scene_order = narrative_result.get('scene_order', [])
            scene_narrations = narrative_result.get('scene_narrations', {})
            opening = narrative_result.get('opening')
            closing = narrative_result.get('closing')
            stat_cards = narrative_result.get('stat_cards')  # Get stat_cards if generated
            
            # Update scenes with narration
            for sid, narrations in scene_narrations.items():
                if sid in generated_scenes_map:
                    generated_scenes_map[sid]['narration'] = narrations
            
            # Add opening/closing
            if opening:
                generated_scenes_map[opening['id']] = opening
                if verbose:
                    print(f"   ✅ Generated [OPENING] {opening.get('content', {}).get('title', 'Untitled')}")
            
            if closing:
                generated_scenes_map[closing['id']] = closing
                if verbose:
                    print(f"   ✅ Generated [CLOSING] {closing.get('content', {}).get('title', 'Thank You')}")
            
            # Add stat_cards if generated by Narrative Director
            if stat_cards:
                stat_cards_id = stat_cards.get('id', 'scene_stats')
                generated_scenes_map[stat_cards_id] = stat_cards
                if verbose:
                    cards_count = len(stat_cards.get('content', {}).get('cards', []))
                    print(f"   ✅ Generated [STAT_CARDS] with {cards_count} metrics")
        
        # Phase 3: Assembly (using narrative director's order)
        if verbose:
            print("\n🔗 Phase 3: Assembling Video...")
        
        # Use scene_order from narrative director
        final_scenes = []
        if narrative_result and 'scene_order' in narrative_result:
            # Add opening first
            if opening and opening['id'] in generated_scenes_map:
                final_scenes.append(generated_scenes_map[opening['id']])
            
            # Add scenes in narrative order
            for sid in scene_order:
                if sid in generated_scenes_map:
                    final_scenes.append(generated_scenes_map[sid])
                else:
                    if verbose:
                        print(f"   ⚠️  Scene in order but not found: {sid}")
            
            # Add closing last
            if closing and closing['id'] in generated_scenes_map:
                final_scenes.append(generated_scenes_map[closing['id']])
        else:
            # Fallback: use scene plan order (by priority)
            if verbose:
                print("   ⚠️  Using fallback scene plan order")
            # Sort by priority (descending)
            sorted_plans = sorted(scene_plans, key=lambda x: x.get('priority', 0.5), reverse=True)
            for plan in sorted_plans:
                sid = plan['id']
                if sid in generated_scenes_map:
                    final_scenes.append(generated_scenes_map[sid])
                else:
                    if verbose:
                        print(f"   ⚠️  Skipping missing/failed scene: {sid}")

        config = {
            "meta": {"title": query, "fps": 30, "width": 1280, "height": 720, "user_query": query},
            "scenes": final_scenes
        }
        
        config = self._clean_time_fields(config)
        config = self._filter_single_data_point_scenes(config, verbose)
        config = self._normalize_background_colors(config, verbose)
        
        if verbose:
            print(f"✅ Final video has {len(config['scenes'])} scenes")

        if not skip_animations:
             if verbose:
                print("\n🎭 Phase 4: Animation Choreography...")
             if progress_callback:
                progress_callback('animating', 80)
             config, animations_added = self._add_animations(config, verbose, phase_token_usage["phase_4_animation"])
             # 累计到总统计
             accumulate_token_usage(phase_token_usage["phase_4_animation"], total_token_usage)
             if verbose:
                if animations_added:
                    print(f"✅ Added animations")
                else:
                    print(f"⚠️  Config generated without animations (fallback)")

        # 添加 token 使用统计到配置中
        config["token_usage"] = total_token_usage
        config["phase_token_usage"] = phase_token_usage
        
        # 输出阶段统计
        if verbose:
            print("\n" + "="*60)
            print("💹 Token Usage by Phase:")
            print("="*60)
            for phase_name, phase_usage in phase_token_usage.items():
                phase_display = {
                    "phase_0_scene_planning": "Phase 0: Scene Planning",
                    "phase_0_5_data_preparation": "Phase 0.5: Data Preparation",
                    "phase_1_visual_generation": "Phase 1: Visual Generation",
                    "phase_2_narrative_generation": "Phase 2: Narrative Generation",
                    "phase_4_animation": "Phase 4: Animation"
                }.get(phase_name, phase_name)
                
                total_phase = phase_usage.get("total_tokens", 0)
                if total_phase > 0:
                    prompt_tokens = phase_usage.get("prompt_tokens", 0)
                    completion_tokens = phase_usage.get("completion_tokens", 0)
                    percentage = (total_phase / total_token_usage["total_tokens"] * 100) if total_token_usage["total_tokens"] > 0 else 0
                    print(f"   {phase_display}:")
                    print(f"      Prompt: {prompt_tokens:,} | Completion: {completion_tokens:,} | Total: {total_phase:,} ({percentage:.1f}%)")
            print("="*60)

        return config

    def generate_legacy(
        self, 
        query: str, 
        data: List[Dict], 
        language: str = "English", 
        verbose: bool = True, 
        skip_animations: bool = False,
        progress_callback = None
    ) -> Dict[str, Any]:
        """
        Generate video configuration
        
        Args:
            query: User query
            data: Raw data
            language: Output language (English, Chinese, etc.)
            verbose: Whether to print detailed info
            skip_animations: Whether to skip animation generation (default False)
            progress_callback: Optional callback function(status, progress) to update progress
        
        Returns:
            Complete video config (without timing fields, but with animations)
        """
        if verbose:
            print("\n" + "="*60)
            print("🎬 Starting video config generation")
            print("="*60)

        total_token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        
        # Phase 0: Query Decomposition
        if verbose:
            print("\n🔍 Phase 0: Query Decomposition...")
        if progress_callback:
            progress_callback('decomposing', 10)
        
        metadata = self._get_data_metadata(data)
        sub_queries = self._decompose_query(query, metadata, language, verbose)
        
        if verbose:
            print(f"✅ Decomposed into {len(sub_queries)} sub-queries")
        if progress_callback:
            progress_callback('decomposing', 15)
        
        # Phase 0.5: Data Filtering and Transformation (for each sub-query)
        if verbose:
            print("\n🔧 Phase 0.5: Data Filtering and Transformation...")
        if progress_callback:
            progress_callback('filtering', 20)
        
        filtered_data_list = []
        for i, sub_query in enumerate(sub_queries, 1):
            if verbose:
                print(f"   Processing data for sub-query {i}/{len(sub_queries)}...")
            filtered_data = self._filter_data_for_subquery(sub_query, data, metadata, language, verbose)
            filtered_data_list.append(filtered_data)
            if verbose:
                print(f"   ✅ Sub-query {i}: {len(filtered_data)} records (transformed)")
        
        if progress_callback:
            progress_callback('filtering', 30)
        
        # Phase 1 & 2: Process each sub-query independently (direct scene generation)
        # Use parallel processing for scene generation
        all_scenes = []
        
        def generate_scene_wrapper(args):
            """Wrapper function for parallel scene generation"""
            i, sub_query, filtered_data = args
            try:
                scene = self._design_scene_from_subquery(
                    sub_query,
                    filtered_data,
                    language,
                    verbose=False  # Reduce verbose output in parallel mode
                )
                
                if scene:
                    # Use temporary unique ID to avoid conflicts (will be renamed later)
                    original_id = scene.get('id', 'scene_chart_1')
                    scene['id'] = f"temp_subquery_{i}_{original_id}"
                    return (i, scene, None)
                else:
                    return (i, None, "Failed to generate scene")
            except Exception as e:
                return (i, None, str(e))
        
        # Prepare arguments for parallel processing
        scene_args = [
            (i + 1, sub_query, filtered_data)
            for i, (sub_query, filtered_data) in enumerate(zip(sub_queries, filtered_data_list))
        ]
        
        if verbose:
            print(f"\n📊 Processing {len(sub_queries)} sub-queries in parallel...")
        
        # Process scenes in parallel (using ThreadPoolExecutor for I/O-bound LLM calls)
        all_scenes = [None] * len(sub_queries)  # Pre-allocate list
        
        with ThreadPoolExecutor(max_workers=min(len(sub_queries), 5)) as executor:  # Limit to 5 concurrent requests
            # Submit all tasks
            future_to_index = {
                executor.submit(generate_scene_wrapper, args): args[0] - 1
                for args in scene_args
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    i, scene, error = future.result()
                    if scene:
                        all_scenes[idx] = [scene]
                        scene_type = scene.get('type', 'unknown')
                        if scene_type == 'chart':
                            chart_type = scene.get('content', {}).get('chart_type', 'unknown')
                            title = scene.get('content', {}).get('title', 'N/A')
                            if verbose:
                                print(f"   ✅ Sub-Query {i}: Generated {chart_type} - {title}")
                        elif scene_type == 'stat_cards':
                            if verbose:
                                print(f"   ✅ Sub-Query {i}: Generated stat_cards")
                    else:
                        all_scenes[idx] = []
                        if verbose:
                            print(f"   ⚠️  Sub-Query {i}: {error or 'Failed to generate scene'}")
                    
                    completed += 1
                    if progress_callback:
                        progress_callback('designing', 30 + completed * 20 // len(sub_queries))
                except Exception as e:
                    all_scenes[idx] = []
                    if verbose:
                        print(f"   ❌ Sub-Query {idx + 1}: Exception - {e}")
        
        # Filter out None values (shouldn't happen, but safety check)
        all_scenes = [scenes if scenes is not None else [] for scenes in all_scenes]
        
        if progress_callback:
            progress_callback('designing', 50)
        
        # Phase 2.5: Merge all scenes
        if verbose:
            print("\n🔗 Phase 2.5: Merging Scenes...")
        if progress_callback:
            progress_callback('merging', 52)
        
        config = self._merge_scenes(all_scenes, query, sub_queries, language, verbose)
        
        # Apply post-processing (same as before)
        config = self._clean_time_fields(config)
        config = self._filter_single_data_point_scenes(config, verbose)
        config = self._normalize_background_colors(config, verbose)
        
        if verbose:
            print(f"✅ Generated {len(config['scenes'])} scenes")
            print(f"   Title: {config['meta']['title']}")
            
            # Output detailed info for each scene
            print("\n   📋 Scene List:")
            for i, scene in enumerate(config['scenes'], 1):
                scene_type = scene.get('type', 'unknown')
                scene_id = scene.get('id', 'unknown')
                content = scene.get('content', {})
                narration_count = len(scene.get('narration', []))
                
                # Show different info based on scene type
                if scene_type == 'opening':
                    title = content.get('title', 'N/A')
                    subtitle = content.get('subtitle', '')
                    print(f"   {i}. 🎬 [OPENING] {scene_id}")
                    print(f"      Title: {title}")
                    if subtitle:
                        print(f"      Subtitle: {subtitle}")
                elif scene_type == 'chart':
                    chart_type = content.get('chart_type', 'unknown')
                    chart_title = content.get('title', 'N/A')
                    data_count = len(content.get('data', []))
                    print(f"   {i}. 📊 [CHART] {scene_id}")
                    print(f"      Chart Type: {chart_type} | Title: {chart_title} | Data Points: {data_count}")
                elif scene_type == 'closing':
                    message = content.get('message', content.get('title', 'N/A'))
                    print(f"   {i}. 🎉 [CLOSING] {scene_id}")
                    print(f"      Closing Message: {message}")
                else:
                    print(f"   {i}. 📌 [{scene_type.upper()}] {scene_id}")
                
                # Show narration preview
                if narration_count > 0:
                    first_narr = scene.get('narration', [{}])[0].get('text', '')
                    preview = first_narr[:50] + '...' if len(first_narr) > 50 else first_narr
                    print(f"      🎙️ Narration({narration_count}): \"{preview}\"")
        
        if progress_callback:
            progress_callback('designing', 55)
        
        # Phase 3: Animation Choreography (optional)
        if not skip_animations:
            if verbose:
                print("\n🎭 Phase 3: Animation Choreography...")
            if progress_callback:
                progress_callback('animating', 60)
            
            config, _ = self._add_animations(config, verbose, total_token_usage)
            
            if verbose:
                total_animations = sum(
                    len(scene.get("animations", [])) 
                    for scene in config["scenes"]
                )
                print(f"✅ Added {total_animations} animations")
            if progress_callback:
                progress_callback('animating', 70)
        else:
            if progress_callback:
                progress_callback('animating', 70)

        # 添加用户原始查询到配置中
        config["meta"]["user_query"] = query
        
        # 添加 token 使用统计到配置中
        config["token_usage"] = total_token_usage

        return config
    
    def _get_data_metadata(self, data: List[Dict]) -> Dict[str, Any]:
        """Extract dataset metadata (without full data)"""
        if not data:
            return {
                "total_records": 0,
                "fields": [],
                "sample": []
            }
        
        sample = data[0]
        fields = list(sample.keys())
        
        # Get data types
        field_types = {}
        for field in fields:
            sample_value = sample.get(field)
            if sample_value is not None:
                if isinstance(sample_value, (int, float)):
                    field_types[field] = "numeric"
                elif isinstance(sample_value, str):
                    field_types[field] = "string"
                else:
                    field_types[field] = "other"
            else:
                field_types[field] = "unknown"
        
        # Get sample values (first 2 records)
        sample_records = data[:2] if len(data) >= 2 else data
        
        return {
            "total_records": len(data),
            "fields": fields,
            "field_types": field_types,
            "sample": sample_records
        }
    
    def _plan_scenes(self, query: str, metadata: Dict[str, Any], language: str, verbose: bool, token_usage: Dict = None) -> List[Dict]:
        """Phase 0: Plan Scenes (what analyses are needed)"""
        prompt = format_scene_planner_prompt(query, metadata, language)
        
        try:
            if verbose:
                print(f"   📋 Planning analysis scenes...")
            response, usage = self.client.call_with_json_mode(prompt, temperature=0.7, verbose=verbose)
            # 累计 token 使用量
            accumulate_token_usage(usage, token_usage)
            scenes = response.get("scenes", [])
            
            if not scenes:
                # Fallback: create simple scene plan
                if verbose:
                    print("   ⚠️  No scenes generated, using default fallback")
                # Try to extract field names from metadata
                fields = metadata.get('fields', [])
                if len(fields) >= 2:
                    return [
                        {
                            "id": "analysis_default",
                            "type": "chart",
                            "query": f"Analyze relationship between {fields[0]} and {fields[1]}",
                            "analysis_type": "comparison",
                            "priority": 1.0,
                            "context": "Default analysis",
                            "required_fields": fields[:2]
                        }
                    ]
                else:
                    return [
                        {
                            "id": "analysis_default",
                            "type": "chart",
                            "query": query,
                            "analysis_type": "comparison",
                            "priority": 1.0,
                            "context": "Default analysis",
                            "required_fields": []
                        }
                    ]
            
            if verbose:
                print(f"   ✅ Planned {len(scenes)} analysis scenes")
                for i, scene in enumerate(scenes, 1):
                    s_type = scene.get('type', 'unknown').upper()
                    priority = scene.get('priority', 0.5)
                    context = scene.get('context', 'N/A')[:50]
                    print(f"      {i}. [{s_type}] Priority: {priority:.1f} - {context}")
            
            return scenes
        
        except Exception as e:
            # ALL errors should fail immediately - no fallback for ablation study
            if verbose:
                print(f"   ❌ FATAL: Scene planning failed")
                print(f"   Error type: {type(e).__name__}")
                print(f"   Error: {e}")
                print(f"   ⛔ Stopping generation process - cannot proceed with invalid scene plan")
            raise ScenePlanningError(f"Scene planning failed: {e}") from e

    def _decompose_query(self, query: str, metadata: Dict[str, Any], language: str, verbose: bool) -> List[Dict]:
        """Legacy method - kept for reference but unused in new flow"""
        return []
    
    def _filter_data_for_subquery(
        self,
        sub_query: Dict[str, Any],
        full_data: List[Dict],
        metadata: Dict[str, Any],
        language: str,
        verbose: bool,
        phase_token_usage: Dict = None,
        transformation_plan: Dict[str, Any] = None
    ) -> List[Dict]:
        """Phase 0.5: Filter and transform data for a specific sub-query
        
        Optimization: All filtering is now handled by the LLM-planned transformation.
        No pre-filtering is done - the LLM will determine all necessary filters
        (both scope and quality filters) in one go.
        
        Args:
            transformation_plan: Optional pre-planned transformation. If provided,
                                skips the planning step (used in batch mode).
        """
        if verbose:
            print(f"   🔍 Preparing data for sub-query: {sub_query.get('query', 'N/A')[:80]}...")
            print(f"      Starting with: {len(full_data)} records")
        
        # Step 1: Plan data transformation using LLM (if not already provided)
        if transformation_plan is None:
            # LLM will determine ALL filters (scope + quality) based on the query
            transformation_plan = self._plan_data_transformation(
                sub_query,
                metadata,
                language,
                verbose,
                phase_token_usage=phase_token_usage
            )
        else:
            if verbose:
                trans_type = transformation_plan.get('transformation_type', 'unknown')
                description = transformation_plan.get('description', 'N/A')
                print(f"      📋 Using pre-planned transformation: {trans_type} - {description}")
        
        # Step 2: Execute data transformation (includes all filtering)
        # The transformation execution will handle:
        # - Scope filtering (e.g., Province='Punjab', Crop='Wheat')
        # - Quality filtering (e.g., field='not null', value>0)
        # - Data cleaning (%, Yes/No conversion)
        # - Aggregation/grouping/sorting
        transformed_data = self._execute_data_transformation(
            full_data,  # Pass full data, let transformation handle filtering
            transformation_plan,
            verbose
        )
        
        if verbose:
            print(f"      ✅ Transformed to {len(transformed_data)} records (ready for visualization)")
        
        return transformed_data
    
    def _is_date_field(self, field: str, df: pd.DataFrame) -> bool:
        """
        检测字段是否为日期类型
        
        Args:
            field: 字段名
            df: DataFrame
        
        Returns:
            是否为日期字段
        """
        if field not in df.columns:
            return False
        
        # 方法1: 检查字段名是否包含日期相关关键词
        field_lower = field.lower()
        if any(keyword in field_lower for keyword in ['date', 'time', 'datetime', 'timestamp']):
            return True
        
        # 方法2: 检查数据类型
        if pd.api.types.is_datetime64_any_dtype(df[field]):
            return True
        
        # 方法3: 尝试解析样本数据判断是否为日期格式
        sample_values = df[field].dropna().head(10)
        if len(sample_values) > 0:
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
                r'\d{4}-\d{1,2}-\d{1,2}',   # YYYY-MM-DD
                r'\d{4}/\d{1,2}/\d{1,2}',  # YYYY/MM/DD
            ]
            import re
            sample_str = ' '.join(str(v) for v in sample_values.head(5))
            if any(re.search(pattern, sample_str) for pattern in date_patterns):
                return True
        
        return False
    
    def _parse_date_threshold(self, date_str: str) -> pd.Timestamp:
        """
        解析日期字符串为 Timestamp
        
        Args:
            date_str: 日期字符串（如 '01/01/2018'）
        
        Returns:
            Timestamp 对象
        """
        try:
            # 使用 pandas 的 to_datetime，支持多种日期格式
            # 尝试常见格式：MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD 等
            return pd.to_datetime(date_str, errors='raise', infer_datetime_format=True)
        except:
            # 如果自动推断失败，尝试手动解析常见格式
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    # 尝试 MM/DD/YYYY
                    try:
                        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                        return pd.Timestamp(year, month, day)
                    except:
                        # 尝试 DD/MM/YYYY
                        try:
                            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                            return pd.Timestamp(year, month, day)
                        except:
                            pass
            raise ValueError(f"无法解析日期: {date_str}")

    def _apply_filter_to_dataframe(
        self,
        df: pd.DataFrame,
        filter_criteria: Dict[str, Any],
        verbose: bool
    ) -> pd.DataFrame:
        """
        Apply filter criteria directly to a DataFrame (more efficient than converting to/from list).
        
        Args:
            df: DataFrame to filter
            filter_criteria: Dict of {field: condition} filters
            verbose: Whether to print filtering info
        
        Returns:
            Filtered DataFrame
        """
        if not filter_criteria or df.empty:
            return df
        
        # Save original df for date field detection (before filtering reduces data)
        df_original = df.copy()
        
        for field, condition in filter_criteria.items():
            if field not in df.columns:
                if verbose:
                    print(f"      ⚠️  Field '{field}' not in data, skipping filter")
                continue
            
            if isinstance(condition, str):
                # 检测字段是否为日期类型 (use original df to ensure enough samples)
                is_date = self._is_date_field(field, df_original)
                
                # Handle range conditions like ">=1900 AND <=1924" or ">=01/01/2018 AND <=12/31/2021"
                if " AND " in condition.upper() or " and " in condition:
                    # 使用原始条件字符串分割，保持日期字符串的原始格式
                    parts = condition.split(" AND ") if " AND " in condition else condition.split(" and ")
                    mask = pd.Series([True] * len(df), index=df.index)
                    for part in parts:
                        part = part.strip()
                        if part.startswith(">="):
                            threshold_str = part[2:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                            if is_date:
                                try:
                                    threshold = self._parse_date_threshold(threshold_str)
                                    # 转换字段为日期类型
                                    df_field_dt = pd.to_datetime(df[field], errors='coerce')
                                    mask = mask & (df_field_dt >= threshold)
                                except Exception as e:
                                    if verbose:
                                        print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                                    mask = mask & pd.Series([False] * len(df), index=df.index)
                            else:
                                try:
                                    threshold = float(threshold_str)
                                    mask = mask & (pd.to_numeric(df[field], errors='coerce') >= threshold)
                                except ValueError:
                                    if verbose:
                                        print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                        elif part.startswith("<="):
                            threshold_str = part[2:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                            if is_date:
                                try:
                                    threshold = self._parse_date_threshold(threshold_str)
                                    df_field_dt = pd.to_datetime(df[field], errors='coerce')
                                    mask = mask & (df_field_dt <= threshold)
                                except Exception as e:
                                    if verbose:
                                        print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                                    mask = mask & pd.Series([False] * len(df), index=df.index)
                            else:
                                try:
                                    threshold = float(threshold_str)
                                    mask = mask & (pd.to_numeric(df[field], errors='coerce') <= threshold)
                                except ValueError:
                                    if verbose:
                                        print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                        elif part.startswith(">"):
                            threshold_str = part[1:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                            if is_date:
                                try:
                                    threshold = self._parse_date_threshold(threshold_str)
                                    df_field_dt = pd.to_datetime(df[field], errors='coerce')
                                    mask = mask & (df_field_dt > threshold)
                                except Exception as e:
                                    if verbose:
                                        print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                                    mask = mask & pd.Series([False] * len(df), index=df.index)
                            else:
                                try:
                                    threshold = float(threshold_str)
                                    mask = mask & (pd.to_numeric(df[field], errors='coerce') > threshold)
                                except ValueError:
                                    if verbose:
                                        print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                        elif part.startswith("<"):
                            threshold_str = part[1:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                            if is_date:
                                try:
                                    threshold = self._parse_date_threshold(threshold_str)
                                    df_field_dt = pd.to_datetime(df[field], errors='coerce')
                                    mask = mask & (df_field_dt < threshold)
                                except Exception as e:
                                    if verbose:
                                        print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                                    mask = mask & pd.Series([False] * len(df), index=df.index)
                            else:
                                try:
                                    threshold = float(threshold_str)
                                    mask = mask & (pd.to_numeric(df[field], errors='coerce') < threshold)
                                except ValueError:
                                    if verbose:
                                        print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                    df = df[mask]
                # Handle single string conditions
                elif condition.startswith(">="):
                    threshold_str = condition[2:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                    if is_date:
                        try:
                            threshold = self._parse_date_threshold(threshold_str)
                            df_field_dt = pd.to_datetime(df[field], errors='coerce')
                            df = df[df_field_dt >= threshold]
                        except Exception as e:
                            if verbose:
                                print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                            df = df.iloc[0:0]  # 返回空 DataFrame
                    else:
                        try:
                            threshold = float(threshold_str)
                            df = df[pd.to_numeric(df[field], errors='coerce') >= threshold]
                        except ValueError:
                            if verbose:
                                print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                elif condition.startswith("<="):
                    threshold_str = condition[2:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                    if is_date:
                        try:
                            threshold = self._parse_date_threshold(threshold_str)
                            df_field_dt = pd.to_datetime(df[field], errors='coerce')
                            df = df[df_field_dt <= threshold]
                        except Exception as e:
                            if verbose:
                                print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                            df = df.iloc[0:0]  # 返回空 DataFrame
                    else:
                        try:
                            threshold = float(threshold_str)
                            df = df[pd.to_numeric(df[field], errors='coerce') <= threshold]
                        except ValueError:
                            if verbose:
                                print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                elif condition.startswith(">"):
                    threshold_str = condition[1:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                    if is_date:
                        try:
                            threshold = self._parse_date_threshold(threshold_str)
                            df_field_dt = pd.to_datetime(df[field], errors='coerce')
                            df = df[df_field_dt > threshold]
                        except Exception as e:
                            if verbose:
                                print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                            df = df.iloc[0:0]  # 返回空 DataFrame
                    else:
                        try:
                            threshold = float(threshold_str)
                            df = df[pd.to_numeric(df[field], errors='coerce') > threshold]
                        except ValueError:
                            if verbose:
                                print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                elif condition.startswith("<"):
                    threshold_str = condition[1:].strip().rstrip(',').strip()  # Clean trailing commas and spaces
                    if is_date:
                        try:
                            threshold = self._parse_date_threshold(threshold_str)
                            df_field_dt = pd.to_datetime(df[field], errors='coerce')
                            df = df[df_field_dt < threshold]
                        except Exception as e:
                            if verbose:
                                print(f"      ⚠️  日期解析失败: {threshold_str}, 错误: {e}")
                            df = df.iloc[0:0]  # 返回空 DataFrame
                    else:
                        try:
                            threshold = float(threshold_str)
                            df = df[pd.to_numeric(df[field], errors='coerce') < threshold]
                        except ValueError:
                            if verbose:
                                print(f"      ⚠️  数值解析失败: {threshold_str}, 跳过该条件")
                elif condition.lower().strip().rstrip(',').strip() in ["not null", "not_null"]:
                    df = df[df[field].notna()]
                elif condition.lower().strip().rstrip(',').strip() in ["is null", "is_null", "null"]:
                    df = df[df[field].isna()]
                else:
                    # Clean trailing commas and spaces from condition
                    condition_cleaned = condition.rstrip(',').strip() if isinstance(condition, str) else condition
                    
                    # Exact match - 智能类型转换
                    # 如果字段是数值型，尝试把条件转为数字（避免 '0' vs 0 的问题）
                    try:
                        if pd.api.types.is_numeric_dtype(df[field]):
                            # 尝试转换条件为数字
                            condition_converted = pd.to_numeric(condition_cleaned, errors='ignore')
                            df = df[df[field] == condition_converted]
                        else:
                            # 字符串字段，智能匹配
                            # 使用原始 df 进行日期字段识别，确保有足够样本
                            is_date = self._is_date_field(field, df_original)
                            if verbose:
                                # 显示字段前3个值样本，用于调试
                                sample_values = df[field].dropna().head(3).tolist() if len(df) > 0 else []
                                print(f"      🔍 过滤前 {len(df)} 条, 字段 '{field}' 识别为日期字段: {is_date}")
                                print(f"         条件值: '{condition_cleaned}' (repr: {repr(condition_cleaned)})")
                                if sample_values:
                                    print(f"         字段样本: {sample_values[:3]}")
                            
                            # 先尝试精确匹配
                            df_exact = df[df[field] == condition_cleaned]
                            
                            # 如果精确匹配成功（有数据），使用精确匹配结果
                            if len(df_exact) > 0:
                                df = df_exact
                            else:
                                # 精确匹配失败，尝试智能匹配
                                # 1. 对于日期字段，检测是否为部分日期格式
                                if is_date and isinstance(condition_cleaned, str):
                                    # 检测是否为部分日期格式（如 MM/YYYY 或 YYYY）
                                    if '/' in condition_cleaned:
                                        parts = condition_cleaned.split('/')
                                        # MM/YYYY 格式（2部分）
                                        if len(parts) == 2:
                                            # 使用部分日期匹配：'01/2012' 应该匹配 '01/XX/2012' 格式
                                            # 匹配以 MM/ 开头且包含 /YYYY 的日期
                                            mm, yyyy = parts[0], parts[1]
                                            # 使用正则表达式：MM/任意2位数字/YYYY
                                            import re
                                            pattern = f"{re.escape(mm)}/\\d{{2}}/{re.escape(yyyy)}"
                                            df = df[df[field].astype(str).str.match(pattern, na=False)]
                                            if verbose:
                                                if len(df) > 0:
                                                    print(f"      ℹ️  使用部分日期匹配: '{condition_cleaned}' (模式: {pattern}, 匹配到 {len(df)} 条)")
                                                else:
                                                    print(f"      ⚠️  部分日期匹配失败: '{condition_cleaned}' (字段 '{field}' 识别为日期字段，但未匹配到数据)")
                                        else:
                                            # 完整日期，使用精确匹配（已经失败，返回空）
                                            if verbose:
                                                print(f"      ⚠️  完整日期精确匹配失败: '{condition_cleaned}' (字段 '{field}' 识别为日期字段)")
                                    elif condition_cleaned.isdigit() and len(condition_cleaned) == 4:
                                        # 只有年份（YYYY）
                                        df = df[df[field].astype(str).str.contains(condition_cleaned, case=False, na=False, regex=False)]
                                        if verbose:
                                            if len(df) > 0:
                                                print(f"      ℹ️  使用年份匹配: '{condition_cleaned}' (匹配到 {len(df)} 条)")
                                            else:
                                                print(f"      ⚠️  年份匹配失败: '{condition_cleaned}' (字段 '{field}' 识别为日期字段，但未匹配到数据)")
                                
                                # 2. 对于非日期字符串字段，尝试部分匹配 + 大小写不敏感
                                # 特别是对于 "Metric", "Description", "Name", "Category", "Type", "Destination" 等字段
                                elif isinstance(condition_cleaned, str):
                                    field_lower = field.lower()
                                    # 判断是否为可能需要部分匹配的字段类型
                                    fuzzy_match_fields = ['metric', 'description', 'name', 'category', 'type', 
                                                         'destination', 'location', 'address', 'title', 'subject']
                                    if any(keyword in field_lower for keyword in fuzzy_match_fields):
                                        # 尝试部分匹配 + 大小写不敏感
                                        df_fuzzy = df[df[field].astype(str).str.contains(condition_cleaned, case=False, na=False, regex=False)]
                                        if len(df_fuzzy) > 0:
                                            df = df_fuzzy
                                            if verbose:
                                                print(f"      ℹ️  使用模糊匹配: '{field}' contains '{condition_cleaned}' (大小写不敏感，匹配到 {len(df)} 条)")
                                        # 如果模糊匹配也失败，保持精确匹配的空结果
                                
                                # 如果所有智能匹配都失败，df 已经是空的（精确匹配失败的结果）
                    except:
                        # 转换失败，直接匹配
                        df = df[df[field] == condition]
            elif isinstance(condition, list):
                # Handle list conditions
                df = df[df[field].isin(condition)]
            else:
                # Handle exact match
                df = df[df[field] == condition]
            
            # Log filtering result
            if verbose:
                print(f"      📊 过滤字段 '{field}' 后: {len(df)} 条记录")
        
        return df
    
    def _apply_programmatic_filter(
        self,
        data: List[Dict],
        required_fields: List[str],
        filter_criteria: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Apply programmatic filtering based on criteria using pandas (legacy method for List input)"""
        if not data:
            return []
        
        # Convert to DataFrame
        df = list_to_dataframe(data)
        if df.empty:
            return []
        
        # Apply filter using the efficient DataFrame method
        df = self._apply_filter_to_dataframe(df, filter_criteria, verbose)
        
        # Select only required fields
        if required_fields:
            # Also keep fields needed for filtering
            fields_to_keep = set(required_fields)
            if filter_criteria:
                fields_to_keep.update(filter_criteria.keys())
            available_fields = [f for f in fields_to_keep if f in df.columns]
            if available_fields:
                df = df[available_fields]
        
        # Convert back to List[Dict]
        return dataframe_to_list(df)
    
    def _plan_data_transformation(
        self,
        sub_query: Dict[str, Any],
        metadata: Dict[str, Any],
        language: str,
        verbose: bool,
        phase_token_usage: Dict = None
    ) -> Dict[str, Any]:
        """Plan data transformation using LLM (retry handled by LLMClient)"""
        prompt = format_data_transform_planner_prompt(
            sub_query.get('query', ''),
            sub_query.get('analysis_type', 'comparison'),
            sub_query.get('required_fields', []),
            metadata,
            language
        )
        
        if verbose:
            print(f"      🧠 Planning data transformation...")
        
        try:
            plan, usage = self.client.call_with_json_mode(prompt, temperature=0.3, verbose=verbose)
            
            # Validate that plan is a dict, not a list
            if not isinstance(plan, dict):
                error_msg = (
                    f"Transformation planning returned invalid type: {type(plan).__name__} (expected dict). "
                    f"This usually means the LLM returned a JSON array instead of an object. "
                    f"Plan content: {str(plan)[:200]}"
                )
                if verbose:
                    print(f"      ❌ {error_msg}")
                raise DataPreparationError(error_msg)
            
            # 成功：累计 token 使用量
            if phase_token_usage is not None:
                accumulate_token_usage(usage, phase_token_usage)
            
            if verbose:
                trans_type = plan.get('transformation_type', 'unknown')
                description = plan.get('description', 'N/A')
                print(f"      📋 Transformation: {trans_type} - {description}")
            
            return plan
            
        except Exception as e:
            if verbose:
                import traceback
                error_detail = traceback.format_exc()
                print(f"      ❌ Transformation planning failed: {e}")
                print(f"      详细堆栈:\n{error_detail}")
            raise DataPreparationError(f"Transformation planning failed: {e}")
    
    def _plan_data_transformations_batch(
        self,
        scenes: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        language: str,
        verbose: bool,
        phase_token_usage: Dict = None
    ) -> Dict[str, Dict[str, Any]]:
        """Plan data transformations for multiple scenes in a single LLM call
        
        Args:
            scenes: List of scene dicts containing query, analysis_type, required_fields, id
            metadata: Dataset metadata (shared by all scenes)
            language: Language for responses
            verbose: Whether to print verbose output
            phase_token_usage: Token usage tracking dict
            
        Returns:
            Dict mapping scene_id to transformation plan
        """
        if verbose:
            print(f"      🧠 Planning data transformations for {len(scenes)} scenes (batch mode)...")
        
        # Prepare scenes data for batch prompt
        scenes_for_prompt = []
        for scene in scenes:
            scenes_for_prompt.append({
                'scene_id': scene.get('id', 'unknown'),
                'sub_query': scene.get('query', ''),
                'analysis_type': scene.get('analysis_type', 'comparison'),
                'required_fields': scene.get('required_fields', [])
            })
        
        # Format batch prompt
        prompt = format_data_transform_planner_prompt_batch(
            scenes_for_prompt,
            metadata
        )
        
        if verbose:
            print(f"      📊 Batch prompt prepared (metadata sent once for all scenes)")
        
        try:
            # Call LLM with batch prompt (retry handled by LLMClient)
            plans_dict, usage = self.client.call_with_json_mode(prompt, temperature=0.3, verbose=verbose)
            
            # Validate response format
            if not isinstance(plans_dict, dict):
                error_msg = (
                    f"Batch transformation planning returned invalid type: {type(plans_dict).__name__} (expected dict). "
                    f"Expected format: {{scene_id: plan, ...}}. "
                    f"Response content: {str(plans_dict)[:200]}"
                )
                if verbose:
                    print(f"      ❌ {error_msg}")
                raise DataPreparationError(error_msg)
            
            # Validate all scenes have plans
            missing_scenes = []
            for scene in scenes:
                scene_id = scene.get('id', 'unknown')
                if scene_id not in plans_dict:
                    missing_scenes.append(scene_id)
            
            if missing_scenes:
                error_msg = (
                    f"Batch transformation planning missing plans for scenes: {missing_scenes}. "
                    f"Expected {len(scenes)} plans, got {len(plans_dict)}."
                )
                if verbose:
                    print(f"      ❌ {error_msg}")
                raise DataPreparationError(error_msg)
            
            # Validate each plan is a dict
            for scene_id, plan in plans_dict.items():
                if not isinstance(plan, dict):
                    error_msg = (
                        f"Transformation plan for scene '{scene_id}' has invalid type: {type(plan).__name__} (expected dict). "
                        f"Plan content: {str(plan)[:200]}"
                    )
                    if verbose:
                        print(f"      ❌ {error_msg}")
                    raise DataPreparationError(error_msg)
            
            # Success: accumulate token usage
            if phase_token_usage is not None:
                accumulate_token_usage(usage, phase_token_usage)
            
            if verbose:
                print(f"      ✅ Batch planning complete: {len(plans_dict)} transformation plans generated")
                print(f"      💰 Token savings: Metadata sent once instead of {len(scenes)} times")
            
            return plans_dict
            
        except Exception as e:
            if verbose:
                import traceback
                error_detail = traceback.format_exc()
                print(f"      ❌ Batch transformation planning failed: {e}")
                print(f"      详细堆栈:\n{error_detail}")
            raise DataPreparationError(f"Batch transformation planning failed: {e}")
    
    def _execute_data_transformation(
        self,
        data: List[Dict],
        transformation_plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute data transformation based on plan"""
        trans_type = transformation_plan.get('transformation_type', 'sample_representative')
        
        # Apply filter BEFORE transformation if specified in plan
        # This allows filtering by location (state, city, etc.) before aggregation
        # Note: filter_and_select type handles its own filtering, so we skip unified filtering for it
        filter_criteria = transformation_plan.get('filter', {})
        if filter_criteria and data and trans_type != 'filter_and_select':
            if verbose:
                print(f"      🔍 Applying filter: {filter_criteria}")
            # Apply filter using pandas (reuse _apply_programmatic_filter logic)
            data = self._apply_programmatic_filter(data, [], filter_criteria, verbose)
            if verbose:
                print(f"      ✅ Filtered to {len(data)} records")
        
        if trans_type == 'group_by_aggregate':
            return self._execute_group_by_aggregate(data, transformation_plan, verbose)
        elif trans_type == 'time_series_aggregate':
            return self._execute_time_series_aggregate(data, transformation_plan, verbose)
        elif trans_type == 'filter_and_select':
            return self._execute_filter_and_select(data, transformation_plan, verbose)
        elif trans_type == 'top_n':
            return self._execute_top_n(data, transformation_plan, verbose)
        elif trans_type == 'correlation_data':
            return self._execute_correlation_data(data, transformation_plan, verbose)
        elif trans_type == 'sample_representative':
            return self._execute_sample_representative(data, transformation_plan, verbose)
        else:
            error_msg = (
                f"Unknown transformation type: '{trans_type}'. "
                f"Valid types: group_by_aggregate, time_series_aggregate, filter_and_select, "
                f"top_n, correlation_data, sample_representative"
            )
            if verbose:
                print(f"      ❌ {error_msg}")
            raise DataPreparationError(error_msg)
    
    def _clean_field_for_aggregation(self, df: pd.DataFrame, field: str, verbose: bool = False) -> pd.DataFrame:
        """Clean a field to make it suitable for numeric aggregation.
        
        Handles common data quality issues:
        - Percentage strings (e.g., "40%" -> 40)
        - Yes/No boolean strings (e.g., "Yes" -> 1, "No" -> 0)
        - Numeric strings with units or formatting
        
        Args:
            df: DataFrame to modify (modified in place)
            field: Field name to clean
            verbose: Whether to print cleaning info
        
        Returns:
            Modified DataFrame (same object, for chaining)
        """
        if field not in df.columns:
            return df
        
        # Get a sample of non-null values to detect data type
        sample_values = df[field].dropna().head(10).astype(str)
        if sample_values.empty:
            return df
        
        # Check if values contain percentage signs
        if sample_values.str.contains('%', regex=False).any():
            if verbose:
                print(f"         🧹 Cleaning '{field}': removing % signs")
            # Remove % sign and convert to numeric
            df[field] = df[field].astype(str).str.replace('%', '', regex=False)
            df[field] = pd.to_numeric(df[field], errors='coerce')
            return df
        
        # Check if values are Yes/No
        unique_values = set(sample_values.str.strip().str.lower().unique())
        if unique_values <= {'yes', 'no', 'nan', 'none', ''}:
            if verbose:
                print(f"         🧹 Cleaning '{field}': converting Yes/No to 1/0")
            # Convert Yes/No to 1/0
            df[field] = df[field].astype(str).str.strip().str.lower()
            df[field] = df[field].map({'yes': 1, 'no': 0})
            return df
        
        # Try to convert to numeric (handles most other cases)
        original_type = df[field].dtype
        converted = pd.to_numeric(df[field], errors='coerce')
        
        # Only apply conversion if it successfully converted some values
        non_null_count = converted.notna().sum()
        if non_null_count > 0 and original_type == 'object':
            if verbose:
                print(f"         🧹 Cleaning '{field}': converting to numeric ({non_null_count} values)")
            df[field] = converted
        
        return df
    
    def _execute_group_by_aggregate(
        self,
        data: List[Dict],
        plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute group by and aggregate transformation using pandas"""
        if not data:
            return []
        
        df = list_to_dataframe(data)
        if df.empty:
            return []
        
        # Calculate derived fields if specified (before any other operations)
        derived_fields = plan.get('derived_fields', {})
        if derived_fields:
            if verbose:
                print(f"      🧮 Calculating {len(derived_fields)} derived field(s)...")
            
            # Extract all field names used in expressions to ensure they have correct types
            import re
            all_fields_in_expressions = set()
            for expression in derived_fields.values():
                # Extract field names from expression (simple pattern: alphanumeric + underscore)
                # This will match both simple names and backtick-quoted names
                expression_str = str(expression)
                # Remove backticks and extract field names
                fields = re.findall(r'`([^`]+)`|(\b[A-Za-z_][A-Za-z0-9_]*\b)', expression_str)
                for backtick_field, simple_field in fields:
                    field_name = backtick_field if backtick_field else simple_field
                    if field_name and field_name in df.columns:
                        all_fields_in_expressions.add(field_name)
            
            # Ensure numeric fields are properly typed before derived field calculation
            for field in all_fields_in_expressions:
                if field in df.columns:
                    # Try to convert to numeric if it looks like it should be numeric
                    # This handles cases where filtering operations changed column types
                    if df[field].dtype == 'object':
                        # Try numeric conversion (coerce converts invalid values to NaN)
                        numeric_converted = pd.to_numeric(df[field], errors='coerce')
                        # Only keep conversion if it successfully converted most values
                        if numeric_converted.notna().sum() > 0:
                            df[field] = numeric_converted
                            if verbose:
                                print(f"         🔧 Converted '{field}' from object to {df[field].dtype}")
                        else:
                            if verbose:
                                print(f"         ⚠️  '{field}' appears to be text, keeping as object")
            
            for new_field, expression in derived_fields.items():
                try:
                    # Clean expression: remove trailing commas and spaces
                    # LLM sometimes generates "(Year // 10) * 10, " instead of "(Year // 10) * 10"
                    expression_cleaned = expression.strip().rstrip(',').strip() if isinstance(expression, str) else expression
                    
                    # Fix common LLM mistakes: replace AND/OR/NOT with &/|/~
                    # pandas.eval() doesn't support AND/OR/NOT keywords
                    import re
                    expression_cleaned = re.sub(r'\bAND\b', '&', expression_cleaned, flags=re.IGNORECASE)
                    expression_cleaned = re.sub(r'\bOR\b', '|', expression_cleaned, flags=re.IGNORECASE)
                    expression_cleaned = re.sub(r'\bNOT\b', '~', expression_cleaned, flags=re.IGNORECASE)
                    
                    df[new_field] = self._calculate_derived_field(df, expression_cleaned, verbose=verbose)
                    if verbose:
                        if expression != expression_cleaned:
                            print(f"         ✅ Created '{new_field}' from expression: {expression_cleaned} (cleaned from: {expression})")
                        else:
                            print(f"         ✅ Created '{new_field}' from expression: {expression_cleaned}")
                except Exception as e:
                    error_msg = f"Failed to calculate derived field '{new_field}': {str(e)}"
                    if verbose:
                        print(f"         ❌ {error_msg}")
                    raise TransformationExecutionError(error_msg)
        
        group_by_fields = plan.get('group_by_fields', [])
        aggregate_fields = plan.get('aggregate_fields', {})
        
        # Clean all aggregate fields before processing
        if aggregate_fields and verbose:
            print(f"      🧹 Cleaning aggregate fields...")
        for field in aggregate_fields.keys():
            if field in df.columns:
                self._clean_field_for_aggregation(df, field, verbose=verbose)
        
        # Ensure group_by_fields are properly typed to avoid comparison errors during groupby
        # Pandas groupby sorts by default, which fails if types are inconsistent
        for field in group_by_fields:
            if field in df.columns and df[field].dtype == 'object':
                # Try to convert to numeric if possible (coerce converts invalid values to NaN)
                numeric_converted = pd.to_numeric(df[field], errors='coerce')
                # Only keep conversion if it successfully converted most values
                if numeric_converted.notna().sum() > 0:
                    df[field] = numeric_converted
                    if verbose:
                        print(f"      🔧 Converted group_by field '{field}' to {df[field].dtype}")
        
        # If no group_by_fields but has aggregate_fields, calculate overall statistics
        if not group_by_fields and aggregate_fields:
            if verbose:
                print(f"      📊 Calculating overall statistics from {len(data)} records")
            
            # Calculate overall aggregates (no grouping) using pandas
            aggregated = {}
            for field, op in aggregate_fields.items():
                if field not in df.columns:
                    continue
                # Field is already cleaned above
                numeric_series = df[field]
                if op == 'avg':
                    aggregated[f'avg_{field}'] = round(float(numeric_series.mean()), 2) if not numeric_series.empty else 0
                elif op == 'sum':
                    aggregated[f'sum_{field}'] = round(float(numeric_series.sum()), 2) if not numeric_series.empty else 0
                elif op == 'count':
                    aggregated[f'count_{field}'] = int(numeric_series.notna().sum())
                elif op == 'min':
                    aggregated[f'min_{field}'] = round(float(numeric_series.min()), 2) if not numeric_series.empty else 0
                elif op == 'max':
                    aggregated[f'max_{field}'] = round(float(numeric_series.max()), 2) if not numeric_series.empty else 0
            
            aggregated['count'] = len(df)
            return [aggregated]  # Return single record with overall statistics
        
        if not group_by_fields:
            error_msg = "No group_by_fields specified and no aggregate_fields for overall statistics"
            if verbose:
                print(f"      ❌ {error_msg}")
            raise DataPreparationError(error_msg)
        
        # Check if all group_by_fields exist
        missing_fields = [f for f in group_by_fields if f not in df.columns]
        if missing_fields:
            error_msg = f"Missing required group_by_fields: {missing_fields}"
            if verbose:
                print(f"      ❌ {error_msg}")
                print(f"      💡 提示: 如果 {missing_fields} 是派生字段（如分组、分类字段），")
                print(f"          需要在 transformation_plan 的 'derived_fields' 中先定义它们")
                print(f"          例如: 'derived_fields': {{'{missing_fields[0]}': '(Year // 10) * 10'}}")
            # 这是 LLM 规划不完整的错误（忘记定义 derived_fields），可以通过重试修复
            raise TransformationExecutionError(error_msg)
        
        # Build aggregation dictionary and rename mapping
        # Note: We don't need to call pd.to_numeric here because fields are already cleaned above
        agg_dict = {}
        rename_mapping = {}  # Map from old column names to new names
        
        for field, op in aggregate_fields.items():
            if field not in df.columns:
                continue
            # Skip fields that are already used as grouping keys
            # This prevents "cannot insert X, already exists" errors
            if field in group_by_fields:
                if verbose:
                    print(f"      ⚠️  Skipping aggregation on '{field}' (already a grouping key)")
                continue
            if op == 'avg':
                agg_dict[field] = 'mean'
                rename_mapping[field] = f'avg_{field}'
            elif op == 'sum':
                agg_dict[field] = 'sum'
                rename_mapping[field] = f'sum_{field}'
            elif op == 'count':
                agg_dict[field] = 'count'
                rename_mapping[field] = f'count_{field}'
            elif op == 'min':
                agg_dict[field] = 'min'
                rename_mapping[field] = f'min_{field}'
            elif op == 'max':
                agg_dict[field] = 'max'
                rename_mapping[field] = f'max_{field}'
        
        # Add count column
        df['_count'] = 1
        agg_dict['_count'] = 'sum'
        rename_mapping['_count'] = 'count'
        
        # Perform groupby and aggregation
        grouped = df.groupby(group_by_fields).agg(agg_dict)
        
        # Reset index to make group_by_fields regular columns
        result_df = grouped.reset_index()
        
        # Rename aggregated columns to avoid conflicts with group_by_fields
        result_df = result_df.rename(columns=rename_mapping)
        
        # Round all numeric columns to 2 decimal places to avoid floating point precision issues
        for col in result_df.columns:
            if result_df[col].dtype in ['float64', 'float32']:
                result_df[col] = result_df[col].round(2)
        
        # Sort if specified
        if plan.get('sort_by'):
            sort_field = plan['sort_by']
            reverse = plan.get('sort_order') == 'desc'
            if sort_field in result_df.columns:
                result_df = result_df.sort_values(by=sort_field, ascending=not reverse)
        
        # Limit if specified
        limit = plan.get('limit')
        if limit:
            result_df = result_df.head(limit)
        
        # Convert back to List[Dict]
        return dataframe_to_list(result_df)
    
    def _execute_time_series_aggregate(
        self,
        data: List[Dict],
        plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute time series aggregation using pandas"""
        if not data:
            return []
        
        df = list_to_dataframe(data)
        if df.empty:
            return []
        
        time_field = plan.get('time_field', 'date')
        time_grouping = plan.get('time_grouping', 'day')
        aggregate_fields = plan.get('aggregate_fields', {})
        
        if time_field not in df.columns:
            error_msg = f"Time field '{time_field}' not found in data. Available fields: {list(df.columns)}"
            if verbose:
                print(f"      ❌ {error_msg}")
            # 这是 LLM 选择了不存在的时间字段，可以通过重试修复
            raise TransformationExecutionError(error_msg)
        
        # Clean all aggregate fields before processing
        if aggregate_fields and verbose:
            print(f"      🧹 Cleaning aggregate fields...")
        for field in aggregate_fields.keys():
            if field in df.columns:
                self._clean_field_for_aggregation(df, field, verbose=verbose)
        
        # Check if time_field is already datetime or can be converted
        # For numeric years (like 1900), keep as-is and group directly
        # For string dates, try to convert to datetime
        is_numeric_year = pd.api.types.is_numeric_dtype(df[time_field])
        if not is_numeric_year:
            # Try converting string dates to datetime
            try:
                original_series = df[time_field]
                parsed = pd.to_datetime(original_series, errors='coerce')
                # If conversion produced all NaT (e.g. "1月","2月" cannot be parsed), keep as-is
                if parsed.isna().all():
                    pass  # keep original_series, do not replace
                else:
                    df[time_field] = parsed
            except Exception:
                # If conversion fails, keep as-is
                pass
        
        # Build aggregation dictionary and rename mapping
        # Note: Fields are already cleaned above, no need to call pd.to_numeric here
        agg_dict = {}
        rename_mapping = {}  # Map from old column names to new names
        
        for field, op in aggregate_fields.items():
            if field not in df.columns:
                continue
            # Skip fields that are the time grouping field
            # This prevents "cannot insert X, already exists" errors
            if field == time_field:
                if verbose:
                    print(f"      ⚠️  Skipping aggregation on '{field}' (already the time grouping field)")
                continue
            if op == 'avg':
                agg_dict[field] = 'mean'
                rename_mapping[field] = f'avg_{field}'
            elif op == 'sum':
                agg_dict[field] = 'sum'
                rename_mapping[field] = f'sum_{field}'
            elif op == 'count':
                agg_dict[field] = 'count'
                rename_mapping[field] = f'count_{field}'
            elif op == 'min':
                agg_dict[field] = 'min'
                rename_mapping[field] = f'min_{field}'
            elif op == 'max':
                agg_dict[field] = 'max'
                rename_mapping[field] = f'max_{field}'
        
        # Add count column
        df['_count'] = 1
        agg_dict['_count'] = 'sum'
        rename_mapping['_count'] = 'count'
        
        # Group by time period
        # For numeric years (like 1900), group by the field directly
        # For datetime fields, use Grouper with appropriate frequency
        if pd.api.types.is_datetime64_any_dtype(df[time_field]):
            # Determine grouping frequency for datetime
            freq_map = {
                'year': 'YE',  # Use 'YE' instead of deprecated 'Y'
                'month': 'ME',
                'week': 'W',
                'day': 'D'
            }
            freq = freq_map.get(time_grouping, 'D')
            try:
                grouped = df.groupby(pd.Grouper(key=time_field, freq=freq)).agg(agg_dict)
            except:
                # Fallback: group by the field directly
                grouped = df.groupby(time_field).agg(agg_dict)
        else:
            # For numeric years or other non-datetime fields, group directly
            # This handles cases like year=1900, 1901, etc.
            grouped = df.groupby(time_field).agg(agg_dict)
        
        # Reset index to make time_field a regular column
        result_df = grouped.reset_index()
        
        # Rename aggregated columns to avoid conflicts with time_field
        result_df = result_df.rename(columns=rename_mapping)
        
        # Round all numeric columns to 2 decimal places to avoid floating point precision issues
        for col in result_df.columns:
            if result_df[col].dtype in ['float64', 'float32']:
                result_df[col] = result_df[col].round(2)
        
        # Convert time_field back to string if it was datetime
        if pd.api.types.is_datetime64_any_dtype(result_df[time_field]):
            result_df[time_field] = result_df[time_field].dt.strftime('%Y-%m-%d')
        else:
            result_df[time_field] = result_df[time_field].astype(str)
        
        # Sort by time_field
        result_df = result_df.sort_values(by=time_field)
        
        # Limit if specified
        limit = plan.get('limit')
        if limit:
            result_df = result_df.head(limit)
        
        # Convert back to List[Dict]
        return dataframe_to_list(result_df)
    
    def _execute_filter_and_select(
        self,
        data: List[Dict],
        plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute filter and select transformation using pandas"""
        if not data:
            return []
        
        df = list_to_dataframe(data)
        if df.empty:
            return []
        
        # Apply filter directly on DataFrame (avoid unnecessary conversions)
        filter_dict = plan.get('filter', {})
        if filter_dict:
            df = self._apply_filter_to_dataframe(df, filter_dict, verbose)
        
        # Select fields
        select_fields = plan.get('select_fields', [])
        if select_fields:
            available_fields = [f for f in select_fields if f in df.columns]
            if available_fields:
                df = df[available_fields]
        
        # Limit - with intelligent default
        limit = plan.get('limit')
        
        # Safety net: Auto-limit large datasets if no explicit limit was set
        if not limit and len(df) > 200:
            if verbose:
                print(f"      ⚠️  Auto-limiting filter_and_select: {len(df)} → 200 records (no limit specified)")
                print(f"      💡 Tip: Set 'limit' parameter in transformation plan to avoid auto-limiting")
            limit = 200
        
        if limit:
            df = df.head(limit)
        
        return dataframe_to_list(df)
    
    def _execute_top_n(
        self,
        data: List[Dict],
        plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute top N transformation using pandas for better performance"""
        if not data:
            return []
        
        sort_by = plan.get('sort_by')
        sort_order = plan.get('sort_order', 'desc')
        limit = plan.get('limit', 10)
        group_by_fields = plan.get('group_by_fields', [])
        
        # Convert to DataFrame
        df = list_to_dataframe(data)
        if df.empty:
            return []
        
        if group_by_fields:
            # Use pandas groupby + nlargest/nsmallest for efficient top-N selection
            # Remove groups with null keys
            df_filtered = df.dropna(subset=group_by_fields)
            
            if sort_by and sort_by in df_filtered.columns:
                if sort_order == 'desc':
                    result_df = df_filtered.groupby(group_by_fields, as_index=False).apply(
                        lambda x: x.nlargest(limit, sort_by)
                    ).reset_index(drop=True)
                else:
                    result_df = df_filtered.groupby(group_by_fields, as_index=False).apply(
                        lambda x: x.nsmallest(limit, sort_by)
                    ).reset_index(drop=True)
            else:
                # No sort_by specified, just take first N from each group
                result_df = df_filtered.groupby(group_by_fields, as_index=False).head(limit).reset_index(drop=True)
        else:
            # Simple top N - sort and take top records
            if sort_by and sort_by in df.columns:
                ascending = (sort_order == 'asc')
                result_df = df.sort_values(by=sort_by, ascending=ascending).head(limit)
            else:
                # No sort_by specified, just take first N records
                result_df = df.head(limit)
        
        return dataframe_to_list(result_df)
    
    def _execute_correlation_data(
        self,
        data: List[Dict],
        plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute correlation data preparation with support for derived fields"""
        x_field = plan.get('x_field')
        y_field = plan.get('y_field')
        sample_size = plan.get('sample_size', 100)  # Increased default from 30 to 100
        derived_fields = plan.get('derived_fields', {})
        
        if not x_field or not y_field:
            if verbose:
                print(f"      ⚠️  Missing x_field or y_field for correlation")
            return data[:sample_size]
        
        # Convert to DataFrame for cleaning
        df = list_to_dataframe(data)
        if df.empty:
            return []
        
        # Calculate derived fields if specified
        if derived_fields:
            if verbose:
                print(f"      🧮 Calculating derived fields...")
            for new_field, expression in derived_fields.items():
                try:
                    df[new_field] = self._calculate_derived_field(df, expression, verbose=verbose)
                    if verbose:
                        print(f"         ✅ Created '{new_field}' = {expression}")
                except Exception as e:
                    if verbose:
                        print(f"         ⚠️  Failed to create '{new_field}': {str(e)}")
                    # Set to NaN if calculation fails
                    df[new_field] = pd.NA
        
        # Clean correlation fields (including derived fields)
        if verbose:
            print(f"      🧹 Cleaning correlation fields...")
        for field in [x_field, y_field]:
            if field in df.columns:
                self._clean_field_for_aggregation(df, field, verbose=verbose)
        
        # Extract pairs (only non-null values) - use pandas for efficiency
        result_df = df[[x_field, y_field]].dropna()
        
        # Sample if too many - use pandas sample for better performance
        if len(result_df) > sample_size:
            if verbose:
                print(f"      📉 Sampling correlation data: {len(result_df)} → {sample_size} points")
            result_df = result_df.sample(n=sample_size, random_state=42)
        
        return dataframe_to_list(result_df)
    
    def _calculate_derived_field(
        self,
        df: pd.DataFrame,
        expression: str,
        verbose: bool = False
    ) -> pd.Series:
        """
        Calculate a derived field from an expression using pandas.eval().
        Supports complex arithmetic expressions with brackets, multiple operations, etc.
        
        Args:
            df: DataFrame containing source fields
            expression: String expression like "field1 / field2" or "field1 / (field2 + field3)"
            verbose: Whether to print debug info
        
        Returns:
            pd.Series with calculated values
        
        Examples:
            - "Yield / Area" → simple division
            - "Rented / (Owned + Rented)" → division with bracket
            - "(Revenue - Cost) / Revenue" → profit margin
        """
        try:
            # Use pandas eval to safely calculate the expression
            # This supports complex expressions with brackets, multiple operators, etc.
            result = df.eval(expression)
            
            # Convert to Series if it's not already (in case of scalar result)
            if not isinstance(result, pd.Series):
                result = pd.Series([result] * len(df), index=df.index)
            
            return result
            
        except Exception as e:
            # Provide helpful error message
            error_msg = str(e)
            
            # Check if it's a name error (field not found)
            if "name" in error_msg.lower() and "not defined" in error_msg.lower():
                # Try to extract field name from error
                import re
                match = re.search(r"name '([^']+)' is not defined", error_msg)
                if match:
                    missing_field = match.group(1)
                    raise ValueError(
                        f"Field '{missing_field}' not found in data. "
                        f"Available fields: {list(df.columns)}"
                    )
            
            # Generic error
            raise ValueError(
                f"Failed to calculate expression '{expression}': {error_msg}. "
                f"Make sure all field names are correct and exist in the data."
            )
    
    def _execute_sample_representative(
        self,
        data: List[Dict],
        plan: Dict[str, Any],
        verbose: bool
    ) -> List[Dict]:
        """Execute representative sampling"""
        sample_size = plan.get('sample_size', 20)
        ensure_diversity = plan.get('ensure_diversity', False)
        
        if not ensure_diversity or len(data) <= sample_size:
            return data[:sample_size]
        
        # Try to sample from different categories (simple heuristic)
        # Group by first categorical-looking field
        from collections import defaultdict
        groups = defaultdict(list)
        
        # Find a categorical field (field with limited unique values)
        if data:
            sample_record = data[0]
            for field in sample_record.keys():
                unique_values = set(r.get(field) for r in data[:100])
                if len(unique_values) < 20:  # Likely categorical
                    for record in data:
                        groups[record.get(field)].append(record)
                    break
        
        if groups:
            # Sample from each group
            result = []
            per_group = max(1, sample_size // len(groups))
            for records in groups.values():
                result.extend(records[:per_group])
            return result[:sample_size]
        else:
            return data[:sample_size]
    
    def _normalize_scene_ids(self, scenes: List[Dict]) -> List[Dict]:
        """
        统一重命名场景ID为标准格式：
        - scene_opening (只有一个)
        - scene_closing (只有一个)
        - scene_chart_1, scene_chart_2, ... (按顺序)
        - scene_stats, scene_stats_1, scene_stats_2, ... (如果有多个)
        """
        chart_count = 0
        stats_count = 0
        
        for scene in scenes:
            scene_type = scene.get('type', 'unknown')
            
            if scene_type == 'opening':
                scene['id'] = 'scene_opening'
            elif scene_type == 'closing':
                scene['id'] = 'scene_closing'
            elif scene_type == 'chart':
                chart_count += 1
                scene['id'] = f'scene_chart_{chart_count}'
            elif scene_type == 'stat_cards':
                stats_count += 1
                if stats_count == 1:
                    scene['id'] = 'scene_stats'
                else:
                    scene['id'] = f'scene_stats_{stats_count}'
            # 其他类型保持原样或使用默认格式
            elif not scene.get('id') or scene.get('id', '').startswith('temp_'):
                # 如果没有ID或是临时ID，根据类型生成
                if scene_type not in ['opening', 'closing', 'chart', 'stat_cards']:
                    scene['id'] = f'scene_{scene_type}_{chart_count + stats_count + 1}'
        
        return scenes
    
    def _merge_scenes(
        self,
        all_scenes: List[List[Dict]],
        query: str,
        sub_queries: List[Dict],
        language: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """Phase 2.5: Video Directing - Use LLM to arrange scenes and create custom opening/closing"""
        # Flatten all scenes
        merged_scenes = []
        for scenes in all_scenes:
            merged_scenes.extend(scenes)
        
        # Remove any opening/closing scenes from sub-queries (we'll create new ones)
        chart_scenes = [s for s in merged_scenes if s.get('type') == 'chart']
        stat_card_scenes = [s for s in merged_scenes if s.get('type') == 'stat_cards']
        other_scenes = [s for s in merged_scenes if s.get('type') not in ['opening', 'closing', 'chart', 'stat_cards']]
        
        # Combine all scenes that need to be arranged (excluding opening/closing)
        scenes_to_arrange = chart_scenes + stat_card_scenes + other_scenes
        
        # Create scene lookup dictionary
        scene_lookup = {s.get('id'): s for s in scenes_to_arrange}
        
        # Create mapping from scene ID to sub-query info (for priority and original order)
        scene_to_subquery = {}
        for i, (sub_query, scenes_list) in enumerate(zip(sub_queries, all_scenes)):
            for scene in scenes_list:
                scene_id = scene.get('id')
                if scene_id:
                    scene_to_subquery[scene_id] = {
                        "subquery_id": sub_query.get('id', f'subquery_{i+1}'),
                        "subquery_query": sub_query.get('query', ''),
                        "priority": sub_query.get('priority', 1.0),
                        "original_order": i + 1,  # 1-based index
                        "analysis_type": sub_query.get('analysis_type', 'comparison')
                    }
        
        if verbose:
            print(f"   🎬 Directing video: arranging {len(scenes_to_arrange)} scenes...")
        
        # Use LLM as video director to arrange scenes and create custom opening/closing
        try:
            prompt = format_video_director_prompt(query, scenes_to_arrange, scene_to_subquery, language)
            
            if verbose:
                print(f"   🎨 Creating custom opening and closing scenes...")
            
            director_output, usage = self.client.call_with_json_mode(
                prompt,
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                verbose=verbose
            )
            # Note: token_usage accumulation should be handled by caller
            
            # Validate director output structure
            if "meta" not in director_output:
                raise ValueError("Video director output missing meta field")
            if "scene_order" not in director_output:
                raise ValueError("Video director output missing scene_order field")
            if "opening" not in director_output:
                raise ValueError("Video director output missing opening scene")
            if "closing" not in director_output:
                raise ValueError("Video director output missing closing scene")
            
            # Validate scene_order contains all scene IDs
            scene_order = director_output.get("scene_order", [])
            original_scene_ids = set(scene_lookup.keys())
            ordered_scene_ids = set(scene_order)
            
            if original_scene_ids != ordered_scene_ids:
                missing = original_scene_ids - ordered_scene_ids
                extra = ordered_scene_ids - original_scene_ids
                if verbose:
                    if missing:
                        print(f"   ⚠️  Warning: Missing scenes in order: {missing}")
                    if extra:
                        print(f"   ⚠️  Warning: Extra scenes in order: {extra}")
                
                # Fix: add missing scenes, remove extra scenes
                scene_order = [sid for sid in scene_order if sid in original_scene_ids]
                for missing_id in missing:
                    scene_order.append(missing_id)
            
            # Assemble final scenes: opening + ordered scenes + closing
            final_scenes = []
            
            # Add opening scene
            opening = director_output.get("opening", {})
            if 'type' not in opening:
                opening['type'] = 'opening'
            opening.pop('time_range', None)
            for narr in opening.get('narration', []):
                narr.pop('time_start', None)
                narr.pop('time_end', None)
                narr.pop('audio_file', None)
            final_scenes.append(opening)
            
            # Add ordered scenes
            for scene_id in scene_order:
                if scene_id in scene_lookup:
                    scene = scene_lookup[scene_id]
                    # Ensure no timing fields
                    scene.pop('time_range', None)
                    for narr in scene.get('narration', []):
                        narr.pop('time_start', None)
                        narr.pop('time_end', None)
                        narr.pop('audio_file', None)
                    final_scenes.append(scene)
                else:
                    if verbose:
                        print(f"   ⚠️  Warning: Scene ID not found: {scene_id}")
            
            # Add closing scene
            closing = director_output.get("closing", {})
            if 'type' not in closing:
                closing['type'] = 'closing'
            closing.pop('time_range', None)
            for narr in closing.get('narration', []):
                narr.pop('time_start', None)
                narr.pop('time_end', None)
                narr.pop('audio_file', None)
            final_scenes.append(closing)
            
            # Normalize scene IDs to standard format
            final_scenes = self._normalize_scene_ids(final_scenes)
            
            config = {
                "meta": director_output.get("meta", {
                    "title": query[:50] + "..." if len(query) > 50 else query,
                    "fps": 30,
                    "width": 1280,
                    "height": 720
                }),
                "scenes": final_scenes
            }
            
            if verbose:
                scene_count = len([s for s in final_scenes if s.get('type') in ['chart', 'stat_cards']])
                print(f"   ✅ Video directed: {scene_count} content scenes arranged with custom opening/closing")
            
            return config
        
        except Exception as e:
            if verbose:
                print(f"   ⚠️  Video directing failed: {e}")
                print("   Using fallback merge...")
            
            # Fallback to simple merge (original logic)
            meta = {
                "title": query[:50] + "..." if len(query) > 50 else query,
                "fps": 30,
                "width": 1280,
                "height": 720
            }
            
            # Get background color from first chart scene
            ref_bg = "#0f1419"
            if chart_scenes:
                ref_style = chart_scenes[0].get('content', {}).get('style', {})
                ref_bg = ref_style.get('background_color', ref_bg)
            
            # Create simple opening scene
            opening_scene = {
                "id": "scene_opening",
                "type": "opening",
                "content": {
                    "title": meta["title"],
                    "subtitle": "Data Analysis",
                    "background": {
                        "type": "solid",
                        "color": ref_bg
                    },
                    "style": {
                        "text_color": "#ffffff",
                        "subtitle_color": "#e0e0e0"
                    }
                },
                "narration": [
                    {"text": f"Let's analyze: {query}"}
                ]
            }
            
            # Create simple closing scene
            closing_scene = {
                "id": "scene_closing",
                "type": "closing",
                "content": {
                    "title": "Thank You",
                    "style": {
                        "background": {
                            "type": "solid",
                            "color": ref_bg
                        },
                        "text_color": "#ffffff",
                        "subtitle_color": "#e0e0e0"
                    }
                },
                "narration": [
                    {"text": "That concludes our analysis"}
                ]
            }
            
            # Combine all scenes
            final_scenes = [opening_scene]
            final_scenes.extend(chart_scenes)
            final_scenes.extend(stat_card_scenes)
            final_scenes.extend(other_scenes)
            final_scenes.append(closing_scene)
            
            # Normalize scene IDs to standard format
            final_scenes = self._normalize_scene_ids(final_scenes)
            
            config = {
                "meta": meta,
                "scenes": final_scenes
            }
            
            if verbose:
                print(f"   ✅ Fallback merge: {len(chart_scenes)} chart scenes, {len(stat_card_scenes)} stat card scenes")
            
            return config
    
    def _analyze_data(self, query: str, data: List[Dict], language: str, verbose: bool) -> List[Dict]:
        """Phase 1: Data Analysis"""
        prompt = format_data_analyst_prompt(query, data, language)
        
        try:
            if verbose:
                print(f"   📊 Analyzing {len(data)} data records...")
            response, usage = self.client.call_with_json_mode(prompt, temperature=0.7, verbose=verbose)
            # Note: token_usage accumulation should be handled by caller
            insights = response.get("insights", [])
            
            if not insights:
                raise ValueError("No insights extracted")
            
            return insights
        
        except Exception as e:
            if verbose:
                print(f"⚠️  Data analysis failed: {e}")
                print("Using default insights...")
            
            # Return a default insight
            return [{
                "type": "comparison",
                "content": f"Analyzing {len(data)} records in the dataset",
                "importance": 0.8
            }]
    
    def _generate_opening_closing_scenes(
        self,
        query: str,
        generated_scenes: List[Dict],
        opening_ref: Dict[str, Any],
        closing_ref: Dict[str, Any],
        language: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """Phase 1b: Generate opening and closing scenes based on actual generated content"""
        
        # Create scenes summary for LLM
        scenes_summary = []
        for scene in generated_scenes:
            scene_type = scene.get('type', 'unknown')
            if scene_type in ['chart', 'stat_cards']:
                summary = {
                    "type": scene_type,
                    "title": scene.get('content', {}).get('title', 'Untitled'),
                    "chart_type": scene.get('content', {}).get('chart_type', ''),
                    "data_count": len(scene.get('content', {}).get('data', [])),
                }
                
                # Add brief data summary
                if scene_type == 'chart':
                    data = scene.get('content', {}).get('data', [])
                    if data:
                        # Get first few data points as examples
                        summary['sample_data'] = data[:2]
                
                scenes_summary.append(summary)
        
        # Extract reference info
        opening_title = opening_ref.get('title', 'Data Analysis') if opening_ref else 'Data Analysis'
        opening_goal = opening_ref.get('narrative_goal', 'Introduce the analysis') if opening_ref else 'Introduce the analysis'
        closing_title = closing_ref.get('title', 'Thank You') if closing_ref else 'Thank You'
        closing_goal = closing_ref.get('narrative_goal', 'Summarize key findings') if closing_ref else 'Summarize key findings'
        
        # Generate using LLM
        try:
            prompt = format_opening_closing_generator_prompt(
                query=query,
                scenes_summary=scenes_summary,
                opening_title=opening_title,
                opening_goal=opening_goal,
                closing_title=closing_title,
                closing_goal=closing_goal,
                language=language
            )
            
            if verbose:
                print(f"      🎨 Generating engaging opening and closing narrations...")
            
            result, usage = self.client.call_with_json_mode(
                prompt,
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                verbose=verbose
            )
            # Note: token_usage accumulation should be handled by caller
            
            # Ensure IDs match storyboard
            if 'opening' in result and opening_ref:
                result['opening']['id'] = opening_ref.get('id', 'scene_1')
            if 'closing' in result and closing_ref:
                result['closing']['id'] = closing_ref.get('id', 'scene_closing')
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"      ⚠️  Opening/closing generation failed: {e}, using fallback")
            
            # Fallback: create simple opening/closing
            fallback = {}
            
            if opening_ref:
                fallback['opening'] = {
                    "id": opening_ref.get('id', 'scene_1'),
                    "type": "opening",
                    "content": {
                        "title": opening_title,
                        "subtitle": opening_goal,
                        "background": {"type": "gradient", "colors": ["#0f1419", "#1a2332"]},
                        "style": {"text_color": "#ffffff", "subtitle_color": "#e0e0e0"}
                    },
                    "narration": [{"text": opening_goal}]
                }
            
            if closing_ref:
                fallback['closing'] = {
                    "id": closing_ref.get('id', 'scene_closing'),
                    "type": "closing",
                    "content": {
                        "title": closing_title,
                        "subtitle": closing_goal,
                        "background": {"type": "gradient", "colors": ["#1a2332", "#0f1419"]},
                        "style": {
                            "text_color": "#ffffff",
                            "subtitle_color": "#e0e0e0",
                            "background": {"type": "solid", "color": "#0f1419"}
                        }
                    },
                    "narration": [{"text": closing_goal}]
                }
            
            return fallback
    
    def _design_visual_only(
        self,
        sub_query: Dict[str, Any],
        data: List[Dict],
        language: str,
        verbose: bool,
        token_usage: Dict = None,
        include_narration: bool = False
    ) -> Dict[str, Any]:
        """
        Generate visual configuration (optionally with independent narration)
        
        Args:
            include_narration: If True, generate independent narration for ablation study
                              Uses visual_designer_with_narration prompt
        """
        query_text = sub_query.get('query', '')
        analysis_type = sub_query.get('analysis_type', 'comparison')
        planned_type = sub_query.get('type', 'chart')  # Get planned type from scene plan
        
        # Choose prompt based on whether narration is needed
        if include_narration:
            # Ablation mode: generate scene with independent narration
            from prompts import format_visual_designer_with_narration_prompt
            prompt = format_visual_designer_with_narration_prompt(
                query_text,
                analysis_type,
                data,
                language,
                planned_type=planned_type
            )
        else:
            # Normal mode: generate scene without narration
            prompt = format_visual_designer_prompt(
                query_text,
                analysis_type,
                data,
                language,
                planned_type=planned_type
            )
        
        try:
            config, usage = self.client.call_with_json_mode(
                prompt,
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                verbose=verbose
            )
            # 累计 token 使用量
            accumulate_token_usage(usage, token_usage)
            
            # Validate config
            if "scenes" not in config:
                raise ValueError("Config missing scenes field")
            
            scenes = config.get("scenes", [])
            if not scenes:
                raise ValueError("No scenes generated")
            
            # Get the first scene (should be only one)
            scene = scenes[0]
            
            # Validate scene has required fields
            # Note: stat_cards should not be generated here (they're generated in Phase 2)
            if scene.get('type') != 'chart':
                raise ValueError(f"Invalid scene type: {scene.get('type')}. Only 'chart' type should be generated in Phase 1. Stat cards are generated in Phase 2.")
            
            # Ensure no timing fields
            scene.pop("time_range", None)
            
            # Validate chart scene has required fields
            if scene.get('type') == 'chart':
                content = scene.get('content', {})
                if not content.get('chart_type'):
                    raise ValueError("Chart scene missing chart_type")
                if not content.get('data'):
                    raise ValueError("Chart scene missing data")
                if not content.get('data_binding'):
                    raise ValueError("Chart scene missing data_binding")
            
            # Check for insight_summary
            if not scene.get('insight_summary'):
                if verbose:
                    print(f"   ⚠️  Scene missing insight_summary, generating default...")
                scene['insight_summary'] = f"Analysis of {query_text}"
            
            return scene
        
        except Exception as e:
            if verbose:
                print(f"   ⚠️  Visual generation failed: {e}")
                print(f"   Trying fallback...")
            
            # Fallback: create a simple bar chart
            try:
                if not data:
                    return None
                
                # Get first two fields as x and y
                sample = data[0]
                fields = list(sample.keys())
                if len(fields) < 2:
                    return None
                
                x_field = fields[0]
                y_field = fields[1] if len(fields) > 1 else fields[0]
                
                return {
                    "id": "scene_chart_1",
                    "type": "chart",
                    "content": {
                        "chart_type": "bar_chart",
                        "title": query_text[:50],
                        "data": data[:20],
                        "data_binding": {
                            "x_axis": {"field": x_field, "label": x_field},
                            "y_axis": {"field": y_field, "label": y_field}
                        },
                        "style": {
                            "background_color": "#0f1419",
                            "container_background": "#0f1419",
                            "bar_color": "#5b8ff9",
                            "text_color": "#e8eaed"
                        },
                        "layout": {
                            "margin": {"top": 80, "right": 60, "bottom": 100, "left": 100},
                            "chart_area": {"width": 1120, "height": 540}
                        }
                    },
                    "insight_summary": f"Analysis of {query_text}"
                }
            except:
                return None
    
    def _filter_visual_fields(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out visual-only fields (style, layout) that Narrative Director doesn't need"""
        import copy
        
        scene_copy = copy.deepcopy(scene)
        
        # Remove visual styling fields from content (Narrative Director doesn't need these)
        if 'content' in scene_copy:
            content = scene_copy['content']
            # Remove style and layout (visual-only, not needed for narration)
            content.pop('style', None)
            content.pop('layout', None)
        
        return scene_copy
    
    def _generate_unified_narrative(
        self,
        query: str,
        scenes_info: List[Dict],
        opening_ref: Dict[str, Any],
        closing_ref: Dict[str, Any],
        language: str,
        verbose: bool,
        token_usage: Dict = None
    ) -> Dict[str, Any]:
        """Phase 2: Generate unified narrative and scene ordering"""
        
        prompt = format_narrative_director_prompt(
            query=query,
            scenes_info=scenes_info,
            language=language
        )
        
        try:
            if verbose:
                print(f"      🎨 Generating unified script and scene order...")
            
            result, usage = self.client.call_with_json_mode(
                prompt,
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                verbose=verbose
            )
            # 累计 token 使用量
            accumulate_token_usage(usage, token_usage)
            
            # Validate result
            if 'scene_order' not in result:
                raise ValueError("Narrative result missing scene_order")
            if 'opening' not in result:
                raise ValueError("Narrative result missing opening")
            if 'closing' not in result:
                raise ValueError("Narrative result missing closing")
            if 'scene_narrations' not in result:
                raise ValueError("Narrative result missing scene_narrations")
            
            # Set standard IDs (no references in new flow)
            result['opening']['id'] = 'scene_opening'
            result['closing']['id'] = 'scene_closing'
            
            # Validate and set stat_cards ID if present
            if 'stat_cards' in result:
                stat_cards = result['stat_cards']
                if not stat_cards.get('id'):
                    stat_cards['id'] = 'scene_stats'
                # Ensure stat_cards has required fields
                if 'content' not in stat_cards:
                    if verbose:
                        print(f"      ⚠️  Stat cards missing content, removing...")
                    del result['stat_cards']
                elif 'cards' not in stat_cards.get('content', {}):
                    if verbose:
                        print(f"      ⚠️  Stat cards missing cards array, removing...")
                    del result['stat_cards']
            
            if verbose:
                scene_count = len(result['scene_order'])
                stat_cards_info = ""
                if 'stat_cards' in result:
                    cards_count = len(result['stat_cards'].get('content', {}).get('cards', []))
                    stat_cards_info = f" + 1 stat_cards ({cards_count} metrics)"
                print(f"      ✅ Generated script with {scene_count} chart scenes{stat_cards_info}")
                print(f"         Opening: \"{result['opening']['narration'][0]['text'][:50]}...\"")
                print(f"         Closing: \"{result['closing']['narration'][0]['text'][:50]}...\"")
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"      ⚠️  Unified narrative generation failed ({type(e).__name__}): {e}, using fallback")
            
            # Fallback: create simple opening/closing
            fallback = {
                'scene_order': [s['id'] for s in scenes_info],
                'scene_narrations': {},
                'opening': {
                    "id": 'scene_opening',
                    "type": "opening",
                    "content": {
                        "title": query[:50] if len(query) <= 50 else query[:47] + "...",
                        "subtitle": "Data Analysis",
                        "background": {"type": "gradient", "colors": ["#0f1419", "#1a2332"]},
                        "style": {"text_color": "#ffffff", "subtitle_color": "#e0e0e0"}
                    },
                    "narration": [{"text": f"Let's analyze: {query}"}]
                },
                'closing': {
                    "id": 'scene_closing',
                    "type": "closing",
                    "content": {
                        "title": "Thank You",
                        "background": {"type": "gradient", "colors": ["#1a2332", "#0f1419"]},
                        "style": {
                            "text_color": "#ffffff",
                            "subtitle_color": "#e0e0e0",
                            "background": {"type": "solid", "color": "#0f1419"}
                        }
                    },
                    "narration": [{"text": "That concludes our analysis."}]
                }
            }
            
            # Generate simple narrations for each scene
            for scene_info in scenes_info:
                sid = scene_info['id']
                insight = scene_info.get('insight_summary', 'Data visualization')
                fallback['scene_narrations'][sid] = [{"text": insight}]
            
            return fallback
    
    def _design_scene_from_subquery(
        self,
        sub_query: Dict[str, Any],
        data: List[Dict],
        language: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """Generate a single scene from sub-query and data (legacy method, kept for compatibility)"""
        query_text = sub_query.get('query', '')
        analysis_type = sub_query.get('analysis_type', 'comparison')
        
        prompt = format_scene_designer_subquery_prompt(
            query_text,
            analysis_type,
            data,
            language
        )
        
        try:
            config, usage = self.client.call_with_json_mode(
                prompt,
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                verbose=verbose
            )
            # Note: token_usage accumulation should be handled by caller
            
            # Validate config
            if "scenes" not in config:
                raise ValueError("Config missing scenes field")
            
            scenes = config.get("scenes", [])
            if not scenes:
                raise ValueError("No scenes generated")
            
            # Get the first scene (should be only one)
            scene = scenes[0]
            
            # Validate scene has required fields
            if scene.get('type') not in ['chart', 'stat_cards']:
                raise ValueError(f"Invalid scene type: {scene.get('type')}")
            
            # Ensure no timing fields
            scene.pop("time_range", None)
            for narr in scene.get("narration", []):
                narr.pop("time_start", None)
                narr.pop("time_end", None)
                narr.pop("audio_file", None)
            
            # Validate chart scene has required fields
            if scene.get('type') == 'chart':
                content = scene.get('content', {})
                if not content.get('chart_type'):
                    raise ValueError("Chart scene missing chart_type")
                if not content.get('data'):
                    raise ValueError("Chart scene missing data")
                if not content.get('data_binding'):
                    raise ValueError("Chart scene missing data_binding")
            
            return scene
        
        except Exception as e:
            if verbose:
                print(f"   ⚠️  Scene generation failed: {e}")
                print(f"   Trying fallback...")
            
            # Fallback: create a simple bar chart
            try:
                if not data:
                    return None
                
                # Get first two fields as x and y
                sample = data[0]
                fields = list(sample.keys())
                if len(fields) < 2:
                    return None
                
                x_field = fields[0]
                y_field = fields[1] if len(fields) > 1 else fields[0]
                
                return {
                    "id": "scene_chart_1",
                    "type": "chart",
                    "content": {
                        "chart_type": "bar_chart",
                        "title": query_text[:50],
                        "data": data[:20],
                        "data_binding": {
                            "x_axis": {"field": x_field, "label": x_field},
                            "y_axis": {"field": y_field, "label": y_field}
                        },
                        "style": {
                            "background_color": "#0f1419",
                            "container_background": "#0f1419",
                            "bar_color": "#5b8ff9",
                            "text_color": "#e8eaed"
                        },
                        "layout": {
                            "margin": {"top": 80, "right": 60, "bottom": 100, "left": 100},
                            "chart_area": {"width": 1120, "height": 540}
                        }
                    },
                    "narration": [
                        {"text": f"Let's examine {query_text.lower()}"}
                    ]
                }
            except:
                return None
    
    def _design_scenes(
        self,
        query: str,
        insights: List[Dict],
        data: List[Dict],
        language: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """Phase 2: Scene Design (legacy method, kept for compatibility)"""
        prompt = format_scene_designer_prompt(query, insights, data, language)
        
        try:
            if verbose:
                print(f"   🎨 Designing scenes based on {len(insights)} insights...")
            config, usage = self.client.call_with_json_mode(prompt, temperature=0.7, max_tokens=MAX_TOKENS, verbose=verbose)
            # Note: token_usage accumulation should be handled by caller
            
            # Validate config
            if "meta" not in config or "scenes" not in config:
                raise ValueError("Config missing required fields")
            
            # Ensure no timing fields (cleanup)
            config = self._clean_time_fields(config)
            
            # Filter out scenes with single data point (poor visualization)
            config = self._filter_single_data_point_scenes(config, verbose)
            
            # Normalize background colors across all scenes
            config = self._normalize_background_colors(config, verbose)
            
            return config
        
        except Exception as e:
            if verbose:
                print(f"⚠️  Scene design failed: {e}")
                print("Using default config...")
            
            # Return a minimal config
            return self._create_fallback_config(query, data)
    
    def _filter_single_data_point_scenes(self, config: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        """
        过滤掉只有单个数据点的图表场景（不适合可视化）
        
        对于单数据点的场景：
        - 如果是find_extremum类型，可以考虑转换为stat_card（但这里先直接过滤）
        - 其他情况直接移除
        """
        scenes = config.get('scenes', [])
        if not scenes:
            return config
        
        filtered_scenes = []
        removed_count = 0
        
        for scene in scenes:
            scene_type = scene.get('type', '')
            scene_id = scene.get('id', 'unknown')
            
            # 只检查图表场景
            if scene_type == 'chart':
                content = scene.get('content', {})
                data = content.get('data', [])
                chart_type = content.get('chart_type', '')
                
                # 检查数据点数量
                data_count = len(data) if isinstance(data, list) else 0
                
                # 根据图表类型确定最小数据点要求
                min_required = 2  # 默认至少2个数据点
                if chart_type == 'line_chart':
                    min_required = 3  # 折线图至少需要3个时间点
                elif chart_type == 'scatter_chart':
                    min_required = 3  # 散点图至少需要3个点才能看出相关性
                elif chart_type == 'pie_chart':
                    min_required = 2  # 饼图至少需要2个分类
                elif chart_type == 'heatmap':
                    min_required = 4  # 热力图至少需要4个数据点才能形成有意义的网格
                
                if data_count < min_required:
                    if verbose:
                        print(f"   ⚠️  Filtered out scene {scene_id}: {chart_type} with only {data_count} data point(s) (minimum {min_required} required)")
                    removed_count += 1
                    continue
            
            # 保留其他场景
            filtered_scenes.append(scene)
        
        if removed_count > 0 and verbose:
            print(f"✅ Filtered {removed_count} scene(s) with insufficient data points")
        
        config['scenes'] = filtered_scenes
        return config
    
    def _normalize_background_colors(self, config: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        """
        统一所有场景的背景色（background_color 和 container_background）
        如果发现不一致，统一为第一个图表场景的值
        """
        scenes = config.get('scenes', [])
        if not scenes:
            return config
        
        # 找到第一个图表场景作为参考（优先选择 chart 类型）
        reference_scene = None
        for scene in scenes:
            if scene.get('type') == 'chart':
                reference_scene = scene
                break
        
        # 如果没有图表场景，使用第一个有 style 的场景
        if not reference_scene:
            for scene in scenes:
                content = scene.get('content', {})
                style = content.get('style', {})
                if style and style.get('background_color'):
                    reference_scene = scene
                    break
        
        # 如果还是找不到，使用第一个场景
        if not reference_scene:
            reference_scene = scenes[0]
        
        # 获取参考背景色
        ref_style = reference_scene.get('content', {}).get('style', {})
        ref_bg = ref_style.get('background_color')
        ref_container = ref_style.get('container_background', ref_bg)
        
        if not ref_bg:
            if verbose:
                print("⚠️  No reference background_color found, skipping normalization")
            return config
        
        # 统一所有场景的背景色
        normalized_count = 0
        for scene in scenes:
            content = scene.get('content', {})
            style = content.get('style', {})
            scene_type = scene.get('type', '')
            
            # 处理图表场景和 stat_cards 场景（使用 style.background_color）
            if scene_type in ['chart', 'stat_cards']:
                if not style:
                    continue
                
                current_bg = style.get('background_color')
                current_container = style.get('container_background', current_bg)
                
                if current_bg != ref_bg or current_container != ref_container:
                    style['background_color'] = ref_bg
                    style['container_background'] = ref_container
                    normalized_count += 1
            
            # 处理 Opening 场景（使用 content.background）
            elif scene_type == 'opening':
                background = content.get('background', {})
                if not background:
                    # 如果没有 background，创建一个
                    background = {'type': 'solid', 'color': ref_bg}
                    content['background'] = background
                    normalized_count += 1
                else:
                    if background.get('type') == 'gradient':
                        current_colors = background.get('colors', [])
                        if current_colors and current_colors[0] != ref_bg:
                            # 统一为单一背景色（使用纯色，不使用渐变）
                            background['type'] = 'solid'
                            background['color'] = ref_bg
                            if 'colors' in background:
                                del background['colors']
                            normalized_count += 1
                        elif not current_colors:
                            # 如果没有 colors，添加
                            background['type'] = 'solid'
                            background['color'] = ref_bg
                            normalized_count += 1
                    else:
                        # 如果是 solid 类型或其他
                        current_color = background.get('color', background.get('colors', [ref_bg])[0] if background.get('colors') else ref_bg)
                        if current_color != ref_bg:
                            background['type'] = 'solid'
                            background['color'] = ref_bg
                            if 'colors' in background:
                                del background['colors']
                            normalized_count += 1
            
            # 处理 Closing 场景（使用 content.style.background）
            elif scene_type == 'closing':
                if not style:
                    style = {}
                    content['style'] = style
                
                background = style.get('background', {})
                if not background:
                    # 如果没有 background，创建一个
                    background = {'type': 'solid', 'color': ref_bg}
                    style['background'] = background
                    normalized_count += 1
                else:
                    if background.get('type') == 'gradient':
                        current_colors = background.get('colors', [])
                        if current_colors and current_colors[0] != ref_bg:
                            # 统一为单一背景色（使用纯色，不使用渐变）
                            background['type'] = 'solid'
                            background['color'] = ref_bg
                            if 'colors' in background:
                                del background['colors']
                            normalized_count += 1
                        elif not current_colors:
                            # 如果没有 colors，添加
                            background['type'] = 'solid'
                            background['color'] = ref_bg
                            normalized_count += 1
                    else:
                        # 如果是 solid 类型或其他
                        current_color = background.get('color', background.get('colors', [ref_bg])[0] if background.get('colors') else ref_bg)
                        if current_color != ref_bg:
                            background['type'] = 'solid'
                            background['color'] = ref_bg
                            if 'colors' in background:
                                del background['colors']
                            normalized_count += 1
        
        if verbose and normalized_count > 0:
            print(f"✅ Normalized background colors: {normalized_count} scenes updated")
            print(f"   Unified background_color: {ref_bg}")
            print(f"   Unified container_background: {ref_container}")
        
        return config
    
    def _add_animations(self, config: Dict, verbose: bool, token_usage: Dict = None) -> tuple[Dict, bool]:
        """Phase 4: Add Animations (Parallel Generation)
        
        Returns:
            tuple: (config, animations_added)
                - config: Config with or without animations
                - animations_added: True if animations were successfully added, False otherwise
        """
        scenes = config.get("scenes", [])
        if not scenes:
            return config, False
        
        # All scenes need animations
        scenes_to_animate = [
            (i, scene) for i, scene in enumerate(scenes)
        ]
        
        if not scenes_to_animate:
            return config, False
        
        if verbose:
            print(f"   🎬 Generating animations for {len(scenes_to_animate)} scenes in parallel...")
        
        # Prepare context for each scene
        def prepare_scene_context(scene_index: int, scene: Dict) -> Dict:
            """Prepare context information for a scene"""
            def extract_scene_summary(scene: Dict) -> Dict:
                """Extract essential info from adjacent scene (remove data, style, layout to save tokens)"""
                if not scene:
                    return None
                
                summary = {
                    "id": scene.get("id", ""),
                    "type": scene.get("type", "unknown")
                }
                
                # Extract content info but remove data, style, layout
                content = scene.get("content", {})
                if content:
                    content_summary = {}
                    # Keep essential fields
                    if "chart_type" in content:
                        content_summary["chart_type"] = content["chart_type"]
                    if "title" in content:
                        content_summary["title"] = content["title"]
                    if "data_binding" in content:
                        content_summary["data_binding"] = content["data_binding"]
                    # Explicitly exclude: data, style, layout
                    if content_summary:
                        summary["content"] = content_summary
                
                # Keep other useful fields
                if "insight_summary" in scene:
                    summary["insight_summary"] = scene["insight_summary"]
                if "narrative_goal" in scene:
                    summary["narrative_goal"] = scene["narrative_goal"]
                if "priority" in scene:
                    summary["priority"] = scene["priority"]
                if "narration" in scene:
                    summary["narration"] = scene["narration"]
                
                return summary
            
            return {
                "position": scene_index + 1,  # 1-based
                "total_scenes": len(scenes),
                "previous_scene": extract_scene_summary(scenes[scene_index - 1] if scene_index > 0 else None),
                "next_scene": extract_scene_summary(scenes[scene_index + 1] if scene_index < len(scenes) - 1 else None)
            }
        
        # Generate animations in parallel
        def generate_scene_animations_wrapper(args):
            scene_index, scene = args
            try:
                context = prepare_scene_context(scene_index, scene)
                prompt = format_scene_animation_generator_prompt(
                    current_scene=scene,
                    context=context,
                    language="English"  # TODO: get from config
                )
                
                result, usage = self.client.call_with_json_mode(
                    prompt,
                    temperature=0.6,
                    max_tokens=MAX_TOKENS,
                    verbose=False  # Reduce verbose in parallel mode
                )
                
                animations = result.get("animations", [])
                return (scene_index, scene.get('id'), animations, None, usage)
            except Exception as e:
                return (scene_index, scene.get('id'), [], str(e), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        
        # Parallel execution
        animation_results = {}  # scene_index -> animations
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=min(len(scenes_to_animate), 5)) as executor:
            futures = [
                executor.submit(generate_scene_animations_wrapper, (idx, scene))
                for idx, scene in scenes_to_animate
            ]
            
            for future in as_completed(futures):
                scene_index, scene_id, animations, error, usage = future.result()
                # 累计 token 使用量
                if token_usage is not None:
                    accumulate_token_usage(usage, token_usage)
                if error:
                    if verbose:
                        print(f"   ⚠️  Failed to generate animations for {scene_id}: {error}")
                    failed_count += 1
                else:
                    animation_results[scene_index] = animations
                    if verbose:
                        anim_count = len(animations)
                        print(f"   ✅ Generated {anim_count} animation(s) for {scene_id}")
        
        # Apply animations to scenes
        if animation_results:
            for scene_index, animations in animation_results.items():
                scenes[scene_index]['animations'] = animations
            
            # Clean animation time fields
            config = self._clean_animation_time_fields(config)
            
            if verbose:
                total_animations = sum(len(s.get('animations', [])) for s in scenes)
                print(f"   ✅ Total animations added: {total_animations}")
            
            return config, True
        else:
            if verbose:
                print(f"   ⚠️  Failed to generate animations for all scenes")
            return config, False
    
    def _clean_time_fields(self, config: Dict) -> Dict:
        """Clean timing fields from config"""
        # Remove top-level video_duration
        config.get("meta", {}).pop("video_duration", None)
        
        # Remove scene timing fields
        for scene in config.get("scenes", []):
            scene.pop("time_range", None)
            
            # Remove narration timing fields
            for narr in scene.get("narration", []):
                narr.pop("time_start", None)
                narr.pop("time_end", None)
                narr.pop("audio_file", None)
        
        return config
    
    def _clean_animation_time_fields(self, config: Dict) -> Dict:
        """Clean manually set timing fields from animations"""
        for scene in config.get("scenes", []):
            for anim in scene.get("animations", []):
                # Remove manually set timing (should be driven by trigger_narration)
                anim.pop("time_start", None)
                # duration can be kept (as override)
        
        return config
    
    def _create_fallback_config(self, query: str, data: List[Dict]) -> Dict:
        """Create fallback config"""
        # Try to guess fields
        if not data:
            raise ValueError("Data is empty")
        
        sample = data[0]
        fields = list(sample.keys())
        
        # Guess x and y fields
        x_field = fields[0]
        y_field = fields[1] if len(fields) > 1 else fields[0]
        
        # Create short title from query (max 10 words)
        def shorten_title(text: str, max_words: int = 10) -> str:
            if not text:
                return "Data Analysis"
            words = text.split()
            if len(words) <= max_words:
                return text
            # Try to extract key phrase (first few words or key terms)
            # If query is very long, use first part
            return " ".join(words[:max_words]) + "..."
        
        short_title = shorten_title(query, 10)
        
        return {
            "meta": {
                "title": short_title,
                "fps": 30,
                "width": 1280,
                "height": 720
            },
            "scenes": [
                {
                    "id": "scene_opening",
                    "type": "opening",
                    "content": {
                        "title": short_title,
                        "subtitle": "Data-driven Insights"
                    },
                    "narration": [
                        {"text": "Let's analyze this data together"}
                    ]
                },
                {
                    "id": "scene_chart_1",
                    "type": "chart",
                    "content": {
                        "chart_type": "bar_chart",
                        "title": "Data Visualization",
                        "data": data[:20],  # Limit data amount
                        "x_axis": {"field": x_field, "label": x_field},
                        "y_axis": {"field": y_field, "label": y_field}
                    },
                    "narration": [
                        {"text": "Here is our data visualization"}
                    ]
                },
                {
                    "id": "scene_closing",
                    "type": "closing",
                    "content": {
                        "title": "Thanks for Watching"
                    },
                    "narration": [
                        {"text": "That concludes our analysis"}
                    ]
                }
            ]
        }
    
    def _simple_narrative_assembly(
        self,
        query: str,
        scenes_info: List[Dict],
        generated_scenes_map: Dict,
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Ablation mode: Simple scene assembly without intelligent orchestration
        
        Used when skip_orchestration=True for ablation study (w/o Orchestration).
        
        Key differences from normal mode:
        - Keep original scene plan order (NO sorting, no intelligent reordering)
        - Scenes already have independent narrations from Phase 1 (no unified generation)
        - Simple template-based opening/closing (no LLM call)
        - No scene filtering (keep all generated scenes)
        """
        
        # 1. Keep original scene plan order (NO sorting for true w/o Orchestration baseline)
        # Note: This is intentionally weaker than normal mode to show orchestration value
        scene_order = [s['id'] for s in scenes_info]
        
        if verbose:
            print(f"   📊 Scene order (original plan order): {len(scene_order)} scenes")
            for i, sid in enumerate(scene_order, 1):
                priority = next((s.get('priority', 0.5) for s in scenes_info if s['id'] == sid), 0.5)
                print(f"      {i}. {sid} (priority: {priority:.2f})")
        
        # 2. Scenes already have narrations from Phase 1
        # No need to generate scene_narrations - they're already in generated_scenes_map
        scene_narrations = {}
        narration_count = 0
        for sid in scene_order:
            if sid in generated_scenes_map:
                existing_narration = generated_scenes_map[sid].get('narration', [])
                if existing_narration:
                    scene_narrations[sid] = existing_narration
                    narration_count += 1
        
        if verbose:
            print(f"   💬 Using {narration_count} independent narrations from Phase 1")
        
        # 3. Simple template-based opening (no LLM call)
        opening = {
            "id": "scene_opening",
            "type": "opening",
            "content": {
                "title": query[:50] if len(query) <= 50 else query[:47] + "...",
                "subtitle": "Data Analysis",
                "background": {"type": "gradient", "colors": ["#0f1419", "#1a2332"]},
                "style": {"text_color": "#ffffff", "subtitle_color": "#e0e0e0"}
            },
            "narration": [{"text": "Data analysis."}]
        }
        
        # 4. Simple template-based closing (no LLM call)
        closing = {
            "id": "scene_closing",
            "type": "closing",
            "content": {
                "title": "Thank You",
                "background": {"type": "gradient", "colors": ["#1a2332", "#0f1419"]},
                "style": {"text_color": "#ffffff", "subtitle_color": "#e0e0e0"}
            },
            "narration": [{"text": "Thank you."}]
        }
        
        if verbose:
            print(f"   ✅ Simple assembly complete")
            print(f"      - Opening: \"{opening['narration'][0]['text']}\"")
            print(f"      - {len(scene_order)} data scenes (with independent narrations)")
            print(f"      - Closing: \"{closing['narration'][0]['text']}\"")
        
        return {
            'scene_order': scene_order,
            'scene_narrations': scene_narrations,  # Already in generated_scenes_map
            'opening': opening,
            'closing': closing
            # Note: No stat_cards in ablation mode
        }
    
    def _generate_without_decomposition(
        self,
        query: str,
        data: List[Dict],
        metadata: Dict[str, Any],
        language: str,
        verbose: bool,
        skip_orchestration: bool,
        total_token_usage: Dict,
        phase_token_usage: Dict,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Generate video config without scene decomposition (ablation study: w/o Decomposition)
        
        Flow:
        1. Data Transform Planner: Analyze original query, generate transformation plans for multiple scenes
        2. Execute data transformations
        3. Visual Designer Batch: Generate all scene visualizations at once
        4. Narrative Director: Orchestrate scenes (or skip if skip_orchestration=True)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Step 1: Data Transform Planner (from original query)
        if verbose:
            print("\n🔍 Step 1: Data Transform Planning (Direct from Query)...")
        if progress_callback:
            progress_callback('planning', 10)
        
        # Generate transformation plans directly from query
        # Only pass metadata (same as normal flow), no sample data
        prompt = format_data_transform_planner_direct_prompt(
            query=query,
            metadata=metadata,
            language=language
        )
        
        try:
            response, usage = self.client.call_with_json_mode(
                prompt, 
                temperature=0.7, 
                verbose=verbose
            )
            accumulate_token_usage(usage, phase_token_usage["phase_0_scene_planning"])
            accumulate_token_usage(usage, total_token_usage)
            
            scenes_plan = response.get("scenes", [])
            if not scenes_plan:
                raise DataPreparationError("No scenes generated from data transform planner")
            
            if verbose:
                print(f"   ✅ Generated {len(scenes_plan)} scene transformation plans")
                for i, scene_plan in enumerate(scenes_plan, 1):
                    scene_id = scene_plan.get('scene_id', f'scene_{i}')
                    trans_type = scene_plan.get('transformation_type', 'unknown')
                    description = scene_plan.get('description', 'N/A')
                    print(f"      {i}. [{scene_id}] {trans_type} - {description}")
        
        except Exception as e:
            if verbose:
                print(f"   ❌ Data transform planning failed: {e}")
            raise DataPreparationError(f"Data transform planning failed: {e}")
        
        # Step 2: Execute data transformations
        if verbose:
            print("\n🔧 Step 2: Executing Data Transformations...")
        if progress_callback:
            progress_callback('processing', 30)
        
        transformed_data_map = {}
        
        def execute_transformation_wrapper(scene_plan):
            scene_id = scene_plan.get('scene_id', 'unknown')
            try:
                transformed_data = self._execute_data_transformation(
                    data,
                    scene_plan,
                    verbose=False
                )
                return (scene_id, transformed_data)
            except Exception as e:
                if verbose:
                    print(f"   ❌ Data transformation failed for {scene_id}: {e}")
                return (scene_id, [])
        
        # Execute transformations in parallel
        with ThreadPoolExecutor(max_workers=min(len(scenes_plan) + 1, 5)) as executor:
            futures = {executor.submit(execute_transformation_wrapper, scene_plan): scene_plan 
                      for scene_plan in scenes_plan}
            for future in as_completed(futures):
                scene_id, transformed_data = future.result()
                transformed_data_map[scene_id] = transformed_data
                if verbose:
                    if transformed_data:
                        print(f"   ✅ Data transformed for {scene_id}: {len(transformed_data)} records")
                    else:
                        print(f"   ⚠️  Data transformation for {scene_id}: No data returned")
        
        # Check failure rate
        empty_count = sum(1 for data in transformed_data_map.values() if not data)
        if empty_count == len(scenes_plan):
            raise DataPreparationError("All data transformations failed")
        elif empty_count / len(scenes_plan) > 0.8:
            if verbose:
                print(f"   ⚠️  Warning: {empty_count}/{len(scenes_plan)} transformations failed")
        
        # Step 3: Visual Designer Batch (generate all scenes at once)
        if verbose:
            print("\n🎨 Step 3: Generating Visual Configurations (Batch)...")
        if progress_callback:
            progress_callback('designing', 50)
        
        # Prepare scenes data for batch visual designer
        scenes_data_for_visual = []
        for scene_plan in scenes_plan:
            scene_id = scene_plan.get('scene_id', 'unknown')
            if scene_id in transformed_data_map and transformed_data_map[scene_id]:
                scenes_data_for_visual.append({
                    'scene_id': scene_id,
                    'description': scene_plan.get('description', 'N/A'),
                    'analysis_type': scene_plan.get('analysis_type', 'comparison'),
                    'transformed_data': transformed_data_map[scene_id]
                })
        
        if not scenes_data_for_visual:
            raise FatalGenerationError("No valid transformed data for visualization")
        
        # Generate visualizations for all scenes at once
        prompt = format_visual_designer_batch_prompt(
            query=query,
            scenes_data=scenes_data_for_visual,
            language=language
        )
        
        try:
            visual_config, usage = self.client.call_with_json_mode(
                prompt,
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                verbose=verbose
            )
            accumulate_token_usage(usage, phase_token_usage["phase_1_visual_generation"])
            accumulate_token_usage(usage, total_token_usage)
            
            generated_scenes = visual_config.get("scenes", [])
            if not generated_scenes:
                raise FatalGenerationError("No scenes generated from visual designer batch")
            
            # Build generated_scenes_map
            generated_scenes_map = {}
            for scene in generated_scenes:
                scene_id = scene.get('id', 'unknown')
                generated_scenes_map[scene_id] = scene
                if verbose:
                    s_type = scene.get('type', 'unknown').upper()
                    title = scene.get('content', {}).get('title', 'Untitled')
                    print(f"   ✅ Generated [{s_type}] {title}")
        
        except Exception as e:
            if verbose:
                print(f"   ❌ Visual generation failed: {e}")
            raise FatalGenerationError(f"Visual generation failed: {e}")
        
        # Step 4: Prepare scenes for Narrative Director
        if verbose:
            print("\n📋 Step 4: Preparing Scenes for Narrative Director...")
        
        scenes_for_narrative = []
        for scene_plan in scenes_plan:
            scene_id = scene_plan.get('scene_id', 'unknown')
            if scene_id in generated_scenes_map:
                scene = generated_scenes_map[scene_id]
                scene_copy = self._filter_visual_fields(scene)
                scenes_for_narrative.append(scene_copy)
        
        if verbose:
            print(f"   ✅ Prepared {len(scenes_for_narrative)} scenes")
        
        # Step 5: Narrative Director (or skip if skip_orchestration=True)
        if skip_orchestration:
            if verbose:
                print("\n⏭️  Step 5: Skipping Orchestration (Ablation Mode)...")
            if progress_callback:
                progress_callback('generating_narrative', 70)
            
            narrative_result = self._simple_narrative_assembly(
                query=query,
                scenes_info=scenes_for_narrative,
                generated_scenes_map=generated_scenes_map,
                verbose=verbose
            )
        else:
            if verbose:
                print("\n🎬 Step 5: Generating Unified Narration & Ordering Scenes...")
            if progress_callback:
                progress_callback('generating_narrative', 70)
            
            narrative_result = self._generate_unified_narrative(
                query=query,
                scenes_info=scenes_for_narrative,
                opening_ref=None,
                closing_ref=None,
                language=language,
                verbose=verbose,
                token_usage=phase_token_usage["phase_2_narrative_generation"]
            )
            accumulate_token_usage(phase_token_usage["phase_2_narrative_generation"], total_token_usage)
        
        # Apply narrations to scenes
        if narrative_result:
            scene_order = narrative_result.get('scene_order', [])
            scene_narrations = narrative_result.get('scene_narrations', {})
            opening = narrative_result.get('opening')
            closing = narrative_result.get('closing')
            stat_cards = narrative_result.get('stat_cards')
            
            # Update scenes with narration
            for sid, narrations in scene_narrations.items():
                if sid in generated_scenes_map:
                    generated_scenes_map[sid]['narration'] = narrations
            
            # Add opening/closing
            if opening:
                generated_scenes_map[opening['id']] = opening
            if closing:
                generated_scenes_map[closing['id']] = closing
            if stat_cards:
                # stat_cards is a single dict (one stat_cards scene), not a list
                stat_cards_id = stat_cards.get('id', 'scene_stats')
                generated_scenes_map[stat_cards_id] = stat_cards
        
        # Assemble final config (same logic as normal flow)
        final_scenes = []
        if narrative_result:
            scene_order = narrative_result.get('scene_order', [])
            
            # Add opening first (same as normal flow)
            if opening and opening['id'] in generated_scenes_map:
                final_scenes.append(generated_scenes_map[opening['id']])
            
            # Add scenes in narrative order
            for sid in scene_order:
                if sid in generated_scenes_map:
                    final_scenes.append(generated_scenes_map[sid])
                else:
                    if verbose:
                        print(f"   ⚠️  Scene in order but not found: {sid}")
            
            # Add closing last (same as normal flow)
            if closing and closing['id'] in generated_scenes_map:
                final_scenes.append(generated_scenes_map[closing['id']])
        
        # Build final config
        config = {
            "meta": {
                "title": query[:50] if len(query) <= 50 else query[:47] + "...",
                "fps": 30,
                "width": 1280,
                "height": 720
            },
            "scenes": final_scenes,
            "token_usage": total_token_usage,
            "phase_token_usage": phase_token_usage
        }
        
        if verbose:
            print("\n" + "="*60)
            print("✅ Generation Complete (w/o Decomposition)")
            print("="*60)
            print(f"Total scenes: {len(final_scenes)}")
        
        return config


def create_generator(
    api_base: str = None,
    api_key: str = None,
    model: str = None,
    debug_prompts: bool = False
) -> SimpleConfigGenerator:
    """Create config generator (factory function)
    
    In DeepEye-DataMagic, this function is used by VideoGeneratorHandler.
    It should get api_base/api_key/model from settings if not provided.
    """
    resolved_api_base = api_base
    resolved_api_key = api_key
    resolved_model = model

    # Try to import settings if available
    try:
        from app.core.config import settings
        resolved_api_base = resolved_api_base or settings.LLM_BASE_URL
        resolved_api_key = resolved_api_key or settings.LLM_API_KEY
        resolved_model = resolved_model or settings.LLM_MODEL
    except ImportError:
        # Fallback if settings not available
        import os

        resolved_api_base = resolved_api_base or os.getenv("LLM_BASE_URL")
        resolved_api_key = resolved_api_key or os.getenv("LLM_API_KEY")
        resolved_model = resolved_model or os.getenv("LLM_MODEL")

    if not resolved_api_base:
        raise ValueError("LLM_BASE_URL is required for video generation")
    if not resolved_api_key:
        raise ValueError("LLM_API_KEY is required for video generation")
    if not resolved_model:
        raise ValueError("LLM_MODEL is required for video generation")
    
    return SimpleConfigGenerator(
        resolved_api_base,
        resolved_api_key,
        resolved_model,
        debug_prompts=debug_prompts,
    )
