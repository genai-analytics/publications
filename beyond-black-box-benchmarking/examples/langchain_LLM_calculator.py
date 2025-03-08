import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from textwrap import dedent
from delegating_calculator import DelegatingCalculator

from pydantic import BaseModel
from agent_analytics.instrumentation.utils import record_metric_in_span
class metricRecorder(BaseModel):
    type: str = "failure"
    name: str = None
    value: str = None
    message: str = None 



class LangchainLLMCalculator(DelegatingCalculator):
    """
    LangchainLLMCalculator attempts to evaluate expressions using a single call to LLM provide using langchain inference APIs.
    If evaluation fails, it delegates the calculation to the list of provided calculators.
    """

    def __init__(
        self,
        expression_calculation_llm: BaseChatModel,
        result_validation_llm: BaseChatModel = None,
        expression_validation_llm=None,
        validate_expression=False,
        validate_result=False,
        max_num_of_attempts=1,
        calculators=[],
    ):
        super().__init__(calculators)
        if expression_calculation_llm is None:
            logging.critical(
                f"LangchainLLMCalculator - LLM for expression calculation is not provided"
            )
        self.expression_calculation_llm = expression_calculation_llm
        self.expression_validation_llm = (
            expression_validation_llm
            if expression_validation_llm is not None
            else expression_calculation_llm
        )
        self.result_validation_llm = (
            result_validation_llm
            if result_validation_llm is not None
            else expression_calculation_llm
        )
        self.validate_expression = validate_expression
        self.validate_result = validate_result
        self.max_num_of_attempts = max_num_of_attempts

    def calculate_expression(self, expression: str) -> float:
        if self.validate_expression and not self.is_valid_expression(expression):
            logging.warning(
                f"LangchainLLMCalculator - Expression: {expression} is not valid, delegating to next calculator"
            )
            return super().calculate_expression(expression)

        SYSTEM_PROMPT = """
            You are a helpful AI mathematician designed to solve a wide variety of mathematical problems efficiently. You will be provided with textual math questions that may include numbers, words, or a combination of both. Your goal is to interpret the question accurately, translate it into proper mathematical expressions, perform the necessary calculations, and output only the final numeric result.

            ### Key Guidelines:
            1. **Parse Precisely**: Identify and interpret mathematical operations accurately, including:
            - Addition (e.g., "5 plus 3")
            - Subtraction (e.g., "10 minus 4")
            - Multiplication (e.g., "4 times two")
            - Division (e.g., "divide 144 by 12")
            - Other operations like percentages, square roots, or ratios as specified.
            2. **Handle Verbal Descriptions**: Convert natural language descriptions into mathematical expressions (e.g., "four times three" becomes `4 * 3`).
            3. **Step-by-Step Understanding**: For multi-step problems, break them down logically, solve them internally, and output only the final numeric result.
            4. **Output Format**: Always provide the answer as a single numerical value (e.g., `8`, `144.5`, `3.14159`).

            ### Example Questions and Expected Behavior:
            1. "What is the sum of 15, 20, and 35?" → `70`
            2. "Find the average of 5, 12, 18, and 25." → `15`
            3. "Multiply 6 by 7, then add 14." → `56 + 14 = 70`
            4. "Divide 144 by 12." → `12`
            5. "What is 30% of 200?" → `60`
            6. "Find the square root of 121." → `11`
            7. "If the older son is twice as old as the younger son and their combined age is 9, what is the age of the older son?" → `6`
            8. "4 times two" → `8`
            9. "5 plus 3" → `8`
            10. "A car travels 60 miles per hour for 3 hours. How far did it travel in total?" → `180`

            ### Notes:
            - Ensure mathematical expressions are parsed correctly, even if the input uses words instead of symbols (e.g., "times" for multiplication, "plus" for addition).
            - Think step by step to address complex problems
            - Avoid additional explanations or formatting; return only the numeric answer.
            - If an input is unclear or invalid, respond with rusult value of null. 

            ### Additional Instructions:
            - Pay attention to the context of numbers written as words (e.g., "two" is `2`, "fourteen" is `14`).
            - Prioritize accurate calculations and proper numeric conversions in all cases.
        """
        expression_calculation_respose = {
            "title": "expression_calculation_respose",
            "type": "object",
            "properties": {"result": {"type": "number"}},
            "required": ["result"],
            "additionalProperties": False,
        }

        prompt = ChatPromptTemplate.from_messages(
            [("system", dedent(SYSTEM_PROMPT)), ("user", "{input}")]
        )
        chat_model = prompt | self.expression_calculation_llm.with_structured_output(
            expression_calculation_respose
        )
        result = None
        for attempt in range(0, self.max_num_of_attempts):
            try:
                response = chat_model.invoke(
                    {
                        "input": f"Calculate result for the following problem:\n{expression}"
                    }
                )
                result = response["result"]
                if result is not None:
                    if self.validate_result and not self.is_valid_result(
                        expression, result
                    ):
                        logging.warning(
                            f"LangchainLLMCalculator - Attempt:{attempt}: The result:{result} is not vlaid for expression: {expression}, delegating to next calculator"
                        )
                        continue
                    return float(result)
                logging.warning(
                    f"LangchainLLMCalculator - Attempt:{attempt}: Evaluation of {expression} retuned None, delegating to next calculator"
                )
            except Exception as e:
                logging.warning(
                    f"LangchainLLMCalculator - Attempt:{attempt}: Failed to evaluate {expression}, delegating to next calculator"
                )
        return result
        # return super().calculate_expression(expression)

    def is_valid_expression(self, expression: str) -> bool:
        SYSTEM_PROMPT = """
            You are given a textual problem or expression. Your task is to determine whether it is expected to produce exactly one numerical outcome and return a structured JSON output.

            ### Rules for Classification:  
            1. If the expression involves a mathematical operation, a measurement, or a function that evaluates to a single number, classify it as valid.  
            - Examples:  
                - "5 + two" → Valid  
                - "maximum of three and five" → Valid  
                - "What is the distance from A to B?" → Valid  

            2. If the expression asks for something non-numerical (e.g., names, colors, descriptions), classify it as invalid.  
            - Examples:  
                - "What is the color of the sky?" → Invalid  
                - "What is the name of the capital of France?" → Invalid  

            3. If the expression asks for multiple numbers instead of a single one (e.g., a range, a set, a list), classify it as invalid.  
            - Examples:  
                - "What are the maximum and minimum in the following sequence?" → Invalid  
                - "List the prime numbers between 1 and 10" → Invalid  

            4. If the question is open-ended, subjective, or procedural, classify it as invalid.  
            - Examples:  
                - "How do I calculate the area of a circle?" → Invalid  
                - "Are all numbers divisible by 2 even?" → Invalid  

            ### Output Format:  
            Return a JSON object with the following structure:  
            {{
            "result": "valid" | "invalid"
            }}

        """

        expression_validation_respose = {
            "title": "expression_validation_respose",
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "enum": [
                        "Valid",
                        "Invalid",
                    ],
                }
            },
            "required": ["result"],
            "additionalProperties": False,
        }

        prompt = ChatPromptTemplate.from_messages(
            [("system", dedent(SYSTEM_PROMPT)), ("user", "{input}")]
        )
        chat_model = prompt | self.expression_validation_llm.with_structured_output(
            expression_validation_respose
        )
        try:
            response = chat_model.invoke(
                {"input": f"Validate the following expression:\n{expression}"}
            )
            result = response["result"]
            if result == "Valid":
                return True
            logging.warning(
                f"LangchainLLMCalculator - The following expression {expression} is not expected to return a single numerical value"
            )
            metric = metricRecorder(
                type="failure",
                name="invalid_expression",
                value="global_failure",
                message=f"LangchainLLMCalculator - The following expression {expression} is not expected to return a single numerical value"
            )
            record_metric_in_span(metric)

        except Exception as e:
            logging.warning(
                f"LangchainLLMCalculator - Failed to validate expression: {expression}, delegating to next calculator. Exception:\n{e}"
            )
            metric = metricRecorder(
                type="failure",
                name="invalid_expression",
                value="global_failure",
                message=f"LangchainLLMCalculator - Failed to validate expression: {expression}, delegating to next calculator. Exception:\n{e}"
            )
            record_metric_in_span(metric)
        return super().calculate_expression(expression)

    def is_valid_result(self, expression: str, result: float) -> bool:
        SYSTEM_PROMPT = """
            You are a validation agent that takes a natural language mathematical problem, the proposed result, and verifies whether the result is correct. Your task is to return a JSON object with two fields:

            1. **evaluation_status**: 
            - `"Success"` if the result solves the problem.
            - `"Fail"` if the result does not solve the problem.

            2. **explanation**:
            - A string explaining the reason for success or failure.

            ### Examples:

            **Example 1:**

            **Input:**  
            Problem: "What is the sum of 15, 20, and 35?"  
            Result: 70  

            **Output:**  
            {{
                "evaluation_status": "Success",
                "explanation": "The sum of 15, 20, and 35 is correctly calculated as 70."
            }}

            ---

            **Example 2:**

            **Input:**  
            Problem: "Find the average of 5, 12, 18, and 25."  
            Result: 15  

            **Output:**  
            {{
                "evaluation_status": "Fail",
                "explanation": "The average of 5, 12, 18, and 25 is calculated as (5 + 12 + 18 + 25) / 4 = 15. The provided result is incorrect."
            }}

            ---

            **Example 3:**

            **Input:**  
            Problem: "Multiply 6 by 7, then add 14."  
            Result: 70  

            **Output:**  
            {{
                "evaluation_status": "Success",
                "explanation": "6 multiplied by 7 is 42, and adding 14 gives the correct result of 70."
            }}

            ---

            **Example 4:**

            **Input:**  
            Problem: "If the older son is twice as old as the younger son and their combined age is 9, what is the age of the older son?"  
            Result: 6  

            **Output:**  
            {{
                "evaluation_status": "Success",
                "explanation": "If the younger son is x years old, then the older son is 2x years old. Their combined age is x + 2x = 3x = 9, so x = 3. The older son is 2x = 6 years old."
            }}

            ---

            **Example 5:**

            **Input:**  
            Problem: "A car travels 60 miles per hour for 3 hours. How far did it travel in total?"  
            Result: 180  

            **Output:**  
            {{
                "evaluation_status": "Success",
                "explanation": "The car's total distance is calculated as speed × time = 60 miles per hour × 3 hours = 180 miles. The result is correct."
            }}

            ---

            ### Instructions:
            1. Evaluate the provided result against the problem.
            2. Return a JSON object with the `evaluation_status` and an explanation.
            3. Handle a variety of mathematical problems (e.g., sums, averages, percentages, roots, word problems, etc.).
        """

        result_validation_respose = {
            "title": "result_validation_respose",
            "type": "object",
            "properties": {
                "evaluation_status": {
                    "type": "string",
                    "enum": [
                        "Success",
                        "Fail",
                    ],
                },
                "explanation": {"type": "string"},
            },
            "required": ["evaluation_status", "explanation"],
            "additionalProperties": False,
        }

        prompt = ChatPromptTemplate.from_messages(
            [("system", dedent(SYSTEM_PROMPT)), ("user", "{input}")]
        )
        chat_model = prompt | self.result_validation_llm.with_structured_output(
            result_validation_respose
        )

        try:
            request = f"Problem: {expression}\nResult: {result}"
            response = chat_model.invoke({"input": request})
            evaluation_status = response["evaluation_status"]
            explanation = response["explanation"]
            if evaluation_status == "Success":
                return True
            logging.warning(
                f"LangchainLLMCalculator - The result: {result} is not a valid solution for expression: {expression} retuned None, delegating to next calculator. Explanation:\n{explanation}"
            )
            metric = metricRecorder(
                type="failure",
                name="validation_failure",
                value="local_failure",
                message=f"LangchainLLMCalculator - The result: {result} is not a valid solution for expression: {expression} retuned None, delegating to next calculator. Explanation:\n{explanation}"
            )
            record_metric_in_span(metric)
        except Exception as e:
            logging.warning(
                f"LangchainLLMCalculator - Failed to evaluate the correctness of the result: {result} for expression: {expression}. Exception:\n{e}"
            )
            metric = metricRecorder(
                type="failure",
                name="validation_failure",
                value="local_failure",
                message=f"LangchainLLMCalculator - Failed to evaluate the correctness of the result: {result} for expression: {expression}. Exception:\n{e}"
            )
            record_metric_in_span(metric)
        return super().is_valid_result(expression, result)


if __name__ == "__main__":
    MODEL = "gpt-4o-2024-08-06"
    AZURE_API_VERSION = "2024-08-01-preview"
    from langchain_openai import AzureChatOpenAI
    from dotenv import load_dotenv

    load_dotenv()

    llm = AzureChatOpenAI(
        model=MODEL,
        api_version=AZURE_API_VERSION,
    )
    expression = "3+2+5"
    # expression = "3 + (2 *[4 + 5]) + {[7 - 2] + {9 / 3}}-[15 - (3+{2+6})]"
    # expression = "3 + (2 *[4 + 5]) + {[7 - 2] + {nine divided by three}}-[15 - (3+{the next integer after 7})]"
    calculator = LangchainLLMCalculator(
        llm, llm, llm, True, True, max_num_of_attempts=3
    )
    print(calculator.calculate_expression(expression))
