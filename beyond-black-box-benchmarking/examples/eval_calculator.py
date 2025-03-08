import logging
from delegating_calculator import DelegatingCalculator

from pydantic import BaseModel
from agent_analytics.instrumentation.utils import record_metric_in_span
class metricRecorder(BaseModel):
    type: str = "failure"
    name: str = None
    value: str = None
    message: str = None


class EvalCalculator(DelegatingCalculator):
    """
    EvalCalculator attempts to evaluate expressions using Python's eval() method.
    If evaluation fails, it delegates the calculation to the list of provided calculators.
    """

    def covert_brackets_to_parentheses(self, expression: str) -> str:
        converted_expression = (
            expression.replace("[", "(")
            .replace("]", ")")
            .replace("{", "(")
            .replace("}", ")")
        )
        return converted_expression

    def calculate_expression(self, expression: str) -> float:
        try:
            converted_expression = self.covert_brackets_to_parentheses(expression)
            result = eval(converted_expression, {"__builtins__": None}, {})
            logging.info(
                f"EvalCalculator - Successfully evaluated {expression} as {result}"
            )
            return result
        except Exception as e:
            logging.warning(
                f"EvalCalculator - Failed to evaluate {expression}, delegating to next calculator"
            )
        return super().calculate_expression(expression)

    def is_valid_expression(self, expression: str) -> bool:
        converted_expression = self.covert_brackets_to_parentheses(expression)
        try:
            eval(converted_expression, {"__builtins__": None}, {})
            return True
        except Exception:
            logging.error(
                f"EvalCalculator - Failed to validate {expression}, delegating to next calculator"
            )
        return super().is_valid_expression(expression)

    def is_valid_result(self, expression: str, result: float) -> bool:
        converted_expression = self.covert_brackets_to_parentheses(expression)
        try:
            return eval(converted_expression, {"__builtins__": None}, {}) == result
        except Exception:
            logging.error(
                f"EvalCalculator - Failed to validate result:{result} for {expression}, delegating to next calculator"
            )
            metric = metricRecorder(
                type="failure",
                name="validation_failure",
                value="local_failure",
                message=f"EvalCalculator - Failed to validate result:{result} for {expression}, delegating to next calculator"
            )
            record_metric_in_span(metric)

        return super().is_valid_result(expression, result)


if __name__ == "__main__":
    expression = "3+[1+2+3/3]*5+6/((2+1)*2-3)"
    calculator = EvalCalculator()
    result = calculator.calculate_expression(expression=expression)
    print(f"The result of the following expression:{expression} is {result}")
