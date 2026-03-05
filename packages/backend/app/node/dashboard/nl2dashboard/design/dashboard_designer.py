"""Dashboard Designer

Responsible for designing Dashboard structure and layout based on information documents.
Integrated with LIDA for high-quality chart generation and DeepEye for quality detection.
"""

import json
import os
import re
import random
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..llm_compat import LLMClient, Message
from app.core.config import settings
from .chart_prompts import (
    HIGHLIGHT_DESIGN_PROMPT,
    HIGHLIGHT_CONFIG_PROMPT,
    DASHBOARD_DESIGN_PROMPT,
    DASHBOARD_INTERACT_CONFIG_PROMPT,
    DASHBOARD_NAME_DESCRIPTION_PROMPT
)


class DashboardDesigner:
    """Dashboard Designer
    
    Designs Dashboard structure based on input information documents.
    Integrates with LIDA for chart generation and DeepEye for quality detection.
    
    Attributes:
        info_doc: Information document dictionary
        design_result: Design result dictionary
        llm_client: LLM client
        llm_model: LLM model name
        output_dir: Output directory for generated files
    
    Example:
        >>> designer = DashboardDesigner(llm_client=llm_client)
        >>> design = designer.design(info_doc, output_dir="./output")
        >>> print(design["blocks"])
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None, model: str | None = None):
        """Initialize the designer
        
        Args:
            llm_client: LLM client (optional, will be retrieved from environment variables if None)
            model: LLM model name
        """
        self.info_doc: Optional[Dict[str, Any]] = None
        self.design_result: Optional[Dict[str, Any]] = None
        self.output_dir: Optional[Path] = None
        
        resolved_model = model or settings.LLM_MODEL

        # Initialize LLM client
        if llm_client is None:
            api_key = os.getenv("DEEPEYE_LLM_API_KEY") or settings.LLM_API_KEY
            base_url = os.getenv("DEEPEYE_LLM_BASE_URL") or settings.LLM_BASE_URL
            resolved_model = os.getenv("DEEPEYE_LLM_MODEL", resolved_model)
            
            if api_key:
                self.llm_client = LLMClient(api_key=api_key, base_url=base_url)
                self.llm_model = resolved_model
            else:
                self.llm_client = None
                self.llm_model = resolved_model
        else:
            self.llm_client = llm_client
            self.llm_model = resolved_model
    
    def design(
        self, 
        info_doc: Dict[str, Any],
        output_dir: Optional[str] = None,
        n_goals: int = 5,
        n_charts_per_goal: int = 2,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Design Dashboard with LIDA integration
        
        Args:
            info_doc: Information document dictionary, containing:
                - question: User question
                - dataset_path: Dataset path
                - output_path: Output path (optional, will use output_dir if provided)
                - data_schema: Data schema information
                - insight_path: Path to insight data (optional)
            output_dir: Output directory for generated files (optional)
            n_goals: Number of visualization goals to generate (default: 5)
            n_charts_per_goal: Number of charts per goal (default: 2)
            callback: Optional callback function for status updates
        
        Returns:
            Design result dictionary, containing:
                - dataSource: Data source configuration
                - blocks: List of blocks (highlight + view + filter)
                - adjacentEdges: Adjacent edges (empty for now)
                - interactionEdges: Interaction edges
                - metadata: Design metadata
                - charts_directory: Directory containing generated charts
        
        Raises:
            ValueError: If LLM client is not configured (only for highlight/interaction generation)
        """
        # LLM client is optional - only needed for highlight and interaction generation
        # Chart generation uses LIDA's own LLM
        if not self.llm_client:
                print("⚠️ No LLM client configured. Highlight and interaction generation will be skipped.")
        
        self.info_doc = info_doc
        
        # Setup output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            base_output = info_doc.get("output_path", "./output")
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            self.output_dir = Path(base_output) / f"dashboard_design_{timestamp}"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Output directory: {self.output_dir}")
        
        # Extract key information
        question = info_doc.get("question", "")
        dataset_path = str(info_doc.get("dataset_path", ""))
        data_schema = info_doc.get("data_schema", {})
        insight_path = info_doc.get("insight_path", None)
        
        # Step 0: Generate dashboard name and description
        print("\n" + "="*60)
        print("Step 0: Generating dashboard name and description")
        print("="*60)
        if callback: callback("Generating dashboard title and description...")
        
        dashboard_name, dashboard_description = self._generate_dashboard_name_description(
            question=question,
            data_schema=data_schema,
            insight_path=insight_path
        )
        
        # Step 1: Generate high-quality charts using LIDA + DeepEye
        print("\n" + "="*60)
        print("Step 1: Generating visualizations")
        print("="*60)
        if callback: callback("Generating visualization...")
        
        charts_dir = self.output_dir / f"visualizations_{time.strftime('%Y%m%d_%H%M%S')}"
        high_quality_charts = self._generate_simple_chart(
            dataset_path=dataset_path,
            output_dir=str(charts_dir),
            n_goals=n_goals,
            n_charts_per_goal=n_charts_per_goal,
            user_question=question
        )
        
        # Convert charts to dashboard blocks format
        # if callback: callback(f"Visualization generation complete. {len(high_quality_charts)} high-quality visualizations obtained. Converting configurations...")
        chart_configs = self._convert_charts_to_configs(high_quality_charts)
        
        # Step 2: Generate highlight blocks
        print("\n" + "="*60)
        print("Step 2: Generating highlight blocks")
        print("="*60)
        if callback: callback("Designing key metrics...")
        
        highlight_blocks = self._generate_simple_highlight(
            insight_path=insight_path,
            original_question=question,
            data_schema=data_schema
        )
        
        # Step 3: Generate dashboard interactions
        print("\n" + "="*60)
        print("Step 3: Generating dashboard interactions")
        print("="*60)
        if callback: callback("Designing dashboard interactions...")
        
        dashboard_interact_config = self._generate_simple_dashboard_interact(
            insight_path=insight_path,
            data_schema=data_schema,
            chart_configs=chart_configs
        )
        
        # Step 4: Merge all configurations
        print("\n" + "="*60)
        print("Step 4: Merging configurations")
        print("="*60)
        if callback: callback("Consolidating all configurations and optimizing layout...")
        
        # Extract view blocks and filter blocks
        view_blocks = [block for block in chart_configs if block["blockType"] == "view"]
        filter_blocks = []
        if dashboard_interact_config and "blocks" in dashboard_interact_config:
            filter_blocks = [block for block in dashboard_interact_config["blocks"] 
                           if block["blockType"] == "filter"]
        
        # Build final design result
        design_result = {
            "dataSource": {
                "type": "csv",
                "path": dataset_path,
                "schema": data_schema
            },
            "blocks": highlight_blocks + view_blocks + filter_blocks,
            "adjacentEdges": [],
            "interactionEdges": dashboard_interact_config.get("interactionEdges", []) 
                               if dashboard_interact_config else [],
            "metadata": {
                "question": question,
                "output_path": str(self.output_dir),
                "charts_directory": charts_dir.name,
                "design_version": "2.0",
                "timestamp": time.strftime('%Y%m%d_%H%M%S'),
                "n_highlight_blocks": len(highlight_blocks),
                "n_view_blocks": len(view_blocks),
                "n_filter_blocks": len(filter_blocks),
                "dashboard_name": dashboard_name,
                "dashboard_description": dashboard_description
            }
        }
        
        # Ensure blockTypes are correct (robustness fix)
        for block in design_result["blocks"]:
            if block.get("blockType") == "chart":
                block["blockType"] = "view"
        
        self.design_result = design_result
        
        # Step 5: Save design result and print summary
        print("\n" + "="*60)
        print("✅ Dashboard design complete")
        print("="*60)
        metadata = design_result.get('metadata', {})
        print(f"  - Highlight blocks: {metadata.get('n_highlight_blocks', 0)}")
        print(f"  - View blocks: {metadata.get('n_view_blocks', 0)}")
        print(f"  - Filter blocks: {metadata.get('n_filter_blocks', 0)}")
        print(f"  - Total blocks: {len(design_result.get('blocks', []))}")
        
        # Save to file
        try:
            self._save_design()
            # print(f"  - Design file saved to: {design_file}")
        except Exception as e:
            print(f"  ⚠️  Failed to save design file: {e}")
        
        print("="*60 + "\n")
        
        return design_result
    
    def _generate_dashboard_name_description(
        self,
        question: str,
        data_schema: Dict[str, Any],
        insight_path: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate dashboard name and description based on user question and dataset
        
        Args:
            question: User question
            data_schema: Data schema
            insight_path: Path to insight data (optional)
            
        Returns:
            tuple: (dashboard_name, dashboard_description)
        """
        try:
            # If no LLM client, use default values
            if not self.llm_client:
                print("Skipping dashboard name/description generation (no LLM client)")
                return "Data Dashboard", "A comprehensive data visualization dashboard"
            
            # Load insight data if available
            insight_data = self._load_insight_data(insight_path)
            data_summary = insight_data.get("data_summary", "")
            
            # Convert data schema to string format
            data_source_schema_str = json.dumps(data_schema, ensure_ascii=False, indent=2)
            
            print("Generating dashboard name and description...")
            
            # Generate name and description
            prompt = DASHBOARD_NAME_DESCRIPTION_PROMPT.format(
                QUESTION=question,
                DATA_SOURCE_SCHEMA=data_source_schema_str,
                DATA_SUMMARY=data_summary
            )
            
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages=messages,
                model=self.llm_model,
                temperature=0.7
            )
            
            # Parse response
            dashboard_name, dashboard_description = self._parse_dashboard_name_description(response.content)
            
            print(f"Generated dashboard name: {dashboard_name}")
            print(f"Generated dashboard description: {dashboard_description}")
            
            return dashboard_name, dashboard_description
            
        except Exception as e:
            print(f"Error generating dashboard name/description: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return default values on error
            return "Data Dashboard", "A comprehensive data visualization dashboard"
    
    def _parse_dashboard_name_description(self, content: str) -> Tuple[str, str]:
        """
        Parse dashboard name and description from LLM response
        
        Args:
            content: LLM response content
            
        Returns:
            tuple: (dashboard_name, dashboard_description)
        """
        try:
            dashboard_name = "Data Dashboard"
            dashboard_description = "A comprehensive data visualization dashboard"
            
            # Try to extract DASHBOARD_NAME and DASHBOARD_DESCRIPTION
            name_match = re.search(r'DASHBOARD_NAME:\s*(.+)', content, re.IGNORECASE | re.MULTILINE)
            desc_match = re.search(r'DASHBOARD_DESCRIPTION:\s*(.+)', content, re.IGNORECASE | re.MULTILINE)
            
            if name_match:
                dashboard_name = name_match.group(1).strip()
                # Remove any trailing punctuation or extra text
                dashboard_name = re.sub(r'[^\w\s-]+$', '', dashboard_name).strip()
            
            if desc_match:
                dashboard_description = desc_match.group(1).strip()
                # Remove any trailing punctuation or extra text
                dashboard_description = re.sub(r'[^\w\s.,!?-]+$', '', dashboard_description).strip()
            
            return dashboard_name, dashboard_description
            
        except Exception as e:
            print(f"Error parsing dashboard name/description: {str(e)}")
            return "Data Dashboard", "A comprehensive data visualization dashboard"
    
    def _generate_simple_chart(
        self, 
        dataset_path: str,
        output_dir: str,
        n_goals: int = 5,
        n_charts_per_goal: int = 2,
        user_question: str = None
    ) -> List[Dict]:
        """
        Generate charts using LIDA and perform quality detection with DeepEye
        
        Args:
            dataset_path: Path to dataset
            output_dir: Output directory
            n_goals: Number of visualization goals
            n_charts_per_goal: Number of charts per goal
            user_question: User question for focused generation
        
        Returns:
            List[Dict]: List of high-quality chart configurations
        """
        try:
            import sys
            from pathlib import Path
            
            # Import LIDA Lite (Replacing external LIDA)
            try:
                from .lida_lite import Manager, TextGenerationConfig, llm
            except ImportError as e:
                print(f"⚠️  LIDA Lite import failed: {e}")
                print("Make sure lida_lite.py exists and all dependencies (pandas, etc.) are installed.")
                return []
            
            # Import DeepEye detector (optional)
            try:
                # Try to import the visualization detector
                detector_dir = Path(__file__).parent / "error_detection"
                # print(f"Detector directory: {detector_dir}")
                if detector_dir.exists():
                    sys.path.insert(0, str(detector_dir))
                    from detect_visualization_quality import VisualizationDetector
                    has_detector = True
                else:
                    has_detector = False
                    print("⚠️  DeepEye detector not found, skipping quality detection")
            except ImportError:
                has_detector = False
                print("⚠️  DeepEye detector not available, skipping quality detection")
            
            # print("="*60)
            # print("Starting chart generation and quality detection")
            # print("="*60)
            
            # 1. Generate charts with LIDA
            # Get API config from LLM client or environment
            api_key = None
            base_url = None
            
            if self.llm_client:
                api_key = getattr(self.llm_client, 'api_key', None)
                base_url = getattr(self.llm_client, 'base_url', None)
            
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            if not base_url:
                base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPEYE_LLM_BASE_URL")
            
            if not api_key:
                print("⚠️  No API key available for LIDA. Please configure LLM client or set OPENAI_API_KEY environment variable.")
                return []
            
            # Initialize LIDA with proper OpenAI configuration
            # Set environment variables (try multiple variable names for compatibility)
            os.environ["OPENAI_API_KEY"] = api_key
            if base_url:
                # print(f"[INFO] Using API base URL: {base_url}")
                # Set multiple environment variable names for better compatibility
                os.environ["OPENAI_BASE_URL"] = base_url  # New OpenAI SDK
                os.environ["OPENAI_API_BASE"] = base_url  # Old OpenAI SDK
            
            lida = Manager(text_gen=llm("openai"), llm_client=self.llm_client)
            
            textgen_config = TextGenerationConfig(
                n=1,
                temperature=0,
                model=self.llm_model,
                use_cache=False
            )
            
            # Create output directories first
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            charts_dir = output_path / "echart_code"
            charts_dir.mkdir(exist_ok=True)
            
            # Generate data summary
            print(f"[INFO] Generating data summary...")
            data_summary = lida.summarize(dataset_path, summary_method="default")
            
            # Save data summary
            summary_file = output_path / "data_summary.json"
            try:
                # Convert summary to dict if it's an object
                if hasattr(data_summary, '__dict__'):
                    summary_dict = data_summary.__dict__
                elif isinstance(data_summary, dict):
                    summary_dict = data_summary
                else:
                    # Try to convert to string representation
                    summary_dict = {"summary": str(data_summary)}
                
                with open(summary_file, "w", encoding="utf-8") as f:
                    json.dump(summary_dict, f, ensure_ascii=False, indent=2)
                print(f"✓ Data summary saved: {summary_file}")
            except Exception as e:
                print(f"⚠ Failed to save data summary: {e}")
            
            # Generate visualization goals (generate 10, will filter to top 5 later)
            print(f"🎯 Generating 10 visualization goals...")
            if user_question:
                # print(f"  Focus Area: {user_question}")
                goals = lida.goals_with_focus_area(
                    data_summary, 
                    n=2,  # Generate 10 goals
                    textgen_config=textgen_config, 
                    focus_area=user_question
                )
            else:
                goals = lida.goals(data_summary, n=10, textgen_config=textgen_config)  # Generate 10 goals
            print(f"✓ Successfully generated {len(goals)} goals")
            
            # Save goals
            goals_file = output_path / "visualization_goals.json"
            try:
                goals_list = []
                for goal in goals:
                    if hasattr(goal, '__dict__'):
                        goal_dict = goal.__dict__
                    elif isinstance(goal, dict):
                        goal_dict = goal
                    else:
                        # Convert to string representation
                        goal_dict = {
                            "question": getattr(goal, 'question', str(goal)),
                            "visualization": getattr(goal, 'visualization', None),
                            "rationale": getattr(goal, 'rationale', None)
                        }
                    goals_list.append(goal_dict)
                
                with open(goals_file, "w", encoding="utf-8") as f:
                    json.dump(goals_list, f, ensure_ascii=False, indent=2)
                print(f"✓ Visualization goals saved: {goals_file}")
            except Exception as e:
                print(f"⚠ Failed to save visualization goals: {e}")
            
            # Generate charts
            print(f"📈 Generating ECharts visualizations...")
            all_charts = []
            chart_files = []
            library = "echarts"
            
            for i, goal in enumerate(goals):
                try:
                    print(f"  Goal {i+1}/{len(goals)}: {getattr(goal, 'question', str(goal))}")
                    
                    # Generate charts for each goal
                    goal_charts = lida.visualize_wo_excecute(
                        summary=data_summary,
                        goal=goal,
                        textgen_config=textgen_config,
                        library=library
                    )
                    
                    # Limit charts per goal
                    goal_charts = goal_charts[:n_charts_per_goal]
                    
                    for j, chart in enumerate(goal_charts):
                        try:
                            chart_id = f"intent_{i}_goal_0_chart{j}"
                            code_file = charts_dir / f"{chart_id}_echarts.py"
                            
                            # Check if code exists
                            if not chart.code:
                                print(f"    ⚠ {chart_id}: Empty code, skipping")
                                continue
                            
                            # Save code file (remove ``` wrapper and final chart = plot(data))
                            code_content = chart.code
                            if code_content:
                                # Remove leading ```python or ```
                                code_content = re.sub(r'^```\w*\n?', '', code_content)
                                # Remove trailing ```
                                code_content = re.sub(r'\n?```$', '', code_content)
                                # Remove final "chart = plot(data)" line
                                code_content = re.sub(r'\n\s*chart\s*=\s*plot\s*\(\s*data\s*\).*$', '', code_content)
                            
                            with open(code_file, "w", encoding="utf-8") as f:
                                f.write(code_content)
                            
                            if not code_file.exists():
                                print(f"    ✗ Failed to save file: {code_file}")
                                continue
                            
                            print(f"    ✓ Code saved: {code_file.name}")
                            
                            # Save image if raster data exists
                            try:
                                raster_data = getattr(chart, "raster", None)
                                if raster_data:
                                    png_file = charts_dir / f"{chart_id}_screenshot.png"
                                    import base64 as b64
                                    with open(png_file, "wb") as f:
                                        f.write(b64.b64decode(raster_data))
                                    print(f"    ✓ Image saved: {png_file.name}")
                            except Exception as img_err:
                                print(f"    ⚠ Image save failed (not critical): {img_err}")
                            
                            # Add to list
                            all_charts.append({
                                'chart_id': chart_id,
                                'goal_index': i,
                                'chart_index': j,
                                'goal_question': getattr(goal, 'question', str(goal)),
                                'code_file': str(code_file),
                                'code': chart.code,
                                'chart_object': chart
                            })
                            chart_files.append(str(code_file))
                            
                        except Exception as save_err:
                            print(f"    ✗ Failed to save chart {j}: {save_err}")
                            continue
                    
                    print(f"    ✓ Goal {i+1} complete, saved {len([c for c in all_charts if c['goal_index']==i])} charts")
                    
                except Exception as e:
                    print(f"    ✗ Goal {i+1} generation failed: {str(e)}")
                    continue
            
            print(f"✓ Total generated: {len(all_charts)} charts")
            
            # 2. Quality detection with DeepEye when available
            if has_detector and all_charts:
                print(f"\n🔍 Starting quality detection...")
                
                try:
                    # Create detector
                    detector = VisualizationDetector(dataset_path)
                    detector.load_data()
                    detector.initialize_deepeye()
                    
                    # Detect all charts
                    detection_results = []
                    for chart_info in all_charts:
                        try:
                            result = detector.detect_visualization(chart_info['code_file'])
                            result['chart_id'] = chart_info['chart_id']
                            result['goal_question'] = chart_info['goal_question']
                            detection_results.append(result)
                            
                            score = result.get('score', -999)
                            quality = result.get('quality', 'Unknown')
                            score_str = f"{score:.4f}" if isinstance(score, (int, float)) and score is not None else 'N/A'
                            print(f"  {chart_info['chart_id']}: Score={score_str}, Quality={quality}")
                            
                        except Exception as e:
                            print(f"  ✗ Detection failed for {chart_info['chart_id']}: {str(e)}")
                            detection_results.append({
                                'chart_id': chart_info['chart_id'],
                                'goal_question': chart_info['goal_question'],
                                'score': None,
                                'quality': 'Detection Failed',
                                'error': str(e)
                            })
                    
                    # 3. Filter high-quality charts
                    print("\n[INFO] Filtering high-quality charts...")
                    high_quality_charts = []
                    
                    for result in detection_results:
                        chart_id = result.get('chart_id')
                        chart_info = next((c for c in all_charts if c['chart_id'] == chart_id), None)
                        if not chart_info:
                            print(f"  ⚠ Chart info not found for {chart_id}")
                            continue
                        
                        score = result.get('score')
                        chart_type = result.get('chart_type', '').lower()
                        
                        # Filter out Boxplot-type charts
                        if chart_type == 'boxplot' or 'boxplot' in chart_type:
                            print(f"  ✗ {chart_info['chart_id']}: Filtered (Boxplot type not supported)")
                            continue
                        
                        # Keep charts with score >= 0 or passed rule validation
                        if score is not None and score >= 0:
                            high_quality_charts.append({
                                'chart_id': chart_info['chart_id'],
                                'goal_question': chart_info['goal_question'],
                                'code_file': chart_info['code_file'],
                                'code': chart_info['code'],
                                'score': score,
                                'quality': result.get('quality', 'Unknown'),
                                'M_value': result.get('M_value'),
                                'Q_value': result.get('Q_value'),
                                'chart_type': result.get('chart_type'),
                                'x_field': result.get('x_field'),
                                'y_field': result.get('y_field'),
                                'view_info': result.get('view_info', {})
                            })
                            print(f"  ✓ {chart_info['chart_id']}: Score={score:.4f}, Quality={result.get('quality')}")
                        elif result.get('rule_valid') and not result.get('violations'):
                            high_quality_charts.append({
                                'chart_id': chart_info['chart_id'],
                                'goal_question': chart_info['goal_question'],
                                'code_file': chart_info['code_file'],
                                'code': chart_info['code'],
                                'score': 0,
                                'quality': 'Passed Rule Validation',
                                'chart_type': result.get('chart_type'),
                                'x_field': result.get('x_field'),
                                'y_field': result.get('y_field')
                            })
                            print(f"  ✓ {chart_info['chart_id']}: Passed rule validation (no score)")
                        else:
                            print(f"  ✗ {chart_info['chart_id']}: Filtered (score={score if score is not None else 'N/A'}, quality={result.get('quality')})")
                    
                    # Sort by score
                    high_quality_charts.sort(key=lambda x: x.get('score', 0), reverse=True)
                    
                    # 3.5. Filter goals by score and data column diversity
                    print("\n[INFO] Filtering goals by score and data column diversity (keep top 5 with score >= 0)...")
                    goal_scores = {}  # goal_index -> best_score
                    goal_fields = {}  # goal_index -> set of fields used
                    
                    # Calculate best score and collect fields for each goal
                    for chart in high_quality_charts:
                        # Extract goal_index from chart_id (format: intent_{goal_index}_goal_0_chart{chart_index})
                        try:
                            goal_index = int(chart['chart_id'].split('_')[1])
                            score = chart.get('score', -999)
                            
                            # Keep the best (highest) score for each goal
                            if goal_index not in goal_scores or score > goal_scores[goal_index]:
                                goal_scores[goal_index] = score
                            
                            # Collect fields used by this goal
                            if goal_index not in goal_fields:
                                goal_fields[goal_index] = set()
                            
                            # Add x_field and y_field if they exist
                            x_field = chart.get('x_field')
                            y_field = chart.get('y_field')
                            if x_field:
                                goal_fields[goal_index].add(x_field)
                            if y_field:
                                goal_fields[goal_index].add(y_field)
                            
                            # Also check view_info for additional fields
                            view_info = chart.get('view_info', {})
                            if isinstance(view_info, dict):
                                for field in view_info.get('fields', []):
                                    if field:
                                        goal_fields[goal_index].add(field)
                        except (ValueError, IndexError):
                            continue
                    
                    # Filter goals: only keep those with score >= 0
                    candidate_goals = [
                        goal_idx for goal_idx, score in goal_scores.items() 
                        if score is not None and score >= 0
                    ]
                    
                    # Select goals considering both score and field diversity
                    # Use greedy algorithm: prioritize goals that bring new fields
                    # Randomly select 4-6 goals
                    max_goals = random.randint(4, 6)
                    selected_goals = []
                    selected_fields = set()
                    remaining_goals = sorted(candidate_goals, key=lambda idx: goal_scores[idx], reverse=True)
                    
                    while len(selected_goals) < max_goals and remaining_goals:
                        best_goal = None
                        best_score = -999
                        best_new_fields_count = 0
                        
                        # Find the goal that maximizes (score + diversity bonus)
                        for goal_idx in remaining_goals:
                            score = goal_scores[goal_idx]
                            goal_fields_set = goal_fields.get(goal_idx, set())
                            new_fields = goal_fields_set - selected_fields
                            new_fields_count = len(new_fields)
                            
                            # Calculate selection priority: score + diversity bonus
                            # Diversity bonus: 0.1 * number of new fields
                            priority = score + (0.1 * new_fields_count)
                            
                            # Prefer goals with higher priority, or if priority is close, prefer more new fields
                            if (priority > best_score + 0.05) or \
                               (abs(priority - best_score) < 0.05 and new_fields_count > best_new_fields_count):
                                best_goal = goal_idx
                                best_score = priority
                                best_new_fields_count = new_fields_count
                        
                        if best_goal is not None:
                            selected_goals.append(best_goal)
                            selected_fields.update(goal_fields.get(best_goal, set()))
                            remaining_goals.remove(best_goal)
                        else:
                            break
                    
                    valid_goal_indices = selected_goals[:max_goals]  # Keep top N (randomly 4-6)
                    
                    print(f"  Found {len(goal_scores)} goals with scores")
                    print(f"  {len(candidate_goals)} goals have score >= 0")
                    print(f"  Selected {len(valid_goal_indices)} goals (randomly {max_goals}, considering field diversity): {valid_goal_indices}")
                    for idx in valid_goal_indices:
                        fields = goal_fields.get(idx, set())
                        print(f"    Goal {idx}: score={goal_scores[idx]:.4f}, fields={sorted(fields)}")
                    
                    # Filter charts to only include those from selected goals
                    filtered_charts = [
                        chart for chart in high_quality_charts
                        if int(chart['chart_id'].split('_')[1]) in valid_goal_indices
                    ]
                    
                    # Update high_quality_charts to only include filtered ones
                    high_quality_charts = filtered_charts
                    print(f"  ✓ Filtered to {len(high_quality_charts)} charts from {len(valid_goal_indices)} goals")
                    
                    # 4. Write report
                    report_file = output_path / "chart_quality_report.json"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'total_charts': len(all_charts),
                            'high_quality_charts': len(high_quality_charts),
                            'filtered_charts': len(all_charts) - len(high_quality_charts),
                            'charts': high_quality_charts,
                            'all_detection_results': detection_results
                        }, f, ensure_ascii=False, indent=2)
                    
                    # print(f"\n{'='*60}")
                    print(f"✅ Chart generation and detection complete")
                    # print(f"{'='*60}")
                    print(f"  Total generated: {len(all_charts)} charts")
                    print(f"  High quality: {len(high_quality_charts)} charts")
                    print(f"  Filtered: {len(all_charts) - len(high_quality_charts)} charts")
                    # print(f"  Report saved: {report_file}")
                    # print(f"{'='*60}\n")
                    
                    return high_quality_charts
                    
                except Exception as e:
                    print(f"Quality detection failed: {str(e)}")
                    print("Returning all generated charts without quality filtering")
                    return [{
                        'chart_id': c['chart_id'],
                        'goal_question': c['goal_question'],
                        'code_file': c['code_file'],
                        'code': c['code'],
                        'score': None,
                        'quality': 'Not Detected',
                        'chart_type': 'unknown'
                    } for c in all_charts]
            else:
                # No detector available, return all charts
                print("\n⚠️  Quality detection skipped, returning all charts")
                return [{
                    'chart_id': c['chart_id'],
                    'goal_question': c['goal_question'],
                    'code_file': c['code_file'],
                    'code': c['code'],
                    'score': None,
                    'quality': 'Not Detected',
                    'chart_type': 'unknown'
                } for c in all_charts]
        
        except Exception as e:
            print(f"Error generating charts: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def _convert_charts_to_configs(self, high_quality_charts: List[Dict]) -> List[Dict]:
        """
        Convert high-quality charts to dashboard blocks format
        
        Args:
            high_quality_charts: List of high-quality charts
        
        Returns:
            List[Dict]: Dashboard blocks configuration list
        """
        chart_configs = []
        
        for chart in high_quality_charts:
            try:
                # Extract file names
                code_file = chart.get('code_file', '')
                python_code_name = os.path.basename(code_file) if code_file else ''
                html_code_name = python_code_name.replace('.py', '.html') if python_code_name else ''
                
                # Get score and quality with safe defaults
                score = chart.get('score')
                score = score if score is not None else 0
                quality = chart.get('quality', 'Unknown')
                
                # Convert to view block format
                view_block = {
                    "id": chart['chart_id'],
                    "blockType": "view",
                    "blockContent": {
                        "title": chart.get('goal_question', 'Visualization'),
                        "caption": f"Quality score: {score:.2f} ({quality})",
                        "xDataField": chart.get('x_field', ''),
                        "layers": [
                            {
                                "id": f"{chart['chart_id']}_layer1",
                                "chartType": chart.get('chart_type', 'bar'),
                                "xField": chart.get('x_field', ''),
                                "yField": chart.get('y_field', ''),
                                "yAgg": chart.get('y_agg', 'sum'),
                                "color": "#5470c6",
                                "size": 1,
                                "style": {},
                                "echarts_code": chart.get('code', ''),
                                "code_file": chart.get('code_file', '')
                            }
                        ],
                        "dataProcessing": [],
                        "quality_metrics": {
                            "score": score,
                            "M_value": chart.get('M_value') or 0,
                            "Q_value": chart.get('Q_value') or 0,
                            "quality_level": quality
                        },
                        "python_code_name": python_code_name,
                        "html_code_name": html_code_name
                    }
                }
                
                chart_configs.append(view_block)
                
            except Exception as e:
                print(f"Failed to convert chart {chart.get('chart_id', 'unknown')}: {str(e)}")
                continue
        
        # print(f"Successfully converted {len(chart_configs)} charts to view blocks")
        return chart_configs
    
    def _generate_simple_highlight(
        self, 
        insight_path: Optional[str], 
        original_question: str, 
        data_schema: Dict[str, Any]
    ) -> List[Dict]:
        """
        Generate highlight blocks based on insights
        
        Args:
            insight_path: Path to insight data
            original_question: Original user question
            data_schema: Data schema
            
        Returns:
            List[Dict]: List of highlight block configurations
        """
        try:
            # Skip highlight generation when no LLM client
            if not self.llm_client:
                print("Skipping highlight generation (no LLM client)")
                return []
            
            # Load insight data
            insight_data = self._load_insight_data(insight_path)
            
            # Convert data schema to string
            data_source_schema_str = json.dumps(data_schema, ensure_ascii=False)
            
            print("Generating highlight blocks...")
            
            # Debug: input before highlight generation
            print("Highlight generation context:")
            print(f"  Question: {original_question}")
            print(f"  Intents count: {len(insight_data.get('intents', []))}")
            if insight_path:
                print(f"  Insight path: {insight_path}")
            else:
                print("  ⚠️ No insight path provided, using default data (may lead to empty highlights)")

            # Step 1: Generate highlight designs
            prompt = HIGHLIGHT_DESIGN_PROMPT.format(
                QUESTION=original_question,
                DATA_SOURCE_SCHEMA=data_source_schema_str,
                DATA_SUMMARY=insight_data.get("data_summary", ""),
                DATA_ANALYSIS_RESULT=insight_data.get("data_analysis", ""),
                INSIGHTS=json.dumps(insight_data.get("intents", []), ensure_ascii=False, indent=2)
            )
            
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages=messages,
                model=self.llm_model,
                temperature=0.7
            )
            highlight_designs = self._parse_highlight_designs(response.content)
            
            if not highlight_designs:
                print("No highlight designs generated")
                return []
            
            # Step 2: Generate highlight configurations
            prompt = HIGHLIGHT_CONFIG_PROMPT.format(
                HIGHLIGHT_DESIGN=json.dumps(highlight_designs, ensure_ascii=False, indent=2),
                DATA_SOURCE_SCHEMA=data_source_schema_str
            )
            
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages=messages,
                model=self.llm_model,
                temperature=0.7
            )
            highlight_configs = self._parse_chart_configs(response.content)
            
            # Cap at 6 highlight blocks
            if len(highlight_configs) > 6:
                highlight_configs = highlight_configs[:4]
                print("Limited to 4 highlight blocks (more than 6 were generated)")
            
            print(f"Generated {len(highlight_configs)} highlight blocks")
            
            # Debug: highlight block details
            if highlight_configs:
                print("Highlight block details:")
                for i, hb in enumerate(highlight_configs):
                    content = hb.get("blockContent", {})
                    print(f"  {i+1}. Title: {content.get('title')}, Value: {content.get('value')}")
            else:
                print("⚠️ Warning: No highlight blocks were successfully generated.")
            
            return highlight_configs
            
        except Exception as e:
            print(f"Error generating highlights: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _generate_simple_dashboard_interact(
        self, 
        insight_path: Optional[str], 
        data_schema: Dict[str, Any], 
        chart_configs: List[Dict] = None
    ) -> Dict:
        """
        Generate dashboard interaction configuration
        
        Args:
            insight_path: Path to insight data
            data_schema: Data schema
            chart_configs: Chart configurations
            
        Returns:
            Dict: Dashboard interaction configuration with blocks and interactionEdges
        """
        try:
            # Skip interaction generation when no LLM client
            if not self.llm_client:
                print("Skipping interaction generation (no LLM client)")
                return {"blocks": [], "interactionEdges": []}
            
            # Load insight data
            insight_data = self._load_insight_data(insight_path)
            
            # Convert data schema to string
            data_source_schema_str = json.dumps(data_schema, ensure_ascii=False)
            
            print("Generating dashboard interactions...")
            
            # Debug: input before filter generation
            print("Interaction generation context:")
            print(f"  Chart configs count: {len(chart_configs or [])}")
            print(f"  Data schema fields: {list(data_schema.keys()) if isinstance(data_schema, dict) else 'Unknown'}")

            # Prepare chart designs summary
            chart_designs = []
            for i, chart_config in enumerate(chart_configs or []):
                chart_designs.append({
                    "chart_id": chart_config.get("id", f"chart_{i}"),
                    "related_intents": [1],
                    "chart_purpose": chart_config.get("blockContent", {}).get("title", ""),
                    "chart_description": chart_config.get("blockContent", {}).get("caption", ""),
                    "used_fields": []
                })
            
            # Step 1: Generate dashboard design (filters and interactions)
            print("  → Step 1/2: Generating dashboard design (filters & interactions)...")
            prompt = DASHBOARD_DESIGN_PROMPT.format(
                INSIGHTS=json.dumps(insight_data.get("intents", []), ensure_ascii=False, indent=2),
                CHART_DESIGNS=json.dumps(chart_designs, ensure_ascii=False, indent=2),
                DATA_SOURCE_SCHEMA=data_source_schema_str
            )
            
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages=messages,
                model=self.llm_model,
                temperature=0.7
            )
            print("  ✓ Step 1/2 completed")
            print("  → Parsing dashboard design from LLM response...")
            dashboard_design = self._parse_dashboard_design(response.content)
            
            # Debug: filter design phase output
            if dashboard_design:
                print("  → Dashboard design parsed:")
                print(f"    - Filters planned: {len(dashboard_design.get('filters', []))}")
                print(f"    - Interactions planned: {len(dashboard_design.get('interactions', []))}")
            else:
                print("  ⚠️ Failed to parse dashboard design from LLM response.")
            
            # Step 2: Generate dashboard configuration
            print("  → Step 2/2: Generating dashboard configuration...")
            
            prompt = DASHBOARD_INTERACT_CONFIG_PROMPT.format(
                DASHBOARD_DESIGN=json.dumps(dashboard_design, ensure_ascii=False, indent=2),
                DATA_SOURCE_SCHEMA=data_source_schema_str,
                CHART_CONFIGS=json.dumps(chart_configs or [], ensure_ascii=False, indent=2)
            )
            
            messages = [Message(role="user", content=prompt)]
            response = self.llm_client.generate(
                messages=messages,
                model=self.llm_model,
                temperature=0.7
            )
            print("  ✓ Step 2/2 completed")
            dashboard_interact_config = self._parse_dashboard_config(response.content)
            
            # Debug: filter block details
            filter_blocks = [b for b in dashboard_interact_config.get('blocks', []) if b.get('blockType') == 'filter']
            print(f"Generated {len(filter_blocks)} filter blocks")
            if filter_blocks:
                for i, fb in enumerate(filter_blocks):
                    content = fb.get("blockContent", {})
                    print(f"  Filter {i+1}: Field='{content.get('field')}', Type='{content.get('controlType')}', Label='{content.get('title')}'")
            else:
                print("⚠️ Warning: No filter blocks generated.")
            
            print(f"Generated {len(dashboard_interact_config.get('interactionEdges', []))} interaction edges")

            return dashboard_interact_config
            
        except Exception as e:
            print(f"Error generating dashboard interactions: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"blocks": [], "interactionEdges": []}
    
    def _load_insight_data(self, insight_path: Optional[str]) -> Dict:
        """Load insight data from file"""
        if not insight_path or not Path(insight_path).exists():
            # print(f"⚠️  Invalid insight path: {insight_path}, using default data")
            return {
                "data_summary": "No data summary available",
                "data_analysis": "No data analysis available",
                "key_column": {
                    "key_column_name": "default",
                    "description": "No topic available",
                    "rationale": "No rationale available"
                },
                "title": {
                    "title": "Default Dashboard",
                    "description": "No title description available"
                },
                "intents": [
                    {
                        "intent_id": "default",
                        "intent": "No intent available",
                        "focus": "No focus available"
                    }
                ]
            }
        else:
            with open(insight_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _parse_highlight_designs(self, highlight_designs_rsp: str) -> List[Dict]:
        """Parse highlight designs from LLM response"""
        highlight_designs = []
        highlight_pattern = r"""
            \s*(?:[\s*-]*)?HIGHLIGHT_ID(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?HIGHLIGHT_TITLE(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?HIGHLIGHT_PURPOSE(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?HIGHLIGHT_TYPE(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?HIGHLIGHT_EXPRESSION(?:[:：\s*-]*)(.*?)
            (?=\n|\Z)
        """
        highlight_matches = list(re.finditer(highlight_pattern, highlight_designs_rsp, 
                                             re.DOTALL | re.VERBOSE | re.IGNORECASE))

        for match in highlight_matches:
            try:
                groups = [g.strip() if g else "" for g in match.groups()]
                highlight_design = {
                    "highlight_id": groups[0],
                    "highlight_title": groups[1],
                    "highlight_purpose": groups[2],
                    "highlight_type": groups[3],
                    "highlight_expression": groups[4]
                }
                highlight_designs.append(highlight_design)
            except Exception as e:
                print(f"Error parsing highlight design: {e}")
                continue
        
        return highlight_designs
    
    def _parse_chart_configs(self, chart_configs_rsp: str) -> List[Dict]:
        """Parse chart configurations from LLM response"""
        try:
            # Extract JSON content
            json_pattern = r"```json\s*(.*?)\s*```"
            match = re.search(json_pattern, chart_configs_rsp, re.DOTALL)
            
            if not match:
                print("No JSON configuration found in response")
                return []
            
            json_str = match.group(1).strip()
            
            try:
                config_list = json.loads(json_str)
                
                if not isinstance(config_list, list):
                    print(f"Expected list, got {type(config_list)}")
                    return []
                
                return config_list
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return []
                
        except Exception as e:
            print(f"Error parsing chart configs: {e}")
            return []
    
    def _parse_dashboard_config(self, response: str) -> dict:
        """Parse dashboard configuration from LLM response"""
        try:
            # print(f"     [DEBUG] Config response length: {len(response)} characters")
            # print(f"     [DEBUG] Config response preview (first 500 chars): {response[:500]}")
            
            response = response.strip()
            
            # Try to find JSON code block
            # print("     [DEBUG] Searching for JSON code blocks...")
            json_pattern = r"```(?:json)?\s*(.*?)\s*```"
            matches = list(re.finditer(json_pattern, response, re.DOTALL))
            # print(f"     [DEBUG] Found {len(matches)} JSON code block(s)")
            
            if not matches:
                # Try to parse entire response
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    # Try to find JSON-like content
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        return json.loads(json_str)
                    raise ValueError("No valid JSON found in response")
            
            # Use the last code block
            json_str = matches[-1].group(1).strip()
            # print(f"     [DEBUG] Extracted JSON string length: {len(json_str)} characters")
            
            try:
                config = json.loads(json_str)
                # print(f"     [DEBUG] Successfully parsed JSON: {len(config.get('blocks', []))} blocks, {len(config.get('interactionEdges', []))} edges")
                return config
            except json.JSONDecodeError:
                # print(f"     [DEBUG] JSON decode error, attempting to clean: {str(e)}")
                # Clean common issues
                json_str = re.sub(r'\s*#.*$', '', json_str, flags=re.MULTILINE)
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                json_str = json_str.replace('True', 'true').replace('False', 'false').replace('None', 'null')
                
                try:
                    config = json.loads(json_str)
                    # print(f"     [DEBUG] Successfully parsed JSON after cleaning")
                    return config
                except json.JSONDecodeError as e2:
                    print(f"     [ERROR] Failed to parse JSON even after cleaning: {str(e2)}")
                    raise
                
        except Exception as e:
            print(f"     [ERROR] Failed to parse dashboard config: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "blocks": [],
                "interactionEdges": []
            }
    
    def _parse_dashboard_design(self, dashboard_design_rsp: str) -> Dict:
        """Parse dashboard design from LLM response (filters and interactions)"""
        # print(f"     [DEBUG] Response length: {len(dashboard_design_rsp)} characters")
        # print(f"     [DEBUG] Response preview (first 500 chars): {dashboard_design_rsp[:500]}")
        
        dashboard_design = {
            "blocks": [],
            "interactionEdges": []
        }
        
        # Extract filter design (divide and conquer)
        # 1. Preprocess: normalize line endings
        text = dashboard_design_rsp.replace('\r\n', '\n')
        
        # 2. Step 1: split blocks by "FILTER_ID" to locate each filter
        # Use split to avoid regex backtracking; support FILTER_ID:, **FILTER_ID**:, 1. **FILTER_ID**:
        raw_blocks = re.split(r'(?=(?:^|\n)\s*(?:\d+\.\s*)?(?:\*\*)?\s*FILTER_ID\s*(?:\*\*)?\s*[:：])', text, flags=re.MULTILINE | re.IGNORECASE)
        
        for block in raw_blocks:
            if not re.search(r'FILTER_ID\s*[:：]', block, re.IGNORECASE):
                continue
            
            # 3. Step 2: extract fields inside each block independently
            def extract_field(pattern, content):
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                return match.group(1).strip() if match else None
            
            # Simple regex per field (order-independent); support **FIELD**: value, - **FIELD**: value
            filter_item = {
                "filter_id": extract_field(r"(?:\*\*)?\s*FILTER_ID\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "purpose": extract_field(r"(?:\*\*)?\s*FILTER_PURPOSE\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "description": extract_field(r"(?:\*\*)?\s*FILTER_DESCRIPTION\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "label": extract_field(r"(?:\*\*)?\s*LABEL\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "control_type": extract_field(r"(?:\*\*)?\s*CONTROL_TYPE\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "field": extract_field(r"(?:\*\*)?\s*FIELD\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "operator": extract_field(r"(?:\*\*)?\s*OPERATOR\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
                "range_config": extract_field(r"(?:\*\*)?\s*RANGE_CONFIG\s*(?:\*\*)?\s*[:：\s*-]+(.*?)(?=\n|FILTER_|INTERACTION_|$)", block),
            }
            
            # Only add when ID was extracted to avoid empty blocks
            if filter_item["filter_id"]:
                # Strip leftover Markdown and whitespace
                for k, v in filter_item.items():
                    if v:
                        filter_item[k] = v.strip('`"\'* ').strip()
                
                # Build filter_block structure
                filter_block = {
                    "id": filter_item["filter_id"],
                    "blockType": "filter",
                    "blockContent": {
                        "controlType": (filter_item["control_type"] or "select").lower(),
                        "field": filter_item["field"] or "",
                        "label": filter_item["label"] or filter_item["field"] or filter_item["filter_id"],
                        "operator": (filter_item["operator"] or "equals").lower()
                    }
                }
                
                # Only add when field is present
                if filter_block["blockContent"]["field"]:
                    dashboard_design["blocks"].append(filter_block)
                    # print(f"     [DEBUG] Found Filter: {filter_item['filter_id']} (field={filter_block['blockContent']['field']})")
                else:
                    # print(f"     [WARN] Filter {filter_item['filter_id']} missing field, skipping")
                    pass
        
        # print(f"     [DEBUG] Total filters extracted: {len(dashboard_design['blocks'])}")
        
        # Extract Interaction Design
        # print("     [DEBUG] Extracting interaction designs...")
        interaction_pattern = r"""
            \s*(?:[\s*-]*)?INTERACTION_ID(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?INTERACTION_PURPOSE(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?INTERACTION_DESCRIPTION(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?SOURCE_VIEW(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?SOURCE_LAYER(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?SOURCE_FIELD(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?TARGET_VIEW(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?TARGET_LAYER(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?TARGET_FIELD(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?TYPE(?:[:：\s*-]*)(.*?)
            \s*(?:[\s*-]*)?DETAIL(?:[:：\s*-]*)(.*?)
            (?=\n|\Z)
        """
        interaction_matches = list(re.finditer(interaction_pattern, dashboard_design_rsp, re.DOTALL | re.VERBOSE))
        # print(f"     [DEBUG] Found {len(interaction_matches)} interaction pattern matches")
        
        for i, match in enumerate(interaction_matches):
            try:
                source_block = match.group(4).strip()
                interaction_type = match.group(10).strip()
                # print(f"     [DEBUG] Interaction {i+1}: source={source_block}, type={interaction_type}")
                
                interaction_edge = {
                    "source": {
                        "block": source_block,
                        "layer": match.group(5).strip(),
                        "field": match.group(6).strip()
                    },
                    "target": {
                        "block": match.group(7).strip(),
                        "layer": match.group(8).strip(),
                        "field": match.group(9).strip()
                    },
                    "interaction": {
                        "type": interaction_type,
                        "detail": match.group(11).strip()
                    }
                }
                dashboard_design["interactionEdges"].append(interaction_edge)
            except Exception as e:
                print(f"     [WARN] Failed to parse interaction {i+1}: {str(e)}")
                continue
        
        # print(f"     [DEBUG] Parsing summary: {len(dashboard_design['blocks'])} filters, {len(dashboard_design['interactionEdges'])} interactions")
        return dashboard_design
    
    def _save_design(self, output_path: Optional[str] = None) -> str:
        """Save design result to file
        
        Args:
            output_path: Output path (optional, will use self.output_dir if not provided)
        
        Returns:
            Path to saved file
        """
        if not self.design_result:
            raise ValueError("Design result is empty, please call design() method first")
        
        if output_path:
            output_dir = Path(output_path)
        elif self.output_dir:
            output_dir = self.output_dir
        else:
            output_dir = Path("./output")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        design_file = output_dir / "dashboard_config.json"
        
        with open(design_file, "w", encoding="utf-8") as f:
            json.dump(self.design_result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Design saved to: {design_file}")
        return str(design_file)
