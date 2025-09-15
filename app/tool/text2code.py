from .base import BaseTool
from .python_execute import PythonExecute
from app.llm import LLM
from pydantic import Field, model_validator, ConfigDict
import re
import json
from typing import Dict, Any, Optional

_TEXT2CODE_DESCRIPTION = """
A tool to convert user's natural language question to Python code with intent analysis, data format detection, and execution capabilities.
"""


class Text2Code(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "text2code"
    description: str = _TEXT2CODE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The natural language question describing what python code should be generated.",
            }
        },
        "required": ["question"],
    }
    
    llm: LLM = Field(default_factory=LLM, description="The LLM to convert natural language question to Python code.")
    python_execute: PythonExecute = Field(default_factory=PythonExecute, description="The Python execution tool.")
    
    @model_validator(mode="after")
    def _initialize_text2code(self) -> "Text2Code":
        """Initialize the Text2Code tool with LLM and PythonExecute instances."""
        self.llm = LLM(config_name="default")
        self.python_execute = PythonExecute()
        return self
    
    async def analyze_intent(self, question: str) -> Dict[str, Any]:
        """
        Analyze the user's intent and requirements from the question.
        
        Args:
            question: Natural language question
            
        Returns:
            Dict containing intent analysis results
        """
        intent_prompt = f"""
Analyze the following user question and extract the intent, requirements, and data format information.

Question: {question}

Please analyze and provide:
1. Intent: What does the user want to accomplish?
2. Data format: What data format is mentioned or implied? (CSV, JSON, Excel, database, etc.)
3. Operations: What operations are needed? (read, process, analyze, visualize, etc.)
4. Output: What should be the expected output?
5. Dependencies: What Python libraries might be needed?

Output format:
<analysis>
{{
    "intent": "Brief description of what the user wants to accomplish",
    "data_format": "Detected or implied data format (CSV, JSON, Excel, etc.)",
    "operations": ["list", "of", "required", "operations"],
    "expected_output": "Description of expected output",
    "dependencies": ["pandas", "numpy", "matplotlib", "etc"],
    "complexity": "simple|medium|complex"
}}
</analysis>
        """
        
        response = await self.llm.ask([{"role": "user", "content": intent_prompt}])
        
        # Extract analysis from response
        analysis_match = re.search(r"<analysis>(.*?)</analysis>", response.content, re.DOTALL)
        if not analysis_match:
            # Fallback analysis
            return {
                "intent": "Generate Python code",
                "data_format": "unknown",
                "operations": ["process"],
                "expected_output": "Code execution result",
                "dependencies": [],
                "complexity": "medium"
            }
        
        try:
            analysis = json.loads(analysis_match.group(1).strip())
            return analysis
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "intent": "Generate Python code",
                "data_format": "unknown", 
                "operations": ["process"],
                "expected_output": "Code execution result",
                "dependencies": [],
                "complexity": "medium"
            }
    
    async def generate_enhanced_code_prompt(self, question: str, analysis: Dict[str, Any]) -> str:
        """
        Generate an enhanced prompt for Python code generation based on intent analysis.
        
        Args:
            question: Natural language question
            analysis: Intent analysis results
            
        Returns:
            Enhanced prompt for the LLM
        """
        data_format = analysis.get("data_format", "unknown")
        operations = analysis.get("operations", [])
        dependencies = analysis.get("dependencies", [])
        complexity = analysis.get("complexity", "medium")
        
        # Build data format specific guidance
        data_guidance = ""
        if data_format.lower() == "csv":
            data_guidance = """
- Use pandas.read_csv() to read CSV files
- Handle missing values appropriately
- Consider data types and encoding issues
"""
        elif data_format.lower() == "json":
            data_guidance = """
- Use json.load() or pandas.read_json() for JSON files
- Handle nested JSON structures properly
- Consider JSON schema validation if needed
"""
        elif data_format.lower() == "excel":
            data_guidance = """
- Use pandas.read_excel() for Excel files
- Specify sheet names if needed
- Handle multiple sheets appropriately
"""
        
        # Build operations guidance
        operations_guidance = ""
        if "visualize" in operations or "plot" in operations:
            operations_guidance += "- Use matplotlib or seaborn for visualization\n"
        if "analyze" in operations or "statistics" in operations:
            operations_guidance += "- Use pandas and numpy for data analysis\n"
        if "machine_learning" in operations or "ml" in operations:
            operations_guidance += "- Consider scikit-learn for ML tasks\n"
        
        prompt = f"""
You are an expert Python programmer. Convert the following natural language question into clean, efficient, and well-commented Python code.

Question: {question}

Intent Analysis:
- Intent: {analysis.get('intent', 'Generate Python code')}
- Data Format: {data_format}
- Operations: {', '.join(operations)}
- Expected Output: {analysis.get('expected_output', 'Code execution result')}
- Complexity: {complexity}

Data Format Guidance:
{data_guidance}

Operations Guidance:
{operations_guidance}

Requirements:
- Use appropriate Python libraries: {', '.join(dependencies) if dependencies else 'standard library'}
- Add proper error handling
- Include clear comments explaining the logic
- Make the code readable and maintainable
- Handle edge cases appropriately
- Follow Python best practices

Output format:
<think>
YOUR THINKING PROCESS HERE - analyze the requirements and plan the code structure
</think>
<code>
YOUR COMPLETED PYTHON CODE HERE
</code>
<explanation>
Brief explanation of what the code does and key features
</explanation>

Now, please convert the question to Python code, strictly follow the output format.
        """
        
        return prompt
    
    async def post_process_reflection(self, code: str, question: str, analysis: Dict[str, Any], execution_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Post-process reflection on the generated code and execution results.
        
        Args:
            code: Generated Python code
            question: Original question
            analysis: Intent analysis results
            execution_result: Optional execution results
            
        Returns:
            Dict containing reflection results
        """
        reflection_prompt = f"""
Reflect on the generated Python code and provide feedback on its quality and effectiveness.

Original Question: {question}
Generated Code:
{code}

Intent Analysis:
{json.dumps(analysis, indent=2)}

Execution Results:
{json.dumps(execution_result, indent=2) if execution_result else "Not executed"}

Please provide:
1. Code Quality Assessment
2. Potential Issues or Improvements
3. Suggestions for Optimization
4. Whether the code meets the original requirements

Output format:
<reflection>
{{
    "code_quality": "excellent|good|fair|poor",
    "meets_requirements": true|false,
    "potential_issues": ["list", "of", "issues"],
    "improvements": ["list", "of", "suggestions"],
    "optimization_tips": ["list", "of", "optimization", "suggestions"],
    "overall_assessment": "Brief overall assessment"
}}
</reflection>
        """
        
        response = await self.llm.ask([{"role": "user", "content": reflection_prompt}])
        
        # Extract reflection from response
        reflection_match = re.search(r"<reflection>(.*?)</reflection>", response.content, re.DOTALL)
        if not reflection_match:
            return {
                "code_quality": "good",
                "meets_requirements": True,
                "potential_issues": [],
                "improvements": [],
                "optimization_tips": [],
                "overall_assessment": "Code generated successfully"
            }
        
        try:
            reflection = json.loads(reflection_match.group(1).strip())
            return reflection
        except json.JSONDecodeError:
            return {
                "code_quality": "good",
                "meets_requirements": True,
                "potential_issues": [],
                "improvements": [],
                "optimization_tips": [],
                "overall_assessment": "Code generated successfully"
            }
    
    async def generate_code_prompt(self, question: str) -> str:
        """
        Generate a prompt for Python code generation based on the question.
        
        Args:
            question: Natural language question describing what Python code should be generated
            
        Returns:
            Formatted prompt for the LLM
        """
        prompt = f"""
You are a helpful assistant that converts natural language questions to Python code.

Here is the natural language question:
{question}

Output format:
<think>
YOUR THINKING HERE
</think>
<code>
YOUR COMPLETED PYTHON CODE HERE
</code>

Now, please convert the natural language question to Python code, strictly follow the output format.
        """
        
        return prompt
    
    async def execute(self, question: str, execute_code: bool = True, include_reflection: bool = True):
        """
        Convert natural language question to Python code with enhanced analysis and execution.
        
        Args:
            question: Natural language question describing what Python code should be generated
            execute_code: Whether to execute the generated code
            include_reflection: Whether to include post-processing reflection
            
        Returns:
            Dict containing generated code, analysis, execution results, and reflection
        """
        # Step 1: Intent Analysis
        analysis = await self.analyze_intent(question)
        
        # Step 2: Generate enhanced code prompt based on analysis
        prompt = await self.generate_enhanced_code_prompt(question, analysis)
        
        # Step 3: Get response from LLM
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        # Step 4: Extract code from response
        code_match = re.search(r"<code>(.*?)</code>", response.content, re.DOTALL)
        if not code_match:
            raise ValueError("Could not extract code from LLM response")
        
        code = code_match.group(1).strip()
        
        # Step 5: Extract explanation if available
        explanation_match = re.search(r"<explanation>(.*?)</explanation>", response.content, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided"
        
        # Step 6: Execute code if requested
        execution_result = None
        if execute_code:
            execution_result = await self.python_execute.execute(code)
        
        # Step 7: Post-process reflection if requested
        reflection = None
        if include_reflection:
            reflection = await self.post_process_reflection(code, question, analysis, execution_result)
        
        # Return code directly (like text2sql AI)
        return code
    


if __name__ == "__main__":
    import asyncio
    text2code = Text2Code()
    code = asyncio.run(text2code.execute("Create a function that calculates the factorial of a number"))
    print(code)
