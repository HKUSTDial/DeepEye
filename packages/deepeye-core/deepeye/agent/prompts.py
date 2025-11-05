"""Agent Prompt 模板

定义 Planner Agent 使用的 Prompt 模板。
"""

from typing import Any, Dict, List


def build_planner_prompt(
    task: str,
    available_tools: List[Any],  # List[ToolDescription]
) -> List[Dict[str, str]]:
    """构建规划器的 Prompt
    
    Args:
        task: 用户任务描述
        available_tools: 可用工具列表（ToolDescription 对象列表）
        
    Returns:
        消息列表（适用于 LLM API）
    """
    # 构建工具描述
    tools_description = _format_tools(available_tools)
    
    system_message = f"""# Task Description

You are an intelligent task planning assistant that decomposes natural language tasks into executable steps.

Your responsibilities:
1. Understand the user's task requirements
2. Select appropriate tools from available options
3. Generate a clear execution plan with steps, tools, inputs, and dependencies

# Available Tools

{tools_description}

# Instructions

1. **Analyze the Task**: Break down what the user wants to achieve
2. **Select Tools**: Choose the most appropriate tools from the list above
3. **Plan Steps**: Create a logical sequence of steps
4. **Define Inputs**: For each step, specify:
   - **Dynamic inputs**: Data flowing from previous steps
   - **Static inputs**: User-provided values / constants
5. **Set Dependencies**: Ensure proper execution order based on data flow
6. **Optimize**: Allow parallel execution for independent steps when possible

# Output Format

You MUST respond in the following JSON format ONLY (no additional text):

```json
{{
  "steps": [
    {{
      "step_id": 1,
      "tool": "ToolName",
      "description": "Brief description of what this step does",
      "connections": [
        {{
          "from_step": <previous_step_id>,
          "from_port": "output_port_name",
          "to_port": "input_port_name"
        }}
      ],
      "static_inputs": {{
        "input_port_name": {{
          "param1": "value1",
          "param2": "value2"
        }}
      }}
    }}
  ]
}}
```

# Format Specification

## Step Fields

- **step_id**: Integer starting from 1, incrementing sequentially
- **tool**: Exact tool name from the available tools list
- **description**: Clear description of the step's purpose
- **connections**: List of data flow connections from previous steps (dynamic inputs)
- **static_inputs**: Dictionary of static input values for each input port

## Connections (Dynamic Inputs)

Connections define how data flows from previous steps to the current step.

Each connection has three fields:
```json
{{
  "from_step": <previous_step_id>,
  "from_port": "output_port_name",
  "to_port": "input_port_name"
}}
```

- **from_step**: Integer ID of the previous step providing the data
- **from_port**: Output port name from the previous step (e.g., "data", "result")
- **to_port**: Input port name of the current step (e.g., "database", "query")

**Important**: 
- Port names must match exactly as specified in tool descriptions
- A step can have multiple connections if it needs data from multiple sources
- Connections automatically define step dependencies

## Static Inputs (User-provided Values)

Static inputs provide constant values or parameters that don't come from previous steps.

Structure:
```json
{{
  "input_port_name": {{
    "parameter_name1": "value1",
    "parameter_name2": "value2"
  }}
}}
```

- **Outer key**: Input port name (e.g., "query")
- **Inner keys**: Parameter names specific to that port
- **Values**: Actual parameter values (strings, numbers, lists, etc.)

**Important**: 
- Match port and parameter names exactly as specified in tool descriptions
- Each port can have multiple parameters
- Ensure all required parameters are provided either via connections or static_inputs

# Example

Task: "Query top 10 products by sales in 2024"

```json
{{
  "steps": [
    {{
      "step_id": 1,
      "tool": "DatabaseDataSource",
      "description": "Connect to database and retrieve schema information",
      "connections": [],
      "static_inputs": {{}}
    }},
    {{
      "step_id": 2,
      "tool": "NL2SQL",
      "description": "Generate and execute SQL query for sales analysis",
      "connections": [
        {{
          "from_step": 1,
          "from_port": "data",
          "to_port": "database"
        }}
      ],
      "static_inputs": {{
        "query": {{
          "text": "Query top 10 products by sales amount in 2024"
        }}
      }}
    }},
    {{
      "step_id": 3,
      "tool": "OutputNode",
      "description": "Format and return results to user",
      "connections": [
        {{
          "from_step": 2,
          "from_port": "data",
          "to_port": "data"
        }}
      ],
      "static_inputs": {{}}
    }}
  ]
}}
```

# Important Notes

- Use ONLY tools from the available tools list
- Connections automatically define step dependencies
- Ensure there are no circular dependencies in connections
- Match all port names exactly as defined in tool descriptions
- Static inputs structure: outer key = port name, inner keys = parameter names
- If a tool doesn't have  you can omit it or use empty connections/static_inputs
"""
    
    user_message = f"""# Input

**User Task:**
{task}

# Now Generate Execution Plan

Please analyze the task and generate a complete execution plan following the exact JSON format specified above."""
    
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]


def _format_tools(tools: List[Any]) -> str:
    """格式化工具列表为可读文本
    
    Args:
        tools: 工具列表（ToolDescription 对象列表）
        
    Returns:
        格式化后的工具描述
    """
    if not tools:
        return "（暂无可用工具）"
    
    lines = []
    for i, tool in enumerate(tools, 1):
        # 构建工具描述
        tool_desc = [f"{i}. **{tool.name}**"]
        tool_desc.append(f"   Description: {tool.description}")
        
        # 输入端口
        if tool.input_ports:
            tool_desc.append("   Input Ports:")
            for port in tool.input_ports:
                required_mark = " (required)" if port.required else ""
                tool_desc.append(f"     - {port.name}{required_mark}: {port.label}")
                if port.parameters:
                    tool_desc.append("       Parameters:")
                    for param in port.parameters:
                        req = " (required)" if param.required else ""
                        default_str = f", default={param.default}" if param.default is not None else ""
                        tool_desc.append(f"         • {param.name}: {param.type}{req}{default_str}")
                        if param.description:
                            tool_desc.append(f"           {param.description}")
        
        # 输出端口
        if tool.output_ports:
            tool_desc.append("   Output Ports:")
            for port in tool.output_ports:
                tool_desc.append(f"     - {port.name}: {port.label}")
                if port.parameters:
                    tool_desc.append("       Parameters:")
                    for param in port.parameters:
                        tool_desc.append(f"         • {param.name}: {param.type}")
                        if param.description:
                            tool_desc.append(f"           {param.description}")
        
        lines.append("\n".join(tool_desc))
    
    return "\n\n".join(lines)


def build_reflection_prompt(
    task: str,
    plan: Dict[str, Any],
    execution_result: Dict[str, Any],
) -> List[Dict[str, str]]:
    """构建反思阶段的 Prompt
    
    用于让 Agent 评估任务是否成功完成，以及是否需要调整。
    
    Args:
        task: 原始任务
        plan: 执行计划
        execution_result: 执行结果
        
    Returns:
        消息列表
    """
    system_message = """# Task Description

You are a task evaluation assistant responsible for assessing whether task execution results meet user requirements.

Your responsibilities:
1. Analyze the original task requirements
2. Review the execution plan for reasonableness
3. Evaluate whether execution results meet expectations
4. Determine if the task was successfully completed

# Instructions

1. **Understand Requirements**: Carefully read the original task to understand what the user wanted
2. **Analyze Plan**: Check if the execution plan was appropriate for the task
3. **Evaluate Results**: 
   - Did the execution complete successfully?
   - Are there any errors or issues?
   - Does the output match expectations?
4. **Make Judgment**: Determine overall success status
5. **Provide Feedback**: Suggest improvements if needed

# Output Format

You MUST respond in the following JSON format ONLY:

```json
{
  "success": true/false,
  "reasoning": "Detailed explanation of your evaluation",
  "suggestions": [
    "Improvement suggestion 1",
    "Improvement suggestion 2"
  ],
  "next_action": "continue" | "retry" | "replan" | "complete"
}
```

## Field Descriptions

- **success**: Boolean indicating if the task was completed successfully
- **reasoning**: Clear explanation of why you made this judgment
- **suggestions**: List of concrete improvement suggestions (empty if task succeeded)
- **next_action**: Recommended next action:
  - `"complete"`: Task finished successfully, no further action needed
  - `"continue"`: Partial success, continue with remaining steps
  - `"retry"`: Minor issues, retry current step with adjustments
  - `"replan"`: Major issues, need to regenerate the plan

# Evaluation Criteria

## Success Indicators ✓
- Execution completed without errors
- Output data is present and valid
- Results match the task requirements
- All necessary steps were executed

## Failure Indicators ✗
- Execution errors occurred
- Missing or invalid output
- Results don't address the task
- Plan was incomplete or incorrect
"""
    
    user_message = f"""# Input

## Original Task
{task}

## Execution Plan
{_format_plan(plan)}

## Execution Result
{_format_execution_result(execution_result)}

# Now Evaluate

Please evaluate the task execution and provide your assessment in the JSON format specified above."""
    
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]


def _format_execution_result(result: Dict[str, Any]) -> str:
    """格式化执行结果
    
    Args:
        result: 执行结果字典
        
    Returns:
        格式化后的文本
    """
    success = result.get("success", False)
    status = "成功" if success else "失败"
    
    lines = [f"状态: {status}"]
    
    if "error" in result:
        lines.append(f"错误: {result['error']}")
    
    if "outputs" in result:
        lines.append("输出:")
        outputs = result["outputs"]
        for key, value in outputs.items():
            lines.append(f"  - {key}: {value}")
    
    return "\n".join(lines)


# 预定义的常用 Prompt 片段
PROMPT_FRAGMENTS = {
    "think_step_by_step": "让我们一步步思考。",
    "be_precise": "请准确理解任务需求，确保生成的计划能够完成任务。",
    "consider_dependencies": "注意步骤之间的依赖关系，合理安排执行顺序。",
    "use_appropriate_tools": "选择最合适的工具来完成每个步骤。",
}

