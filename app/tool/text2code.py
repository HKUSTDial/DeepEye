from .base import BaseTool
from .python_execute import PythonExecute
from app.llm import LLM
from pydantic import Field, model_validator, ConfigDict
import re
import json
from typing import Dict, Any

_TEXT2CODE_DESCRIPTION = """
Generate Python code from natural language descriptions. 
This is the primary tool for creating Python functions, scripts, and programs based on user requirements. 
It analyzes intent, detects data formats, and generates executable code.
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

Guidelines:
- If no specific data format is mentioned, use 'not_specified'
- Be specific about operations (e.g., 'data_analysis', 'visualization', 'file_processing')
- Consider both standard library and third-party packages

Output format:
<analysis>
{{
    "intent": "Brief description of what the user wants to accomplish",
    "data_format": "Detected data format (CSV, JSON, Excel, etc.) or 'not_specified' if no specific format mentioned",
    "operations": ["data_analysis", "file_processing", "visualization"],
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
                "data_format": "not_specified",
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
                "data_format": "not_specified", 
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
        data_format = analysis.get("data_format", "not_specified")
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
        elif data_format.lower() == "not_specified":
            data_guidance = """
- No specific data format requirements detected
- Use appropriate data structures based on the task
- Consider using standard Python data types (list, dict, etc.)
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

Now, please convert the question to Python code, strictly follow the output format.
        """
        
        return prompt
    
    
    async def execute(self, question: str, execute_code: bool = True):
        """
        Convert natural language question to Python code with enhanced analysis and execution.
        
        Args:
            question: Natural language question describing what Python code should be generated
            execute_code: Whether to execute the generated code
            
        Returns:
            Dict containing generated code and execution results
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
        
        # Step 5: Execute code if requested
        execution_result = None
        if execute_code:
            execution_result = await self.python_execute.execute(code)
        
        # Return JSON with code and execution result
        return {
            "code": code,
            "execution_result": execution_result
        }
    


if __name__ == "__main__":
    import asyncio
    text2code = Text2Code()
    result = asyncio.run(text2code.execute("Create a function that calculates the factorial of a number"))
    print("Generated Code:")
    print(result["code"])
    print("\nExecution Result:")
    print(result["execution_result"])
