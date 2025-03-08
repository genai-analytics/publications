from langgraph_distributed_calculator import LanggraphDistributedCalculator
from langchain_LLM_calculator import LangchainLLMCalculator
from base_calculator import BaseCalculator
from typing import TypedDict, Any, Optional
import random
import os, re, sys, io
from textwrap import dedent
import logging
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from textwrap import dedent
from agent_analytics.instrumentation import agent_analytics_sdk
# agent_analytics_sdk.initialize_logging(logs_dir_path='/Users/hadarmulian/PycharmProjects/agent-analytics/2025-kdd-paper/experiments_output/2025-02-18_13-19-54_test_no_nl_50x3_18022025_10_ops_2pare_w_curly/',
#             log_filename='testingggg')
from pydantic import BaseModel
from agent_analytics.instrumentation.utils import record_metric_in_span
class metricRecorder(BaseModel):
    type: str = "failure"
    name: str = None
    value: str = None
    message: str = None 
# Agent Analytics instrumentation

# agent_analytics_sdk.initialize_logging()


class LanggraphLLMCalculator(LanggraphDistributedCalculator):
    def __init__(
        self,
        default_llm: BaseChatModel,  # Required parameter for LLM-based calculators.
        calculators: list = None,
        min_delay_msec: int = 0,
        max_delay_msec: int = 0,
        addition_calculator: BaseCalculator = None,
        subtraction_calculator: BaseCalculator = None,
        multiplication_calculator: BaseCalculator = None,
        division_calculator: BaseCalculator = None,
        parentheses_calculator: BaseCalculator = None,
        curly_brackets_calculator: BaseCalculator = None,
        square_brackets_calculator: BaseCalculator = None,  # Optional; default remains None.
    ):


        # Avoid mutable default arguments
        if calculators is None:
            calculators = []
        
        # Set default calculators using default_llm when not provided.
        if addition_calculator is None:
            addition_calculator = LangchainLLMCalculator(default_llm)
        if subtraction_calculator is None:
            subtraction_calculator = LangchainLLMCalculator(default_llm)
        if curly_brackets_calculator is None:
            # Notice the different max_num_of_attempts value for curly_brackets_calculator.
            curly_brackets_calculator = LangchainLLMCalculator(default_llm, validate_expression=True, validate_result=True, max_num_of_attempts=2)
        
        # Call the superclass initializer with matching parameters.
        super().__init__(
            calculators=calculators,
            min_delay_msec=min_delay_msec,
            max_delay_msec=max_delay_msec,
            addition_calculator=addition_calculator,
            subtraction_calculator=subtraction_calculator,
            multiplication_calculator=multiplication_calculator,
            division_calculator=division_calculator,
            parentheses_calculator=parentheses_calculator,
            square_brackets_calculator=square_brackets_calculator,
            curly_brackets_calculator=curly_brackets_calculator,
        )
        
        # Set LanggraphLLMCalculator-specific attributes.
        self.default_llm = default_llm

    def is_valid_expression(self, expression: str) -> bool:
        # Replace every curly bracket block (and its content) with a random number.
        new_expr = ""
        i = 0
        n = len(expression)
        while i < n:
            if expression[i] == "{":
                curly_count = 1
                i += 1
                while i < n and curly_count > 0:
                    if expression[i] == "{":
                        curly_count += 1
                    elif expression[i] == "}":
                        curly_count -= 1
                    i += 1
                # Replace the entire curly bracket block with a random number between 1 and 1000.
                new_expr += str(random.randint(1, 1000))
            else:
                new_expr += expression[i]
                i += 1

        # Replace every variable reference starting with 'E', with a random number between 1 and 1000.
        def replace_e(match):
            return str(random.randint(1, 1000))

        new_expr = re.sub(r"E\d*", replace_e, new_expr)

        converted_expression = self.covert_brackets_to_parentheses(new_expr)
        try:
            eval(converted_expression, {"__builtins__": None}, {})
            return True
        except Exception as e:
            logging.error(
                f"LanggraphLLMCalculator - Failed to validate {expression}, delegating to parent calculator. Exception: {e}"
            )
            metric = metricRecorder(
                type="failure",
                name="invalid_expression",
                value="global_failure",
                message=f"LanggraphLLMCalculator - Failed to validate {expression}, delegating to parent calculator. Exception: {e}"
            )
            record_metric_in_span(metric)


        return super().is_valid_expression(expression)

    def is_simple_arithmetic_expression(self, expression: str) -> bool:
        """
        Validates that the expression contains only:
        - numeric values (integers or decimals, including formats like .2, 0.34),
        - references of the form E<digits> (e.g., E0, E12),
        - arithmetic operators (+, -, *, /),
        - optional whitespace,
        and NOTHING else (no brackets, no random text).

        Examples of valid numbers under the current pattern:
        123, 0.34, .2, 5.0, .56

        """
        pattern = r"^(?:(?:\d+(?:\.\d+)?|\.\d+)|E\d+|[+\-*/]|\s)+$"

        return bool(re.match(pattern, expression.strip()))

    def add_bad_examples(
        self, base_prompt: str, input_expression: str, bad_examples: list
    ) -> str:
        """
        Dynamically build the system prompt for the first LLM call.
        """
        if not bad_examples:
            return base_prompt

        # Convert bad examples into a readable string
        bad_examples_string = f"\nBelow is a list of INCORRECT new_expressions for the input expression: {input_expression}.\nBAD EXAMPLES are:\n{bad_examples}\n"

        return base_prompt + bad_examples_string.replace("{", "{{").replace("}", "}}")

    def extract_upper_level_brackets(self, expression):
        preprocessed_operations = []
        preprocessed_expression = expression

        SYSTEM_PROMPT = """
            You are an expert mathematician. Your task is to analyze a given mathematical expression and identify **only the top-level** bracketed segments. The expression may include pre-existing variable references of the form E0, E1, etc., representing sub-expressions that have already been calculated.

            **Bracket Types and Rules:**
            1. **Brackets:**
            - Parentheses: `( ... )`
            - Square Brackets: `[ ... ]`
            - Curly Brackets: `{{ ... }}`
            2. Treat square brackets `[]` and curly brackets `{{}}` as equivalent to parentheses `()` for grouping and preserving the order of operations.
            3. Do not interchange, omit, or remove any type of bracket. Each bracket type must be used consistently for its intended purpose.
            4. Format all mathematical expressions with clear and consistent grouping, using the same type of bracket for each nesting level.

            **Processing Instructions:**
            - **Identification:** Scan the input expression and extract every **top-level** bracketed segment. Ignore any brackets nested inside these segments; they should remain intact as part of the content.
            - **New Operation Creation:** For each top-level bracket found, create a new operation entry with the following properties:
            - `"operation"`: One of `"parentheses"`, `"square_brackets"`, or `"curly_brackets"`, depending on the type of the bracket.
            - `"name"`: A unique variable identifier in the format `E{{n}}`. **Important:** If the input expression already contains variable references (e.g., `E0`, `E1`, etc.), then the index `n` for any new operation must be strictly greater than the highest index already present. For example, if the expression contains `E0` and `E1`, the first new operation must be named `E2`.
            - `"op1"`: The exact content inside the top-level brackets (do not alter or decompose it, even if it contains nested brackets).
            - `"op2"`: An empty string `""`.
            - **Expression Replacement:** Replace each top-level bracketed segment in the original expression with its corresponding variable name (e.g., `E0`, `E1`, etc.) to form a new expression.
            - **Final Expression Requirements:** The final `"new_expression"` must not contain any parentheses, square brackets, or curly brackets. It should include only:
            - Numeric values (e.g., `2`, `10`, `3.5`)
            - Standard arithmetic operators (`+`, `-`, `*`, `/`)
            - References to sub-expressions (e.g., `E0`, `E1`, etc.)

            **Output Format:**
            Return the result as a JSON object with the following structure:
            {{
            "operations": [
                {{
                "name": "string",
                "operation": "parentheses | square_brackets | curly_brackets",
                "op1": "string with bracket content",
                "op2": ""
                }},
                ...
            ],
            "new_expression": "string with bracket references replaced by E0, E1, etc."
            }}

            ---

            ### Example Inputs and Expected Outputs

            1) Example Input:
            (5 + {{one plus two}}+[6+7]-(9*4)) - 2

            Example Output:
            {{
                "operations": [
                {{
                    "name": "E0",
                    "operation": "parentheses",
                    "op1": "5 + {{one plus two}}+[6+7]-(9*4)",
                    "op2": ""
                }}
                ],
                "new_expression": "E0 - 2"
            }}

            2) Example Input:
            {{some text}} + (3+4)

            Example Output:
            {{
                "operations": [
                {{
                    "name": "E0",
                    "operation": "curly_brackets",
                    "op1": "some text",
                    "op2": ""
                }},
                {{
                    "name": "E1",
                    "operation": "parentheses",
                    "op1": "3+4",
                    "op2": ""
                }}
                ],
                "new_expression": "E0 + E1"
            }}

            3) Example Input:
            [E1 - (E2 - 3)] * 2

            (Here, [E1 - (E2 - 3)] is the only top-level bracket. The nested parentheses (8 - 3)
                is not decomposed because it is inside the top-level square brackets.)

            Example Output:
            {{
                "operations": [
                {{
                    "name": "E3",
                    "operation": "square_brackets",
                    "op1": "E1 - (E2 - 3)",
                    "op2": ""
                }}
                ],
                "new_expression": "E3 * 2"
            }}

            4) Example Input:
            (E0*{{two + one}}+1) - 2

            Example Output:
            {{
                "operations": [
                {{
                    "name": "E1",
                    "operation": "parentheses",
                    "op1": "E0*{{two + one}}+1",
                    "op2": ""
                }}
                ],
                "new_expression": "E1 - 2"
            }}
        """

        # JSON schema for the LLM call
        # We expect two outcomes:
        #   "operations" (list of bracket operations) and
        #   "new_expression" (the top-level expression with bracket references).
        extract_upper_level_brackets_schema = {
            "title": "extract_upper_level_brackets",
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "operation": {
                                "type": "string",
                                "enum": [
                                    "parentheses",
                                    "square_brackets",
                                    "curly_brackets",
                                ],
                            },
                            "op1": {"type": "string"},
                            "op2": {"type": "string"},
                        },
                        "required": ["name", "operation", "op1", "op2"],
                        "additionalProperties": False,
                    },
                },
                "new_expression": {"type": "string"},
            },
            "required": ["operations", "new_expression"],
            "additionalProperties": False,
        }

        # We'll store "bad examples" of the output from prior failed attempts
        bad_examples = []
        extract_parentheses = False
        extract_square_brackets = False
        extract_curly_brackets = False
        for attempt in range(1, 4):
            # On second attempt try to extract all upper level brackets by LLM
            if attempt > 1:
                # On second attempt extract curl upper level brackets programmatically
                extract_curly_brackets = True
                if attempt > 2:
                    # On third attempt extract curl and square upper level brackets programmatically
                    extract_square_brackets = True

                # specific_upper_level_brackets_result = (
                #     self.extract_specific_upper_level_brackets(
                #         expression=expression,
                #         extract_parentheses=extract_parentheses,
                #         extract_square_brackets=extract_square_brackets,
                #         extract_curly_brackets=extract_curly_brackets,
                #     )
                # )
                specific_upper_level_brackets_result = (
                    self.extract_specific_upper_level_brackets(
                        expression=expression,
                        extract_parentheses=False,
                        extract_square_brackets=False,
                        extract_curly_brackets=True,
                    )
                )
                preprocessed_operations = specific_upper_level_brackets_result[
                    "operations"
                ]
                preprocessed_expression = specific_upper_level_brackets_result[
                    "updated_expression"
                ]

            # Build a system prompt that includes any previously failed outputs
            current_prompt_str = self.add_bad_examples(
                SYSTEM_PROMPT, preprocessed_expression, bad_examples
            )

            # Create the prompt for the bracket-extraction call
            prompt = ChatPromptTemplate.from_messages(
                [("system", current_prompt_str), ("user", "{input}")]
            )
            bracket_extractor = prompt | self.default_llm.with_structured_output(
                extract_upper_level_brackets_schema
            )

            # Attempt the LLM call
            try:
                result = bracket_extractor.invoke({"input": preprocessed_expression})
            except Exception as e:
                # If there's a hard failure in the call, store the error as a "bad example"
                logging.warning(
                    f"LLM Failed to extract upper level brackets for {preprocessed_expression}, Exception: {e}"
                )
                metric = metricRecorder(
                    type="failure",
                    name="decomposition_llm_eval",
                    value="local_failure",
                    message=f"LLM Failed to extract upper level brackets for {preprocessed_expression}, Exception: {e}"
                    )
                record_metric_in_span(metric)
                continue

            # Validate the structure
            if "operations" not in result or "new_expression" not in result:
                # This is an invalid structure
                logging.warning(
                    f"LLM Failed to extract upper level brackets for {preprocessed_expression}, Missing output parameters in result: {result}"
                )
                continue

            new_expression = result["new_expression"]
            # Check if new_expression is valid
            if self.is_simple_arithmetic_expression(new_expression):
                return {
                    "operations": preprocessed_operations + result["operations"],
                    "updated_expression": new_expression,
                }
            else:
                logging.warning(
                    f"LLM attempt:{attempt} failed to extract upper level brackets for {preprocessed_expression}, Generated expression is incorrect: {new_expression}"
                )
                        # print("DECOMPOSITION FAILURE REGISTERED")
                metric = metricRecorder(
                    type="failure",
                    name="decomposition_llm_eval",
                    value="local_failure",
                    message=f"LLM attempt:{attempt} failed to extract upper level brackets for {preprocessed_expression}, Generated expression is incorrect: {new_expression}"
                )
                record_metric_in_span(metric)


                bad_examples += result["new_expression"]

        logging.error(
            f"LLM Failed to extract upper level brackets for {preprocessed_expression}, after {self.max_brackets_extraction_attempts} attempts. Will extract them programmatically"
        )
        # Extract all brackets programmatically
        metric = metricRecorder(
            type="failure",
            name="decomposition_llm_eval",
            value="local_failure",
            message=f"LLM Failed to extract upper level brackets for {preprocessed_expression}, after {self.max_brackets_extraction_attempts} attempts. Will extract them programmatically"
        )
        record_metric_in_span(metric)

        return super().extract_upper_level_brackets(expression)

    def are_operations_names_valid(self, operations):
        """
        Checks if all operations have unique names and that each name
        follows the pattern 'E{n}' where n is one or more digits.
        """
        pattern = re.compile(r"^E\d+$")
        seen_names = set()
        for operation in operations:
            name = operation.get("name")
            if name is None or not pattern.fullmatch(name) or name in seen_names:
                return False
            seen_names.add(name)
        return True

    def extract_arithmetic_operations(self, operations, expression):
        SYSTEM_PROMPT = """
            You are an expert mathematician. Now you will receive an expression
            that may contain references like E0, E1, etc. (which represent bracketed
            sub-expressions from a previous step). Your task is to decompose this
            expression into the top-level mathematical operations (multiplication,
            division, addition, subtraction), in that order of precedence (left to right
            for those with equal precedence).

            Instructions:
            - Treat any reference (E0, E1, etc.) as a single operand that must not
                be decomposed further.
            - Only decompose the expression for multiplication, division, addition,
                subtraction at the top level, respecting standard math precedence.
            - For each operation, produce a JSON object:
                {{
                    "name": "string",  // e.g., E2, E3, ...
                    "operation": "multiplication | division | addition | subtraction",
                    "op1": "number or reference to E#",
                    "op2": "number or reference to E#"
                }}
            - Ensure that the generated names are unique and do not conflict with any existing references in the input. Each new operation name must be greater than the highest reference number already present in the expression.
            
            Return your result as:
            {{
            "operations": [
                {{
                "name": "string",
                "operation": "multiplication | division | addition | subtraction",
                "op1": "...",
                "op2": "..."
                }}, ...
            ]
            }}
        """

        extract_arithmetic_operations_schema = {
            "title": "extract_arithmetic_operations",
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "A variable name assigned to the operation (e.g., E0, E1).",
                            },
                            "operation": {
                                "type": "string",
                                "enum": [
                                    "multiplication",
                                    "division",
                                    "addition",
                                    "subtraction",
                                ],
                                "description": "The type of operation to be performed.",
                            },
                            "op1": {
                                "oneOf": [
                                    {
                                        "type": "number",
                                        "description": "The first operand, a numerical value.",
                                    },
                                    {
                                        "type": "string",
                                        "description": "A reference to another variable (e.g., E0, E1) or a numeric string.",
                                    },
                                ]
                            },
                            "op2": {
                                "oneOf": [
                                    {
                                        "type": "number",
                                        "description": "The second operand, a numerical value.",
                                    },
                                    {
                                        "type": "string",
                                        "description": "A reference to another variable (e.g., E0, E1) or a numeric string.",
                                    },
                                ]
                            },
                        },
                        "required": ["name", "operation", "op1", "op2"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["operations"],
            "additionalProperties": False,
        }

        # Build the second prompt
        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT), ("user", "{input}")]
        )

        operation_decomposer = prompt | self.default_llm.with_structured_output(
            extract_arithmetic_operations_schema
        )
        try:
            # Invoke the LLM to Extract the arithmetic operations
            second_result = operation_decomposer.invoke({"input": expression})

            basic_math_ops = second_result["operations"]
            final_operations = operations + basic_math_ops
            if self.are_operations_names_valid(final_operations):
                return final_operations
            else:
                logging.error(
                    f"Failed to extract arithmetic operations from {expression}. Invalid operations names."
                )
                metric = metricRecorder(
                    type="failure",
                    name="decomposition_llm_eval",
                    value="local_failure",
                    message=f"Failed to extract arithmetic operations from {expression}. Invalid operations names."
                    )
                record_metric_in_span(metric)

        except Exception as e:
            logging.error(
                f"Failed to extract arithmetic operations from {expression}. Exception:\n{e}"
            )
                    # print("DECOMPOSITION FAILURE REGISTERED")
            metric = metricRecorder(
                type="failure",
                name="decomposition_llm_eval",
                value="local_failure",
                message=f"Failed to extract arithmetic operations from {expression}. Exception:\n{e}"
            )
            record_metric_in_span(metric)


        # Extract arithmetic operations programattically
        return super().extract_arithmetic_operations(operations, expression)

    def is_valid_result(self, expression, result):
        # This function scans the input expression for top-level curly bracket groups,
        # replaces each group with the corresponding numeric result recalculated by LLM based calculator
        # Send the modified expression to parrent method
        result_parts = []
        last_index = 0
        level = 0
        group_start = None
        validation_calculator = LangchainLLMCalculator(
            self.default_llm,validate_result=True, max_num_of_attempts=2
        )
        for i, ch in enumerate(expression):
            if ch == "{":
                if level == 0:
                    result_parts.append(expression[last_index:i])
                    group_start = i
                level += 1
            elif ch == "}":
                if level == 0:
                    return super().is_valid_result(expression, result)
                level -= 1
                if level == 0:
                    group_content = expression[group_start + 1 : i]
                    calc_val = validation_calculator.calculate_expression(group_content)
                    if calc_val is None:
                        return super().is_valid_result(expression, result)
                    result_parts.append(str(calc_val))
                    last_index = i + 1

        if level != 0:
            return super().is_valid_result(expression, result)

        result_parts.append(expression[last_index:])
        new_expression = "".join(result_parts)
        return super().is_valid_result(new_expression, result)


def initialize_logging(log_path=""):
    from agent_analytics.instrumentation import agent_analytics_sdk
    if log_path:
        logs_dir_path, log_filename = os.path.split(log_path)
        suppress_output(
            agent_analytics_sdk.initialize_logging,
            logs_dir_path=logs_dir_path,
            log_filename=log_filename,
        )
    else:
        suppress_output(agent_analytics_sdk.initialize_logging)


def suppress_output(func, *args, **kwargs):

    original_stdout = sys.stdout
    sys.stdout = io.StringIO()  # Redirect stdout to null
    try:
        return func(*args, **kwargs)
    finally:
        sys.stdout = original_stdout


