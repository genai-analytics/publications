from langgraph_eval_calculator import LanggraphEvalCalculator
from base_calculator import BaseCalculator
from typing import TypedDict, Any, Optional
import json
import time
import random
from textwrap import dedent
import logging
import threading
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
import socket
from pydantic import BaseModel


class LanggraphDistributedCalculator(LanggraphEvalCalculator):
    # Global dictionary to hold server instances, shared among all instances.
    global_servers: dict[int, "LanggraphDistributedCalculator.StoppableServer"] = {}

    # Server configuration defined at the class level.
    BASE_PORT: int = 8000
    NUM_OF_SERVERS: int = 2
    PORTS: list[int] = [8000 + i for i in range(NUM_OF_SERVERS)]

    class StoppableServer(threading.Thread):
        def __init__(self, port: int, calculator: BaseCalculator):
            super().__init__()
            self.port = port
            self.stop_event = threading.Event()
            self.server: Optional[uvicorn.Server] = None
            self.calculator = calculator

        def run(self):
            app = FastAPI()

            class Expression(BaseModel):
                expression: str

            @app.post("/calculate")
            async def calculate(expression: Expression):
                try:
                    # Evaluate the math expression
                    logging.info(
                        f"Calculating expression on server (port={self.port}): {expression.expression}"
                    )
                    result = self.calculator.calculate_expression(expression.expression)
                    return {"result": result}
                except Exception as e:
                    raise HTTPException(status_code=400, detail=str(e))

            config = uvicorn.Config(
                app, host="0.0.0.0", port=self.port, log_level="info"
            )
            self.server = uvicorn.Server(config)

            # Run the server until stop_event is set.
            while not self.stop_event.is_set():
                self.server.run()

        def stop(self):
            if self.server:
                self.server.should_exit = True
            self.stop_event.set()

    # Function to check if a port is available.
    def is_port_available(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) != 0

    # Function to create and start a server.
    def create_server(
        self, port: int
    ) -> "LanggraphDistributedCalculator.StoppableServer":
        server = LanggraphDistributedCalculator.StoppableServer(port, self)
        server.start()
        time.sleep(2)  # Allow time for the server to start.
        return server

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
        # Avoid mutable default arguments
        if calculators is None:
            calculators = []

        # Pass all parameters to the superclass __init__
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

        # Use the class-level global_servers.
        self.servers = LanggraphDistributedCalculator.global_servers

        # For each configured port (from the class-level PORTS), create a server if not already running.
        for port in LanggraphDistributedCalculator.PORTS:
            if port not in self.servers:
                if self.is_port_available(port):
                    server = self.create_server(port)
                    self.servers[port] = server
                else:
                    print(
                        f"Port {port} is already in use. Skipping server creation on this port."
                    )

    def calculate_square_brackets(self, op1: str):
        # Select a random server from the class-level PORTS.
        selected_port = random.choice(LanggraphDistributedCalculator.PORTS)
        url = f"http://localhost:{selected_port}/calculate"
        try:
            logging.info(f"Sending expression: {op1} to port: {selected_port}")
            response = requests.post(url, json={"expression": op1})
            response_data = response.json()
            if "result" in response_data:
                return response_data["result"]
            else:
                raise Exception(response_data.get("detail", "Unknown server error"))
        except requests.exceptions.RequestException as e:
            logging.error(f"Could not connect to server ({str(e)})")
        except Exception as e:
            logging.error(f"Unknown server error: {str(e)}")

        # Fallback to the parent implementation if needed.
        return super().calculate_square_brackets(op1)

    def stop_servers(self):
        # Stop all servers from the global shared dictionary.
        for port, server in LanggraphDistributedCalculator.global_servers.items():
            server.stop()
            server.join()
        print("All servers stopped.")
        # Optionally clear the global dictionary if you intend to restart fresh.
        LanggraphDistributedCalculator.global_servers.clear()


if __name__ == "__main__":
    # Example expression.
    expression = "3+[1+2+3/3]*5+6/((2+1)*2-3)"
    calculator = LanggraphDistributedCalculator()

    try:
        calculated_value = calculator.calculate_expression(expression)
        print(f"Calculated result is: {calculated_value}")
    except Exception as e:
        print(e)

    # Stop the shared servers (this stops servers for all instances).
    calculator.stop_servers()
