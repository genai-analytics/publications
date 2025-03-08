from typing import TypedDict
import re
import json
import time
import random
from base_calculator import BaseCalculator
from eval_calculator import EvalCalculator
from langgraph.graph import StateGraph, END, START
import logging

from textwrap import dedent


class LanggraphEvalCalculator(EvalCalculator):
    def __init__(
        self,
        calculators: list = None,
        min_delay_msec: int = 0,
        max_delay_msec: int = 0,
        addition_calculator: BaseCalculator = None,
        subtraction_calculator: BaseCalculator = None,
        multiplication_calculator: BaseCalculator = None,
        division_calculator: BaseCalculator = None,
        parentheses_calculator: BaseCalculator = None,
        square_brackets_calculator: BaseCalculator = None,
        curly_brackets_calculator: BaseCalculator = None,
    ):
        if calculators is None:
            calculators = []
        super().__init__(calculators)

        self.min_delay_msec = min_delay_msec
        self.max_delay_msec = max_delay_msec
        self.addition_calculator = (
            addition_calculator if addition_calculator is not None else EvalCalculator()
        )
        self.subtraction_calculator = (
            subtraction_calculator if subtraction_calculator is not None else EvalCalculator()
        )
        self.multiplication_calculator = (
            multiplication_calculator if multiplication_calculator is not None else EvalCalculator()
        )
        self.division_calculator = (
            division_calculator if division_calculator is not None else EvalCalculator()
        )
        self.parentheses_calculator = parentheses_calculator
        self.square_brackets_calculator = square_brackets_calculator
        self.curly_brackets_brackets = curly_brackets_calculator

    class ExpressionGraphState(TypedDict):
        expression: str
        operations: list
        result_variable_name: str
        result: float
        iteration: int
        is_result_correct: bool
        calc_operations_agent: StateGraph

    def extract_specific_upper_level_brackets(
        self,
        expression: str,
        extract_parentheses: bool,
        extract_square_brackets: bool,
        extract_curly_brackets: bool,
    ):
        """
        Extracts all top-level bracket groups from the expression for the specified bracket types.
        A bracket group is considered top-level if its opening bracket is not nested inside any other bracket,
        regardless of the outer bracket's type.

        The extraction is performed only for those bracket types for which the corresponding flag is True.
        For example, if extract_parentheses is True but extract_square_brackets is False, then even if a pair
        of square brackets appears at the top level, it will not be extracted.

        Returns a dictionary with:
        - "updated_expression": the original expression with each extracted bracket group replaced by a unique variable name.
        - "operations": a list of dictionaries for each extracted group, each containing:
                "name": the variable name (e.g., "E0")
                "operation": a label indicating the type ("parentheses", "square_brackets", or "curly_brackets")
                "op1": the inner content of the extracted bracket group
                "op2": an empty string (reserved for further use)
        """
        # Mapping for allowed extraction types.
        allowed_extraction = {}
        if extract_parentheses:
            allowed_extraction["("] = (")", "parentheses")
        if extract_square_brackets:
            allowed_extraction["["] = ("]", "square_brackets")
        if extract_curly_brackets:
            allowed_extraction["{"] = ("}", "curly_brackets")

        # If no bracket type is allowed for extraction, return the expression unchanged.
        if not allowed_extraction:
            return {"updated_expression": expression, "operations": []}

        # Full mapping for all bracket types for matching purposes.
        full_map = {"(": ")", "[": "]", "{": "}"}

        extractions = (
            []
        )  
        stack = []
        for i, char in enumerate(expression):
            if char in full_map:  # Opening bracket (any type).
                is_top_level = len(stack) == 0 and char in allowed_extraction
                stack.append((char, i, is_top_level))
            elif char in full_map.values():  # Closing bracket (any type).
                if not stack:
                    continue
                open_char, start_index, is_top_level = stack[-1]
                expected_close = full_map[open_char]
                if char == expected_close:
                    stack.pop()
                    if is_top_level and len(stack) == 0:
                        inner_expr = expression[start_index + 1 : i]
                        label = allowed_extraction[open_char][
                            1
                        ]  # Retrieve the label for this bracket type.
                        extractions.append((start_index, i, label, inner_expr))
                else:
                    continue

        # Process the extractions from left to right, replacing each extracted bracket group with a variable.
        operations = []
        updated_expression = expression
        delta = 0  # Tracks shifts in indices due to replacements.
        variable_counter = 0
        for start, end, label, inner_expr in extractions:
            variable_name = f"E{variable_counter}"
            variable_counter += 1
            operations.append(
                {
                    "name": variable_name,
                    "operation": label,
                    "op1": inner_expr,
                    "op2": "",
                }
            )
            # Replace the entire bracket group (from start to end, inclusive) with the variable name.
            updated_expression = (
                updated_expression[: start - delta]
                + variable_name
                + updated_expression[end - delta + 1 :]
            )
            # Update delta to account for the change in length.
            delta += (end - start + 1) - len(variable_name)

        return {"updated_expression": updated_expression, "operations": operations}

    def extract_upper_level_brackets(self, expression: str):
        return self.extract_specific_upper_level_brackets(
            expression=expression,
            extract_parentheses=True,
            extract_square_brackets=True,
            extract_curly_brackets=True,
        )

    def extract_arithmetic_operations(self, operations, expression: str):
        # Handle Multiplication and Division next (left to right)
        tokens = re.split(r"(\+|-|\*|/)", expression)
        variable_counter = len(operations)

        i = 0
        while i < len(tokens):
            if tokens[i] in ("*", "/"):  # If it's a multiplication or division
                op = tokens[i]
                op1 = tokens[i - 1].strip()
                op2 = tokens[i + 1].strip()
                variable_name = f"E{variable_counter}"
                variable_counter += 1
                operations.append(
                    {
                        "name": variable_name,
                        "operation": "multiplication" if op == "*" else "division",
                        "op1": op1,
                        "op2": op2,
                    }
                )
                # Update tokens list
                tokens[i - 1] = variable_name
                del tokens[i : i + 2]
            else:
                i += 1

        # Handle Addition and Subtraction last (left to right)
        i = 0
        while i < len(tokens):
            if tokens[i] in ("+", "-"):  # If it's an addition or subtraction
                op = tokens[i]
                op1 = tokens[i - 1].strip()
                op2 = tokens[i + 1].strip()
                variable_name = f"E{variable_counter}"
                variable_counter += 1
                operations.append(
                    {
                        "name": variable_name,
                        "operation": "addition" if op == "+" else "subtraction",
                        "op1": op1,
                        "op2": op2,
                    }
                )
                # Update tokens list
                tokens[i - 1] = variable_name
                del tokens[i : i + 2]
            else:
                i += 1

        for obj in operations:
            print(json.dumps(obj, separators=(",", ":")))
        return operations

    def decompose(self, state: ExpressionGraphState):
        expression = state["expression"]
        upper_level_brackets_extraction_result = self.extract_upper_level_brackets(
            expression
        )
        upper_level_brackets_operations = upper_level_brackets_extraction_result[
            "operations"
        ]
        updated_expression = upper_level_brackets_extraction_result[
            "updated_expression"
        ]
        operations = self.extract_arithmetic_operations(
            upper_level_brackets_operations, updated_expression
        )
        return {"operations": operations}

    def calculate_addition(self, op1, op2) -> float:
        return self.addition_calculator.calculate_expression(f"{op1}+{op2}")

    def calculate_subtraction(self, op1, op2) -> float:
        return self.subtraction_calculator.calculate_expression(f"{op1}-{op2}")

    def calculate_multiplication(self, op1, op2) -> float:
        return self.multiplication_calculator.calculate_expression(
            f"{op1}*{op2}"
        )

    def calculate_division(self, op1, op2) -> float:
        return self.division_calculator.calculate_expression(f"{op1}/{op2}")

    def calculate_parentheses(self, op1) -> float:
        if self.parentheses_calculator is not None:
            return self.parentheses_calculator.calculate_expression(op1)
        # Recursive call
        return self.calculate_expression(op1)

    def calculate_square_brackets(self, op1) -> float:
        if self.square_brackets_calculator is not None:
            return self.square_brackets_calculator.calculate_expression(op1)
        # Recursive call
        return self.calculate_expression(op1)

    def calculate_curly_brackets(self, op1) -> float:
        if self.curly_brackets_brackets is not None:
            return self.curly_brackets_brackets.calculate_expression(op1)
        # Recursive call
        return self.calculate_expression(op1)

    def create_operation_function(
        self, operations_graph_state_class, variable_name, operation, op1, op2
    ):
        def operation_function(state: operations_graph_state_class):  # type: ignore
            print(f"Calculate {variable_name} by {operation}({op1},{op2})")
            full_operation = state[variable_name]
            if operation == "parentheses":
                result = self.calculate_parentheses(op1)
            elif operation == "square_brackets":
                result = self.calculate_square_brackets(op1)
            elif operation == "curly_brackets":
                result = self.calculate_curly_brackets(op1)
            else:
                operand1 = state[op1]["result"] if isinstance(op1, str) else op1
                operand2 = state[op2]["result"] if isinstance(op2, str) else op2

                if operation == "addition":
                    result = self.calculate_addition(operand1, operand2)
                elif operation == "subtraction":
                    result = self.calculate_subtraction(operand1, operand2)
                elif operation == "multiplication":
                    result = self.calculate_multiplication(operand1, operand2)
                elif operation == "division":
                    if operand2 == 0:
                        raise ValueError("Division by zero is not allowed.")
                    result = self.calculate_division(operand1, operand2)
                else:
                    raise ValueError(f"Unknown operation: {operation}")
            time.sleep(
                random.uniform(self.min_delay_msec, self.max_delay_msec)
                / 1000
            )
            print(f"The value of {variable_name} is {result}")
            full_operation["result"] = result
            return {variable_name: full_operation}

        # Set the name of the function dynamically
        operation_function.__name__ = f"calc_{variable_name}"

        return operation_function

    def create_claculation_agent(self, operations):
        fields = {operation["name"]: dict for operation in operations}
        OperationsGraphState = TypedDict("OperationsGraphState", fields)
        workflow = StateGraph(OperationsGraphState)
        for operation in operations:
            variable_name = operation["name"]
            op1 = operation["op1"]
            op2 = operation["op2"]
            if (
                operation["operation"] != "parentheses"
                and operation["operation"] != "square_brackets"
                and operation["operation"] != "curly_brackets"
            ):
                if isinstance(op1, str) and not op1.startswith("E"):
                    op1 = float(op1) if "." in op1 else int(op1)
                if isinstance(op2, str) and not op2.startswith("E"):
                    op2 = float(op2) if "." in op2 else int(op2)
            node_function = self.create_operation_function(
                OperationsGraphState, variable_name, operation["operation"], op1, op2
            )
            workflow.add_node(node_function.__name__, node_function)
            operation_has_no_dependencies = True
            if (
                operation["operation"] != "parentheses"
                and operation["operation"] != "square_brackets"
                and operation["operation"] != "curly_brackets"
            ):
                if isinstance(op1, str) and isinstance(op2, str):
                    workflow.add_edge(
                        [f"calc_{op1}", f"calc_{op2}"], node_function.__name__
                    )
                    operation_has_no_dependencies = False
                else:
                    if isinstance(op1, str):
                        workflow.add_edge(f"calc_{op1}", node_function.__name__)
                        operation_has_no_dependencies = False
                    if isinstance(op2, str):
                        workflow.add_edge(f"calc_{op2}", node_function.__name__)
                        operation_has_no_dependencies = False
            if operation_has_no_dependencies:
                workflow.add_edge(START, node_function.__name__)
        calc_operations_agent = workflow.compile()
        return calc_operations_agent

    def plan(self, state: ExpressionGraphState):
        operations = state["operations"]
        calc_operations_agent = self.create_claculation_agent(operations)
        result_variable_name = operations[len(operations) - 1]["name"]
        time.sleep(
            random.uniform(self.min_delay_msec, self.max_delay_msec)
            / 1000
        )
        return {
            "calc_operations_agent": str(id(calc_operations_agent)),
            "result_variable_name": result_variable_name,
        }

    def execute(self, state: ExpressionGraphState):
        operations = state["operations"]
        calc_operations_agent = self.create_claculation_agent(operations)
        input = {obj["name"]: obj for obj in operations if "name" in obj}
        output = calc_operations_agent.invoke(input=input)
        result = output[state["result_variable_name"]]["result"]
        return {"result": result, "iteration": state["iteration"] + 1}

    def validate(self, state: ExpressionGraphState):
        is_result_correct = self.is_valid_result(state["expression"], state["result"])
        time.sleep(
            random.uniform(self.min_delay_msec, self.max_delay_msec)
            / 1000
        )
        return {"is_result_correct": is_result_correct}

    def should_finish(self, state: ExpressionGraphState):
        iteration = state["iteration"]
        if state["is_result_correct"]:
            return "finish"
        if iteration > 2:
            raise Exception("Unable to calculate expression")
        print(f"Iteration {iteration}: failed to create correct result")
        return "continue"

    def calculate_expression(self, expression: str) -> float:
        try:
            print("Calculate the following expression: " + expression)
            if self.is_valid_expression(expression):
                workflow = StateGraph(self.__class__.ExpressionGraphState)
                workflow.add_node("decompose", self.decompose)
                workflow.add_node("plan", self.plan)
                workflow.add_node("execute", self.execute)
                workflow.add_node("validate", self.validate)
                workflow.add_edge(START, "decompose")
                workflow.add_edge("decompose", "plan")
                workflow.add_edge("plan", "execute")
                workflow.add_edge("execute", "validate")
                workflow.add_conditional_edges(
                    "validate",
                    self.should_finish,
                    {
                        "finish": END,
                        "continue": "decompose",
                    },
                )
                langgraph = workflow.compile()
                output = langgraph.invoke(
                    input={"expression": expression, "iteration": 0}
                )
                result = output["result"]
                time.sleep(
                    random.uniform(
                        self.min_delay_msec, self.max_delay_msec
                    )
                    / 1000
                )
                print(f"The result of {expression} is: {result}")
                return result
        except Exception as e:
            logging.error(
                f"LanggraphEvalCalculator - Failed to calculate expression: {expression}. Exception: {e}"
            )
        return super().calculate_expression(expression)


if __name__ == "__main__":
    # expression = "3+(1+2+3/3)*5+6/(8+((6-2)*4-7)-14)"
    # expression = "3 + (2 *[4 + 5]) + {[7 - 2] + {9 / 3}}-[15 - (3+{2+6})]"
    expression = "7*[2+18/3]-9+(4*5-2)"

    calculator = LanggraphEvalCalculator()
    try:
        calculated_value = calculator.calculate_expression(expression)
    except Exception as e:
        print(e)
