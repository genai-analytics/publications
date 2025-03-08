import logging


class BaseCalculator:
    def calculate_expression(self, expression: str) -> float:
        logging.error(f"BaseCalculator - Unable to calculate {expression}")
        return None

    def is_valid_expression(self, expression: str) -> bool:
        return False

    def is_valid_result(self, expression: str, result: float) -> bool:
        return False
