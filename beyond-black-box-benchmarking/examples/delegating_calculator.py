import logging
from base_calculator import BaseCalculator


class DelegatingCalculator(BaseCalculator):
    """
    DelegatingCalculator attempts to calculate an expression by delegating it to a list of other calculators.
    It iterates through the list and returns the result from the first calculator that successfully evaluates the expression.
    If none of the calculators can evaluate the expression, it returns None.
    """

    def __init__(self, calculators: list[BaseCalculator] = []):
        """
        Initializes the calculator with a list of calculators to delegate calculations to.
        """
        self.calculators = calculators

    def calculate_expression(self, expression: str) -> float:

        for i, calculator in enumerate(self.calculators):
            try:
                result = calculator.calculate_expression(expression)
                if result is not None:
                    logging.info(
                        f"DelegatingCalculator - {expression} calculated using {calculator.__class__.__name__} at index {i}"
                    )
                    return result
            except Exception as e:
                logging.warning(
                    f"DelegatingCalculator - Failed to calculate {expression} by calculator {calculator.__class__.__name__} at index {i}. Exception {e}"
                )

        logging.warning(
            f"DelegatingCalculator - Unable to calculate {expression} with any available calculators"
        )
        return super().calculate_expression(expression)

    def is_valid_expression(self, expression: str) -> bool:
        """
        Checks if any of the calculators can handle the given expression.
        """
        return any(
            calculator.is_valid_expression(expression)
            for calculator in self.calculators
        )

    def is_valid_result(self, expression: str, result: float) -> bool:
        """
        Checks if any of the calculators validate the given result for the expression.
        """
        return any(
            calculator.is_valid_result(expression, result)
            for calculator in self.calculators
        )
