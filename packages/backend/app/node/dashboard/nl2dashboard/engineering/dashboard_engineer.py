"""Dashboard Engineer

Responsible for implementing the Dashboard based on design results.
Refers to the implementation process of va_system_builder.py.
"""

import json
import os
import re
import shutil
import glob
from typing import Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..llm_compat import LLMClient, Message
from app.core.config import settings


class DashboardEngineer:
    """Dashboard Engineer
    
    Generates actual Dashboard code or configuration files based on design results.
    Refers to the implementation of the _build_va_system method in va_system_builder.py.
    
    Attributes:
        design_result: Design result dictionary
        output_path: Output path
        llm_client: LLM client
        page_theme_content: Page theme content (for chart beautification)
    
    Example:
        >>> engineer = DashboardEngineer(llm_client=llm_client)
        >>> engineer.implement(design_result, output_path, info_doc)
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None, model: str | None = None):
        """Initialize the Dashboard Engineer
        
        Args:
            llm_client: LLM client (optional, if None, it will be retrieved from environment variables)
            model: Model name to use
        """
        self.design_result: Optional[Dict[str, Any]] = None
        self.output_path: Optional[str] = None
        self.page_theme_content: str = ""
        
        # Load template mapping configuration
        self.template_mapping = self._load_template_mapping()
        
        resolved_model = model or settings.LLM_MODEL

        # Initialize LLM client
        if llm_client is None:
            api_key = os.getenv("DEEPEYE_LLM_API_KEY") or settings.LLM_API_KEY
            base_url = os.getenv("DEEPEYE_LLM_BASE_URL") or settings.LLM_BASE_URL
            env_model = os.getenv("DEEPEYE_LLM_MODEL", resolved_model)
            
            if api_key:
                self.llm_client = LLMClient(api_key=api_key, base_url=base_url)
                self.llm_model = env_model
            else:
                self.llm_client = None
                self.llm_model = env_model
        else:
            self.llm_client = llm_client
            self.llm_model = resolved_model  # Use the provided model name
    
    def implement(
        self,
        design_result: Dict[str, Any],
        output_path: str,
        info_doc: Dict[str, Any]
    ) -> str:
        """Implement Dashboard
        
        Refers to the implementation of the _build_va_system method in va_system_builder.py.
        
        Args:
            design_result: Design result dictionary, containing:
                - layout: Dashboard layout structure
                - charts: List of chart configurations
                - filters: Filter configurations
                - metadata: Design metadata
            output_path: Output path
            info_doc: Information document, containing:
                - question: User question
                - dataset_path: Path to dataset
                - output_path: Output path
                - data_schema: Data schema information
        
        Returns:
            Implemented Dashboard file path (path to va_app directory)
        """
        self.design_result = design_result
        self.output_path = output_path
        
        # Extract information
        question = info_doc.get("question", "")
        dataset_path = info_doc.get("dataset_path", "")
        
        # Build VA system
        va_app_path = self._build_va_system(
            output_path=output_path,
            dataset_path=dataset_path,
            question=question,
            design_result=design_result
        )
        
        return va_app_path
    
    def _build_va_system(
        self,
        output_path: str,
        dataset_path: str,
        question: str,
        design_result: Dict[str, Any]
    ) -> str:
        """Core implementation for building the VA system
        
        Refers to the _build_va_system method in va_system_builder.py.
        
        Implementation steps:
        1. Pre-processing: Template cloning, dataset copying, configuration generation, path updates
        2. Configuration processing: Personalized layout implementation, Filter component data binding
        3. Page template beautification: Generating personalized page styles based on the question topic
        4. Chart beautification: Beautifying chart styles based on the page theme
        
        Args:
            output_path: Output path
            dataset_path: Dataset path
            question: User question
            design_result: Design result
        
        Returns:
            Path to va_app directory
        """
        # ========== Step 1: Pre-processing ==========
        # 1.1 Clone all files from template directory to output_path
        template_path = os.path.join(os.path.dirname(__file__), 'template')
        template_path = os.path.abspath(template_path)
        
        # Create va_app folder in the target directory
        va_app_path = os.path.join(output_path, 'va_app')
        if os.path.exists(va_app_path):
            shutil.rmtree(va_app_path)
        shutil.copytree(template_path, va_app_path)
        
        # 1.2 Find chart code directory from design results
        echart_source = None
        if 'charts_directory' in design_result:
            charts_dir = design_result['charts_directory']
            if os.path.isabs(charts_dir):
                echart_source = os.path.join(charts_dir, 'echart_code') if os.path.exists(charts_dir) else None
            else:
                echart_source = os.path.join(output_path, charts_dir, 'echart_code')
        
        # If not specified in design results, try to find default location
        if not echart_source or not os.path.exists(echart_source):
            # Look for visualizations_* directories
            viz_charts_dirs = glob.glob(os.path.join(output_path, 'visualizations_*'))
            if viz_charts_dirs:
                # Use the latest one
                viz_charts_dirs.sort(reverse=True)
                echart_source = os.path.join(viz_charts_dirs[0], 'echart_code')
        
        charts_dest = os.path.join(va_app_path, 'public', 'charts')
        
        if echart_source and os.path.exists(echart_source):
            # Detect and generate HTML files (if they don't exist)
            # print(f"🔧 Generating HTML from Python charts...")
            # self._generate_html_from_python_charts(
            #     echart_source_dir=echart_source,
            #     dataset_path=dataset_path,
            #     max_workers=4
            # )
            
            # Clear target charts directory
            if os.path.exists(charts_dest):
                shutil.rmtree(charts_dest)
            os.makedirs(charts_dest)
            
            # Copy all echart files and process
            print(f"📋 Processing and copying chart files...")
            for file in os.listdir(echart_source):
                src_file = os.path.join(echart_source, file)
                dst_file = os.path.join(charts_dest, file)
                if os.path.isfile(src_file) and file.endswith('.html'):
                    # Read, process and write HTML file
                    self._process_echart_html(src_file, dst_file)
                elif os.path.isfile(src_file):
                    # Copy non-HTML files directly
                    shutil.copy2(src_file, dst_file)
            print(f"✓ Processed echart code from {echart_source}")
        
        # 1.3 Copy dashboard_config.json to va_app/public/configs
        # This file is generated by DashboardDesigner.save_design()
        configs_dest = os.path.join(va_app_path, 'public', 'configs')
        
        # Find configuration file (could be dashboard_config.json or dashboard_config_*.json)
        config_files = []
        dashboard_config_path = os.path.join(output_path, 'dashboard_config.json')
        if os.path.exists(dashboard_config_path):
            config_files.append(dashboard_config_path)
        else:
            # Find configuration file with timestamp
            config_pattern = os.path.join(output_path, 'dashboard_config_*.json')
            config_files = glob.glob(config_pattern)
        
        config_file = None
        dashboard_config_filename = None
        
        if config_files:
            # Use the first found configuration file
            source_config = config_files[0]
            dashboard_config_filename = os.path.basename(source_config)
            config_file = os.path.join(configs_dest, dashboard_config_filename)
            
            shutil.copy2(source_config, config_file)
            print(f"✓ Copied config file: {dashboard_config_filename}")
            
            # Update python_code_name and html_code_name fields in the config file
            if os.path.exists(charts_dest):
                print(f"🔧 Updating config with HTML names...")
                self._update_config_with_html_names(config_file, charts_dest)
        else:
            print(f"⚠️  No dashboard_config.json found in {output_path}, generating from design_result...")
            # If config file is not found, generate from design_result
            config_file = self._generate_dashboard_config(design_result, va_app_path)
            if config_file:
                dashboard_config_filename = os.path.basename(config_file)
                if os.path.exists(charts_dest):
                    self._update_config_with_html_names(config_file, charts_dest)
        
        # 1.4 Copy dataset to va_app/public/data
        if dataset_path and os.path.exists(dataset_path):
            data_dest = os.path.join(va_app_path, 'public', 'data')
            os.makedirs(data_dest, exist_ok=True)
            filename = os.path.basename(dataset_path)
            dst_file = os.path.join(data_dest, filename)
            shutil.copy2(dataset_path, dst_file)
            print(f"✓ Copied dataset to {dst_file}")
            if config_file:
                self._ensure_config_dataset_path(config_file, filename)
        
        # 1.5 Update schema_path configuration in app.py to point to the config file
        if dashboard_config_filename:
            app_py_path = os.path.join(va_app_path, 'app.py')
            self._update_app_config(app_py_path, dashboard_config_filename)
        
        # ========== Step 2: Configuration processing ==========
        if config_file and self.llm_client:
            # 2.1 Personalized layout implementation: Generate Layout and Position info
            # 2.2 Filter component data binding: Generate Options for Filter components
            print(f"🔧 Processing dashboard config (layout + filter options)...")
            self._process_dashboard_config(
                config_file_path=config_file,
                dataset_path=dataset_path,
                question=question,
                va_app_path=va_app_path,
                max_retries=3
            )
        
        # ========== Step 3: Page template beautification ==========
        # Dynamically select template based on the number of highlight blocks and charts in the config
        selected_template = self._select_template_by_config(config_file)
        print(f"🎨 Applying {selected_template} with variable substitution...")
        template_success = self._apply_template_with_substitution(
            template_name=selected_template,
            va_app_path=va_app_path,
            question=question,
            config_file=config_file
        )
        
        # If page template applied successfully, update pageTemplate path in config
        if template_success and config_file:
            print(f"🔧 Updating page template path in config...")
            self._update_page_template_config(config_file)
        
        return va_app_path

    def _ensure_config_dataset_path(self, config_file_path: str, dataset_filename: str) -> None:
        if not config_file_path or not os.path.exists(config_file_path):
            return
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to read dashboard config for dataset path update: {e}")
            return

        data_source = config.get("dataSource")
        if not isinstance(data_source, dict):
            data_source = {}
            config["dataSource"] = data_source

        data_source["path"] = f"/data/{dataset_filename}"

        try:
            with open(config_file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to write dashboard config dataset path: {e}")
    
    def _generate_dashboard_config(
        self,
        design_result: Dict[str, Any],
        va_app_path: str
    ) -> Optional[str]:
        """Generate Dashboard configuration file
        
        Args:
            design_result: Design result
            va_app_path: VA application path
        
        Returns:
            Path to the configuration file
        """
        configs_dest = os.path.join(va_app_path, 'public', 'configs')
        
        # Generate config from design result
        config = {
            "layout": design_result.get("layout", {}),
            "blocks": design_result.get("blocks", [])
        }
        
        # Add dataSource information (required for app.py to find data file)
        if "dataSource" in design_result:
            data_source = design_result["dataSource"].copy()
            # Convert absolute path to path relative to va_app
            if "path" in data_source and os.path.isabs(data_source["path"]):
                # Data file should be in public/data/
                filename = os.path.basename(data_source["path"])
                data_source["path"] = f"/data/{filename}"
            config["dataSource"] = data_source
        
        # If no blocks, try to generate from old format charts and filters
        if not config["blocks"]:
            # Add chart blocks
            charts = design_result.get("charts", [])
            for i, chart in enumerate(charts):
                config["blocks"].append({
                    "id": f"chart_{i}",
                    "blockType": "view",
                    "blockContent": {
                        "description": chart.get("title", ""),
                        "html_code_name": f"chart_{i}.html"
                    }
                })
            
            # Add filter blocks
            filters = design_result.get("filters", [])
            for i, filter_config in enumerate(filters):
                config["blocks"].append({
                    "id": f"filter_{i}",
                    "blockType": "filter",
                    "blockContent": {
                        "field": filter_config.get("field", ""),
                        "type": filter_config.get("type", "select"),
                        "options": []
                    }
                })
        
        # Save configuration
        config_file = os.path.join(configs_dest, 'dashboard_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # print(f"✓ Generated dashboard config with {len(config.get('blocks', []))} blocks")
        
        return config_file
    
    def _process_dashboard_config(
        self,
        config_file_path: str,
        dataset_path: str,
        question: str,
        va_app_path: str,
        max_retries: int = 3
    ):
        """Process dashboard configuration: Add Filter Options, Layout, and Position info
        
        Refers to the _process_dashboard_config method in va_system_builder.py.
        
        Args:
            config_file_path: Path to configuration file
            dataset_path: Path to dataset
            question: User question
            va_app_path: VA application path
            max_retries: Maximum number of retries
        """
        if not self.llm_client:
            return
        
        try:
            # Read configuration file
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            original_view_block_assets = {}
            for block in config.get('blocks', []):
                if block.get('blockType') != 'view':
                    continue
                block_id = block.get('id') or block.get('blockId')
                block_content = block.get('blockContent', {}) or {}
                if not block_id:
                    continue
                original_view_block_assets[block_id] = {
                    'python_code_name': block_content.get('python_code_name'),
                    'html_code_name': block_content.get('html_code_name'),
                }
            
            # 1. Generate Options and Range for Filter components
            if dataset_path and os.path.exists(dataset_path):
                try:
                    import pandas as pd
                    df = pd.read_csv(dataset_path)
                    
                    if 'blocks' in config:
                        for block in config['blocks']:
                            if block.get('blockType') == 'filter' and 'blockContent' in block:
                                field = block['blockContent'].get('field')
                                control_type = block['blockContent'].get('controlType', 'select')
                                if field and field in df.columns:
                                    # Generate date range configuration for date_range type
                                    if control_type == 'date_range':
                                        try:
                                            # Try converting field to date type
                                            date_series = pd.to_datetime(df[field], errors='coerce').dropna()
                                            
                                            if len(date_series) > 0:
                                                min_date = date_series.min()
                                                max_date = date_series.max()
                                                
                                                # Format as date string
                                                # Check if it only has date part (time is 00:00:00)
                                                if min_date.hour == 0 and min_date.minute == 0 and min_date.second == 0:
                                                    min_date_str = min_date.strftime('%Y/%m/%d')
                                                else:
                                                    min_date_str = min_date.strftime('%Y/%m/%d %H:%M:%S')
                                                
                                                if max_date.hour == 0 and max_date.minute == 0 and max_date.second == 0:
                                                    max_date_str = max_date.strftime('%Y/%m/%d')
                                                else:
                                                    max_date_str = max_date.strftime('%Y/%m/%d %H:%M:%S')
                                                
                                                # Set range for date_range
                                                block['blockContent']['range'] = {
                                                    'min': min_date_str,
                                                    'max': max_date_str
                                                }
                                                
                                                # Remove unneeded options
                                                if 'options' in block['blockContent']:
                                                    del block['blockContent']['options']
                                                
                                                print(f"  ✓ Set date_range for {field}: {min_date_str} ~ {max_date_str}")
                                        except Exception as e:
                                            print(f"  ⚠️  Failed to process date_range for {field}: {e}")
                                            pass
                                    # Generate range configuration for slider or range type
                                    elif control_type in ('slider', 'range'):
                                        try:
                                            # Determine if it's a time field
                                            is_time_field = 'time' in field.lower() or 'hour' in field.lower()
                                            
                                            if is_time_field:
                                                # Time field: Extract hour from time string
                                                def extract_hour(time_str):
                                                    if pd.isna(time_str):
                                                        return None
                                                    time_str = str(time_str).strip()
                                                    if ':' in time_str:
                                                        hour_str = time_str.split(':')[0]
                                                        try:
                                                            return int(hour_str)
                                                        except ValueError:
                                                            return None
                                                    return None
                                                
                                                values = df[field].apply(extract_hour).dropna()
                                            else:
                                                # Numeric field: Try converting to numeric
                                                values = pd.to_numeric(df[field], errors='coerce').dropna()
                                            
                                            if len(values) > 0:
                                                min_val = float(values.min())
                                                max_val = float(values.max())
                                                
                                                # Calculate appropriate step
                                                if is_time_field:
                                                    step = 1  # 1 hour step for time fields
                                                else:
                                                    # Automatically calculate step for numeric fields based on range
                                                    range_size = max_val - min_val
                                                    if range_size <= 10:
                                                        step = 0.1
                                                    elif range_size <= 100:
                                                        step = 1
                                                    elif range_size <= 1000:
                                                        step = 10
                                                    elif range_size <= 10000:
                                                        step = 100
                                                    else:
                                                        step = max(1, int(range_size / 100))  # Approx 100 steps
                                                
                                                # Set range for slider
                                                block['blockContent']['range'] = {
                                                    'min': min_val,
                                                    'max': max_val,
                                                    'step': step
                                                }
                                                
                                                # Remove unneeded options
                                                if 'options' in block['blockContent']:
                                                    del block['blockContent']['options']
                                                
                                                print(f"  ✓ Set slider range for {field}: {min_val}-{max_val} (step: {step})")
                                            else:
                                                print(f"  ⚠️  No valid values found for slider field {field}")
                                        except Exception as e:
                                            print(f"  ⚠️  Failed to process slider for {field}: {e}")
                                            pass
                                    else:
                                        # Generate options for non-slider types
                                        unique_values = df[field].dropna().unique().tolist()
                                        # Limit to maximum 50 options
                                        if len(unique_values) > 50:
                                            unique_values = unique_values[:50]
                                        # Do not add "All" for multiselect type
                                        if control_type == 'multiselect':
                                            options = [str(v) for v in unique_values]
                                        else:
                                            # Add "All" for other types (select, checkbox, etc.)
                                            options = ["All"] + [str(v) for v in unique_values]
                                        block['blockContent']['options'] = options
                except Exception as e:
                    # Skip if reading dataset fails
                    print(f"  ⚠️  Failed to process filters: {e}")
                    pass
            
            # 2. Read chart dimensions from HTML files
            chart_dimensions = self._extract_chart_dimensions(config, va_app_path)
            chart_dimensions_str = self._format_chart_dimensions(chart_dimensions)
            
            # 3. Generate Layout and Position info using LLM (with retry mechanism)
            from .prompt import LAYOUT_POSITION_GENERATION_PROMPT
            
            config_json_str = json.dumps(config, ensure_ascii=False, indent=2)
            prompt = LAYOUT_POSITION_GENERATION_PROMPT.format(
                config_json=config_json_str,
                chart_dimensions=chart_dimensions_str
            )
            
            updated_config = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Call LLM
                    messages = [Message(role="user", content=prompt)]
                    response = self.llm_client.generate(
                        messages,
                        model=self.llm_model,
                        temperature=0.0,
                        max_tokens=settings.LLM_MAX_TOKENS
                    )
                    
                    response_content = response.content
                    
                    # Try to extract JSON
                    json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(1)
                    elif '```' in response_content:
                        # If there's a code block but no json tag
                        response_content = re.sub(r'```\w*\s*|\s*```', '', response_content)
                    
                    response_content = response_content.strip()
                    
                    # Try to parse JSON
                    try:
                        updated_config = json.loads(response_content)
                        break  # Successfully parsed, exit retry loop
                    except json.JSONDecodeError:
                        # Try to fix common issues
                        response_fixed = re.sub(r',\s*}', '}', response_content)
                        response_fixed = re.sub(r',\s*\]', ']', response_fixed)
                        
                        try:
                            updated_config = json.loads(response_fixed)
                            break
                        except json.JSONDecodeError:
                            if attempt < max_retries:
                                prompt = f"{prompt}\n\nIMPORTANT: Please return ONLY valid JSON, no explanations."
                            else:
                                # Use default configuration
                                updated_config = config
                                if 'layout' not in updated_config:
                                    updated_config['layout'] = {
                                        "type": "grid",
                                        "columns": 3,
                                        "gap": 1.0,
                                        "pageTemplate": "public/templates/page_default.html"
                                    }
                
                except Exception:
                    if attempt >= max_retries:
                        # Use default configuration
                        updated_config = config
                        if 'layout' not in updated_config:
                            updated_config['layout'] = {
                                "type": "grid",
                                "columns": 3,
                                "gap": 1.0,
                                "pageTemplate": "public/templates/page_default.html"
                            }
            
            # If all attempts fail, use default configuration
            if updated_config is None:
                updated_config = config
                if 'layout' not in updated_config:
                    updated_config['layout'] = {
                        "type": "grid",
                        "columns": 3,
                        "gap": 1.0,
                        "pageTemplate": "public/templates/page_default.html"
                    }
            
            # Add default position for each block (if missing)
            if 'blocks' in updated_config:
                row = 1
                col = 1
                for block in updated_config['blocks']:
                    if 'position' not in block and block.get('blockType') in ['highlight', 'view']:
                        block['position'] = {
                            "col": col,
                            "row": row,
                            "span": 1,
                            "rowSpan": 1
                        }
                        col += 1
                        if col > 3:
                            col = 1
                            row += 1

                for block in updated_config['blocks']:
                    if block.get('blockType') != 'view':
                        continue
                    block_id = block.get('id') or block.get('blockId')
                    if not block_id:
                        continue
                    previous_assets = original_view_block_assets.get(block_id)
                    if not previous_assets:
                        continue
                    block_content = block.setdefault('blockContent', {})
                    if previous_assets.get('python_code_name') and not block_content.get('python_code_name'):
                        block_content['python_code_name'] = previous_assets['python_code_name']
                    if previous_assets.get('html_code_name') and not block_content.get('html_code_name'):
                        block_content['html_code_name'] = previous_assets['html_code_name']

            # Save updated configuration
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_config, f, ensure_ascii=False, indent=2)
        
        except Exception:
            # Continue execution even if processing fails
            pass
    
    def _extract_chart_dimensions(self, config: dict, va_app_path: str) -> dict:
        """Extract chart dimension information from HTML files
        
        Refers to the _extract_chart_dimensions method in va_system_builder.py.
        
        Args:
            config: Configuration file dictionary
            va_app_path: VA application path
        
        Returns:
            Dictionary in the format {block_id: {"width": int, "height": int, "aspect_ratio": float, "html_file": str}}
        """
        dimensions = {}
        charts_dir = os.path.join(va_app_path, 'public', 'charts')
        
        if 'blocks' not in config or not os.path.exists(charts_dir):
            return dimensions
        
        for block in config['blocks']:
            if block.get('blockType') != 'view':
                continue
            
            block_id = block.get('id') or block.get('blockId')
            block_content = block.get('blockContent', {})
            html_file = block_content.get('html_code_name')
            
            if not html_file or not block_id:
                continue
            
            html_path = os.path.join(charts_dir, html_file)
            
            if not os.path.exists(html_path):
                continue
            
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Extract width and height from the div's style attribute
                width = None
                height = None
                
                style_match = re.search(r'style\s*=\s*["\']([^"\']*width[^"\']*)["\']', html_content, re.IGNORECASE)
                if style_match:
                    style_str = style_match.group(1)
                    width_match = re.search(r'width\s*:\s*(\d+)px', style_str, re.IGNORECASE)
                    height_match = re.search(r'height\s*:\s*(\d+)px', style_str, re.IGNORECASE)
                    
                    if width_match:
                        width = int(width_match.group(1))
                    if height_match:
                        height = int(height_match.group(1))
                
                # Calculate aspect ratio if dimensions extracted successfully
                if width and height:
                    aspect_ratio = round(width / height, 2)
                    dimensions[block_id] = {
                        "width": width,
                        "height": height,
                        "aspect_ratio": aspect_ratio,
                        "html_file": html_file,
                        "description": block_content.get('description', '')
                    }
                else:
                    # Use default values
                    dimensions[block_id] = {
                        "width": 1000,
                        "height": 500,
                        "aspect_ratio": 2.0,
                        "html_file": html_file,
                        "description": block_content.get('description', '')
                    }
            except Exception:
                # Use default values
                dimensions[block_id] = {
                    "width": 1000,
                    "height": 500,
                    "aspect_ratio": 2.0,
                    "html_file": html_file,
                    "description": block_content.get('description', '')
                }
        
        return dimensions
    
    def _format_chart_dimensions(self, dimensions: dict) -> str:
        """Format chart dimension information into a readable string
        
        Refers to the _format_chart_dimensions method in va_system_builder.py.
        
        Args:
            dimensions: Chart dimensions dictionary
        
        Returns:
            Formatted string
        """
        if not dimensions:
            return "No chart dimension information available."
        
        lines = ["### Chart Dimensions and Aspect Ratios:\n"]
        
        for block_id, info in dimensions.items():
            width = info['width']
            height = info['height']
            ratio = info['aspect_ratio']
            html_file = info['html_file']
            description = info.get('description', '')
            
            # Determine chart shape type
            if ratio > 2.0:
                shape_type = "Wide"
            elif ratio > 1.2:
                shape_type = "Landscape"
            elif ratio >= 0.8:
                shape_type = "Square"
            elif ratio >= 0.5:
                shape_type = "Portrait"
            else:
                shape_type = "Tall"
            
            lines.append(f"**{block_id}**:")
            lines.append(f"  - File: `{html_file}`")
            lines.append(f"  - Dimensions: {width}px × {height}px")
            lines.append(f"  - Aspect Ratio: {ratio} ({shape_type})")
            if description:
                lines.append(f"  - Description: {description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _load_template_mapping(self) -> Dict[str, Any]:
        """Load template mapping configuration file
        
        Returns:
            Template mapping configuration dictionary
        """
        mapping_file = os.path.join(
            os.path.dirname(__file__),
            'template_mapping.json'
        )
        
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️  Template mapping file not found: {mapping_file}, using default")
                # Return default configuration
                return {
                    "template_library_path": "template_library",
                    "default_template": "template_base.html",
                    "rules": [],
                    "templates": {}
                }
        except Exception as e:
            print(f"⚠️  Error loading template mapping: {e}, using default")
            return {
                "template_library_path": "template_library",
                "default_template": "template_base.html",
                "rules": [],
                "templates": {}
            }
    
    def _select_template_by_config(self, config_file: Optional[str] = None) -> str:
        """Select a template based on the number of highlight blocks and charts in the configuration file
        
        Read rules from mapping configuration and match.
        
        Args:
            config_file: Configuration file path (optional)
        
        Returns:
            Template filename (e.g., 'template_base.html')
        """
        # Get default template from mapping config
        default_template = self.template_mapping.get('default_template', 'template_base.html')
        
        if not config_file or not os.path.exists(config_file):
            return default_template
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Count the number of highlight and view blocks
            highlight_count = 0
            view_count = 0
            
            for block in config.get('blocks', []):
                block_type = block.get('blockType', '')
                if block_type == 'highlight':
                    highlight_count += 1
                elif block_type == 'view':
                    view_count += 1
            
            # Read rules from mapping config and match
            rules = self.template_mapping.get('rules', [])
            for rule in rules:
                conditions = rule.get('conditions', {})
                match = True
                
                # Check highlight_count condition
                if 'highlight_count' in conditions:
                    highlight_cond = conditions['highlight_count']
                    if 'min' in highlight_cond and highlight_count < highlight_cond['min']:
                        match = False
                    if 'max' in highlight_cond and highlight_count > highlight_cond['max']:
                        match = False
                
                # Check view_count condition
                if 'view_count' in conditions:
                    view_cond = conditions['view_count']
                    if 'min' in view_cond and view_count < view_cond['min']:
                        match = False
                    if 'max' in view_cond and view_count > view_cond['max']:
                        match = False
                
                # If matched, return the corresponding template
                if match:
                    template = rule.get('template')
                    if template:
                        print(f"✓ Matched rule '{rule.get('name', 'unknown')}': {rule.get('description', '')}")
                        return template
            
            # If no rule matched, return the default template
            print(f"✓ No rule matched, using default template: {default_template}")
            return default_template
            
        except Exception as e:
            print(f"⚠️  Error selecting template: {e}, using default template")
            return default_template
    
    def _apply_template_with_substitution(
        self,
        template_name: str,
        va_app_path: str,
        question: str,
        config_file: Optional[str] = None
    ) -> bool:
        """Apply the specified template and perform variable substitution (generic method)
        
        Process:
        1. Read template from template library (template_library)
        2. Copy template to va_app/public/templates/
        3. Perform variable substitution and application
        
        Args:
            template_name: Template filename (e.g., 'template_base.html' or 'template_with_table.html')
            va_app_path: VA application path
            question: User question
            config_file: Configuration file path (optional)
        
        Returns:
            Whether template was applied successfully
        """
        try:
            # 1. Get template information from mapping config
            templates_info = self.template_mapping.get('templates', {})
            template_info = templates_info.get(template_name, {})
            
            # Get template library path
            template_library_path = self.template_mapping.get('template_library_path', 'template_library')
            template_library_dir = os.path.join(os.path.dirname(__file__), template_library_path)
            
            # 2. Determine template source file path
            # Prioritize using source_path from mapping config
            if template_info.get('source_path'):
                template_source = os.path.join(os.path.dirname(__file__), template_info['source_path'])
            else:
                # Fallback to template library directory
                template_source = os.path.join(template_library_dir, template_name)
            
            # If not present in template library, try finding in old locations (backward compatibility)
            if not os.path.exists(template_source):
                # Try finding from ui_templates directory
                template_source = os.path.join(
                    os.path.dirname(__file__),
                    'ui_templates',
                    template_name
                )
                
                # If still not found, try template/public/templates
                if not os.path.exists(template_source):
                    template_source = os.path.join(
                        os.path.dirname(__file__),
                        'template',
                        'public',
                        'templates',
                        template_name
                    )
            
            if not os.path.exists(template_source):
                print(f"⚠️  Template {template_name} not found")
                # Fallback to default template if specified template not found
                default_template = self.template_mapping.get('default_template', 'template_base.html')
                if template_name != default_template:
                    print(f"⚠️  Falling back to {default_template}")
                    return self._apply_template_with_substitution(
                        default_template, va_app_path, question, config_file
                    )
                return False
            
            # 3. Read template content
            with open(template_source, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 4. Ensure target directory exists
            templates_dest = os.path.join(va_app_path, 'public', 'templates')
            os.makedirs(templates_dest, exist_ok=True)
            
            # 5. Read all information from configuration file
            dashboard_name = "Dashboard"
            dashboard_description = "Explore data insights and analytics."
            chart_titles = []
            chart_ids = []
            highlight_titles = []
            highlight_ids = []
            
            if config_file and os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 1. Get dashboard name and description from metadata
                    metadata = config.get('metadata', {})
                    dashboard_name = metadata.get('dashboard_name', dashboard_name)
                    dashboard_description = metadata.get('dashboard_description', dashboard_description)
                    
                    # If metadata is missing, try getting from layout
                    if dashboard_name == "Dashboard":
                        layout = config.get('layout', {})
                        dashboard_name = layout.get('dashboard_name', dashboard_name)
                        dashboard_description = layout.get('dashboard_description', dashboard_description)
                    
                    # 2. Get titles and IDs for all highlight blocks
                    for block in config.get('blocks', []):
                        if block.get('blockType') == 'highlight':
                            block_id = block.get('id', '')
                            block_content = block.get('blockContent', {})
                            title = block_content.get('title', '')
                            if block_id:
                                highlight_ids.append(block_id)
                            if title:
                                highlight_titles.append(title)
                    
                    # 3. Get titles and IDs for all view blocks (following config order)
                    for block in config.get('blocks', []):
                        if block.get('blockType') == 'view':
                            block_id = block.get('id', '')
                            block_content = block.get('blockContent', {})
                            # Prioritize description, fallback to title
                            title = block_content.get('description', '') or block_content.get('title', '')
                            if block_id:
                                chart_ids.append(block_id)
                            if title:
                                chart_titles.append(title)
                except Exception as e:
                    print(f"⚠️  Error reading config file: {e}")
                    # If reading fails, use question as fallback
                    dashboard_name = self._extract_dashboard_name(question)
                    dashboard_description = self._extract_dashboard_description(question)
            
            # Variable substitution
            # 1. Replace Dashboard name
            template_content = re.sub(
                r'<span class="font-bold text-xl tracking-tight text-gray-800">DataMiner</span>',
                f'<span class="font-bold text-xl tracking-tight text-gray-800">{dashboard_name}</span>',
                template_content
            )
            
            # 2. Replace title and description
            template_content = re.sub(
                r'<h2 class="text-xl font-bold text-gray-800">Maven Roasters Sales</h2>\s*<p class="text-xs text-gray-500 mt-0.5">Explore sales trends and product performance across NYC locations\.</p>',
                f'<h2 class="text-xl font-bold text-gray-800">{dashboard_name}</h2>\n                <p class="text-xs text-gray-500 mt-0.5">{dashboard_description}</p>',
                template_content
            )
            
            # 3. Replace chart titles (find and replace all chart titles)
            chart_title_pattern = r'(<h3 class="font-bold text-gray-800 mb-6 text-sm uppercase tracking-wide flex items-center gap-2">\s*<span class="w-1 h-4 bg-\[#[^\]]+\] rounded-full"></span>\s*)([^<]+)(</h3>)'
            
            title_index = 0
            def replace_chart_title(match):
                nonlocal title_index
                prefix = match.group(1)
                suffix = match.group(3)
                
                # Use available chart title if available; otherwise keep unchanged
                if title_index < len(chart_titles):
                    new_title = chart_titles[title_index]
                    title_index += 1
                    return prefix + new_title + suffix
                return match.group(0)
            
            template_content = re.sub(chart_title_pattern, replace_chart_title, template_content)
            
            # 4. Replace chart IDs (replace intent_X_goal_0_chart0 in template with actual IDs from config)
            if chart_ids:
                # Find all chart ID patterns: intent_DIGIT_goal_DIGIT_chartDIGIT
                chart_id_pattern = r'id="(intent_\d+_goal_\d+_chart\d+)"'
                
                chart_id_index = 0
                def replace_chart_id(match):
                    nonlocal chart_id_index
                    
                    # Use available chart ID if available; otherwise keep unchanged
                    if chart_id_index < len(chart_ids):
                        new_id = chart_ids[chart_id_index]
                        chart_id_index += 1
                        return f'id="{new_id}"'
                    return match.group(0)
                
                template_content = re.sub(chart_id_pattern, replace_chart_id, template_content)
            
            # 5. Inject configuration data for JavaScript if using the universal template
            if template_name == 'template_universal.html' and config_file and os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # Inject configuration data into HTML
                    config_json_str = json.dumps(config_data, ensure_ascii=False)
                    config_script = f'\n<script id="dashboard-config-data" type="application/json">{config_json_str}</script>\n'
                    
                    # Insert before the first <script> tag to ensure config is available before template script runs
                    first_script_pos = template_content.find('<script')
                    if first_script_pos != -1:
                        template_content = template_content[:first_script_pos] + config_script + template_content[first_script_pos:]
                    elif '</body>' in template_content:
                        template_content = template_content.replace('</body>', config_script + '</body>')
                    elif '</div>' in template_content:
                        # Insert before the last </div>
                        last_div_pos = template_content.rfind('</div>')
                        if last_div_pos != -1:
                            template_content = template_content[:last_div_pos] + config_script + template_content[last_div_pos:]
                    else:
                        # Fallback: append to end
                        template_content = template_content + config_script
                    
                    print(f"✓ Injected dashboard config data for universal template")
                except Exception as e:
                    print(f"⚠️  Failed to inject config data for universal template: {e}")
            
            # 7. Save replaced template to target path (templates_dest already created)
            customized_template_path = os.path.join(templates_dest, 'page_customized.html')
            with open(customized_template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            # Store theme content for chart beautification
            self.page_theme_content = template_content
            
            print(f"✓ Applied {template_name} with substitutions")
            return True
            
        except Exception as e:
            print(f"❌ Error applying template {template_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extract_dashboard_name(self, question: str) -> str:
        """Extract Dashboard name from the question
        
        Args:
            question: User question
        
        Returns:
            Dashboard name
        """
        if not question:
            return "Dashboard"
        
        # Try extracting key nouns as the name
        # Remove common question words
        question_clean = question.strip()
        
        # Use directly if question is short
        if len(question_clean) <= 30:
            # Remove punctuation
            question_clean = re.sub(r'[?。！？]$', '', question_clean)
            return question_clean[:30]
        
        # If long, extract first few keywords
        # Simple approach: take first 20 characters
        question_clean = re.sub(r'[?。！？]$', '', question_clean)
        return question_clean[:20] + "..."
    
    def _extract_dashboard_description(self, question: str) -> str:
        """Extract Dashboard description from the question
        
        Args:
            question: User question
        
        Returns:
            Dashboard description
        """
        if not question:
            return "Explore data insights and analytics."
        
        # Use directly if question is short
        if len(question) <= 60:
            return question
        
        # Use first 50 characters if long
        return question[:50] + "..."
    
    def _update_app_config(self, app_py_path: str, config_filename: str):
        """Update configuration file path in app.py
        
        Refers to the _update_app_config method in va_system_builder.py.
        
        Args:
            app_py_path: Path to app.py file
            config_filename: Configuration filename
        """
        try:
            with open(app_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace schema_path configuration
            pattern = r'schema_path\s*=\s*os\.path\.join\(CONFIGS_DIR,\s*["\'][^"\']*["\']\)'
            replacement = f'schema_path = os.path.join(CONFIGS_DIR, "{config_filename}")'
            
            updated_content = re.sub(pattern, replacement, content)
            
            with open(app_py_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        except Exception:
            pass
    
    def _update_page_template_config(self, config_file_path: str):
        """Update pageTemplate path in the configuration file
        
        Refers to the _update_page_template_config method in va_system_builder.py.
        
        Args:
            config_file_path: Path to configuration file
        """
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Update pageTemplate in layout
            if 'layout' in config:
                config['layout']['pageTemplate'] = 'public/templates/page_customized.html'
                
                with open(config_file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _generate_html_from_python_charts(
        self, 
        echart_source_dir: str, 
        dataset_path: str,
        max_workers: int = 4
    ):
        """Detect if HTML files exist in echart_code directory; run Python code to generate them if not.
        
        Refers to the _generate_html_from_python_charts method in va_system_builder.py.
        
        Args:
            echart_source_dir: Path to echart_code directory
            dataset_path: Path to dataset
            max_workers: Maximum number of parallel workers
        """
        if not os.path.exists(echart_source_dir):
            print(f"⚠️  EChart source directory not found: {echart_source_dir}")
            return
        
        # 1. Check if HTML files already exist
        html_files = [f for f in os.listdir(echart_source_dir) if f.endswith('.html')]
        python_files = [f for f in os.listdir(echart_source_dir) if f.endswith('.py')]
        
        if html_files:
            print(f"✓ Found {len(html_files)} HTML files in {echart_source_dir}, skip generation")
            return
        
        if not python_files:
            print(f"⚠️  No Python files found in {echart_source_dir}")
            return
        
        print(f"🔧 No HTML files found, generating from {len(python_files)} Python files...")
        
        # 2. Prepare data path (verify dataset exists)
        if not os.path.exists(dataset_path):
            print(f"❌ Dataset not found: {dataset_path}")
            return
        
        # 3. Define execution function for a single Python file
        def execute_python_chart(py_file: str) -> Tuple[str, bool, str]:
            """Execute a single Python chart file to generate HTML"""
            py_path = os.path.join(echart_source_dir, py_file)
            chart_name = os.path.splitext(py_file)[0]
            
            try:
                # Read Python code
                with open(py_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Check code structure: is plot function defined?
                has_plot_function = 'def plot(' in code
                
                # Create temporary execution environment
                exec_globals = {
                    '__file__': py_path,
                    '__name__': '__main__',
                    'dataset_path': dataset_path,
                }
                
                # Build execution code
                if has_plot_function:
                    # Code generated by LIDA: has plot(data) function
                    exec_code = f"""
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import *
import os

# Load data
data = pd.read_csv(r'{dataset_path}')

# Execute original code (defining plot function)
{code}

# Call plot function to generate chart
chart = plot(data)

# Render HTML file
chart.render(r'{os.path.join(echart_source_dir, chart_name + ".html")}')
"""
                else:
                    # Code that generates chart directly
                    exec_code = f"""
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import *
import os

# Load data
data = pd.read_csv(r'{dataset_path}')

# Execute original code
{code}

# Find chart object and render
for var_name in dir():
    var = locals().get(var_name)
    if hasattr(var, 'render') and hasattr(var, 'options'):
        var.render(r'{os.path.join(echart_source_dir, chart_name + ".html")}')
        break
"""
                
                # Execute code to generate HTML
                exec(exec_code, exec_globals)
                
                # Check if HTML file was generated
                expected_html = os.path.join(echart_source_dir, f"{chart_name}.html")
                if os.path.exists(expected_html):
                    return py_file, True, f"✓ Generated {chart_name}.html"
                else:
                    return py_file, False, "✗ No HTML generated after execution"
                        
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                # Log full error info
                print(f"❌ Error executing {py_file}:\n{error_detail}")
                return py_file, False, f"✗ Error: {str(e)}"
        
        # 4. Execute in parallel using thread pool
        success_count = 0
        failed_files = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(execute_python_chart, py_file): py_file 
                for py_file in python_files
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                py_file, success, message = future.result()
                if success:
                    success_count += 1
                    print(f"  {message}")
                else:
                    failed_files.append((py_file, message))
                    print(f"  {message}")
        
        # 5. Output summary
        print(f"HTML generation completed: {success_count}/{len(python_files)} succeeded")
        if failed_files:
            print(f"⚠️  Failed files ({len(failed_files)}):")
            for py_file, error in failed_files:
                print(f"  - {py_file}: {error}")
    
    def _process_echart_html(self, src_file: str, dst_file: str):
        """Process ECharts HTML file: Remove title, truncate data to retain only first 10 examples.
        
        Refers to the _process_echart_html method in va_system_builder.py.
        
        Args:
            src_file: Source file path
            dst_file: Target file path
        """
        try:
            with open(src_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find starting position of option configuration
            option_pattern = r'var option_[a-zA-Z0-9_]+ = ({.*?});'
            match = re.search(option_pattern, content, re.DOTALL)
            
            if match:
                option_json_str = match.group(1)
                
                try:
                    # Parse JSON configuration
                    option_config = json.loads(option_json_str)
                    
                    # 1. Delete title configuration
                    if 'title' in option_config:
                        del option_config['title']
                    
                    # 2. Process series data, keep only first 10 items
                    if 'series' in option_config:
                        for series in option_config['series']:
                            if 'data' in series and isinstance(series['data'], list):
                                original_length = len(series['data'])
                                if original_length > 10:
                                    series['data'] = series['data'][:10]
                            
                            # Hide labels
                            if 'label' in series:
                                series['label']['show'] = False
                    
                    # 3. Process xAxis data, keep only first 10 items
                    if 'xAxis' in option_config:
                        x_axes = option_config['xAxis'] if isinstance(option_config['xAxis'], list) else [option_config['xAxis']]
                        for x_axis in x_axes:
                            if 'data' in x_axis and isinstance(x_axis['data'], list):
                                original_length = len(x_axis['data'])
                                if original_length > 10:
                                    x_axis['data'] = x_axis['data'][:10]
                    
                    # 4. Process grid
                    if 'grid' in option_config:
                        option_config['grid']['containLabel'] = True
                    else:
                        option_config['grid'] = {
                            "containLabel": True
                        }

                    # 5. Process top configuration in legend
                    if 'legend' in option_config:
                        # legend can be dict or list
                        if isinstance(option_config['legend'], dict):
                            option_config['legend']['top'] = '5%'
                        elif isinstance(option_config['legend'], list):
                            for legend in option_config['legend']:
                                if isinstance(legend, dict):
                                    legend['top'] = '5%'
                    
                    # Convert modified configuration back to JSON string
                    new_option_json = json.dumps(option_config, ensure_ascii=False, indent=4)
                    
                    # Replace option configuration in original content
                    new_content = content[:match.start(1)] + new_option_json + content[match.end(1):]
                    
                    # Write to target file
                    with open(dst_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                except json.JSONDecodeError:
                    # If parsing fails, copy original file directly
                    shutil.copy2(src_file, dst_file)
            else:
                # If configuration not found, copy original file directly
                shutil.copy2(src_file, dst_file)
                
        except Exception:
            # If processing fails, copy original file directly
            shutil.copy2(src_file, dst_file)
    
    def _update_config_with_html_names(self, config_file_path: str, charts_dir: str):
        """Update python_code_name and html_code_name fields in configuration file to ensure they point to actual generated files.
        
        Refers to the _update_config_with_html_names method in va_system_builder.py.
        
        Args:
            config_file_path: Path to configuration file
            charts_dir: Path to charts directory
        """
        try:
            # Read configuration file
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Get all files in charts directory
            if not os.path.exists(charts_dir):
                print(f"⚠️  Charts directory not found: {charts_dir}")
                return

            python_files = sorted(
                [name for name in os.listdir(charts_dir) if name.endswith('.py')]
            )
            html_files = sorted(
                [name for name in os.listdir(charts_dir) if name.endswith('.html')]
            )
            python_file_set = set(python_files)
            html_file_set = set(html_files)

            def infer_python_from_html(html_name: str) -> str:
                if not html_name:
                    return ''
                base = os.path.basename(html_name)
                stem, _ = os.path.splitext(base)
                stem = re.sub(r'_iteration\d+$', '', stem)
                candidates = [
                    f'{stem}_echarts.py',
                    f'{stem}.py',
                ]
                for candidate in candidates:
                    if candidate in python_file_set:
                        return candidate
                return ''

            def infer_html_from_python(python_name: str) -> str:
                if not python_name:
                    return ''
                base = os.path.basename(python_name)
                stem, _ = os.path.splitext(base)
                prefixes = [stem]
                if stem.endswith('_echarts'):
                    prefixes.insert(0, stem[:-8])
                for prefix in prefixes:
                    candidates = [
                        name for name in html_files
                        if name == f'{prefix}.html' or name.startswith(f'{prefix}_iteration')
                    ]
                    if candidates:
                        candidates.sort()
                        return candidates[-1]
                return ''

            def infer_python_from_block_id(block_id: str) -> str:
                if not block_id:
                    return ''
                variants = []
                raw = block_id.strip()
                variants.append(raw)

                no_intent = re.sub(r'^intent_\d+_', '', raw)
                if no_intent != raw:
                    variants.append(no_intent)

                compact_goal = re.sub(r'goal_(\d+)', r'goal\1', no_intent)
                if compact_goal not in variants:
                    variants.append(compact_goal)

                compact_all = compact_goal.replace('_', '')
                if compact_all not in variants:
                    variants.append(compact_all)

                for prefix in variants:
                    candidates = [
                        name for name in python_files
                        if name.startswith(prefix)
                    ]
                    if candidates:
                        candidates.sort()
                        return candidates[0]
                return ''
            
            updated_count = 0
            
            # Traverse all blocks
            for block in config.get('blocks', []):
                if block.get('blockType') == 'view':
                    block_id = block.get('id', '')
                    block_content = block.get('blockContent', {})
                    
                    # Check if python_code_name and html_code_name already exist
                    python_name = block_content.get('python_code_name', '')
                    html_name = block_content.get('html_code_name', '')
                    
                    # If fields missing, try extracting from layers
                    if not python_name:
                        layers = block_content.get('layers', [])
                        if layers and 'code_file' in layers[0]:
                            code_file = layers[0].get('code_file', '')
                            python_name = os.path.basename(code_file) if code_file else ''
                            html_name = html_name or infer_html_from_python(python_name)

                    if not python_name and html_name:
                        python_name = infer_python_from_html(html_name)

                    if not python_name and block_id:
                        python_name = infer_python_from_block_id(block_id)

                    if python_name and not html_name:
                        html_name = infer_html_from_python(python_name)
                    
                    # Verify file existence
                    if python_name and python_name in python_file_set:
                        # Update fields
                        block_content['python_code_name'] = python_name
                        if html_name:
                            block_content['html_code_name'] = html_name
                        
                        updated_count += 1
            
            # Save updated configuration
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Updated {updated_count} view blocks with python_code_name and html_code_name")
            
        except Exception as e:
            print(f"❌ Error updating config with HTML names: {str(e)}")
    
    def _reprocess_charts_after_beautify(self, charts_dest: str):
        """Apply standardization treatment to all charts again after beautification (in-place processing).
        
        Refers to the _reprocess_charts_after_beautify method in va_system_builder.py.
        
        - Uniformly hide series.label
        - Truncate data in series/xAxis to first 10 items
        - Keep grid.containLabel as True
        
        Args:
            charts_dest: Path to charts directory
        """
        try:
            if not os.path.exists(charts_dest):
                print(f"⚠️  Charts directory not found for reprocess: {charts_dest}")
                return
            
            for file in os.listdir(charts_dest):
                src_path = os.path.join(charts_dest, file)
                if os.path.isfile(src_path) and file.endswith('.html'):
                    # In-place processing: src and dst are the same
                    self._process_echart_html(src_path, src_path)
            
            print("✓ Reprocessed charts after beautify (labels hidden, data trimmed)")
        except Exception as e:
            print(f"❌ Error in _reprocess_charts_after_beautify: {e}")
