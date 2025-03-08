import logging
from base_calculator import BaseCalculator


class PredefinedCalculator(BaseCalculator):
    """
    PredefinedCalculator stores a set of predefined expressions and their results.
    It can only calculate expressions that were initialized in the constructor.
    If an expression is not found, it returns None.
    """

    def __init__(self, predefined_results: dict = None):
        """
        Initializes the calculator with predefined expressions and their results.
        :param predefined_results: A dictionary where keys are expressions (str) and values are results (float).
        """
        self.predefined_results = predefined_results if predefined_results else {}

    def calculate_expression(self, expression: str) -> float:
        """
        Returns the result of the expression if it's predefined, otherwise logs an error.
        """
        if self.is_valid_expression(expression):
            result = self.predefined_results[expression]
            logging.info(
                f"PredefinedCalculator - Calculated result for {expression} is: {result}"
            )
            return result

        logging.warning(
            f"PredefinedCalculator - Unable to find predefined expression: {expression}"
        )
        return super().calculate_expression(expression)

    def is_valid_expression(self, expression: str) -> bool:
        """
        Checks if the expression is one of the predefined expressions.
        """
        return expression in self.predefined_results

    def is_valid_result(self, expression: str, result: float) -> bool:
        """
        Checks if the given result matches the predefined result for the expression.
        """
        return self.predefined_results.get(expression) == result
