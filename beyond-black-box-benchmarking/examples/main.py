from langgraph_LLM_calculator import LanggraphLLMCalculator

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
    # Example expression.
    # expression = "3+[1+2+3/3]*5+6/((2+1)*2-3)"
    expression = "3 + (2 *[4 + 5]) + {[7 - 2] + {nine divided by three}}-[15 - (3+{the next integer after 7})]"
    calculator = LanggraphLLMCalculator(llm)

    try:
        calculated_value = calculator.calculate_expression(expression)
        print(f"Calculated result is: {calculated_value}")
    except Exception as e:
        print(e)

    # Stop the shared servers (this stops servers for all instances).
    calculator.stop_servers()