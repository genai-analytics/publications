# Agent Analytics SDK

![Python Version](https://img.shields.io/badge/python-3.10--3.12-blue.svg)
![Work in Progress](https://img.shields.io/badge/status-WIP-orange.svg)
![Version](https://img.shields.io/badge/version-0.3.2-blue)

The Agent Analytics SDK is a Python package designed to enhance the observability and tracing capabilities of your LLM-based agentic applications. It integrates seamlessly with popular libraries like LangChain and OpenAI, offering robust logging and tracing features to effectively monitor your applications.

Currently, the Agent Analytics SDK extends popular LLM tracing tools like [Traceloop](https://www.traceloop.com/) and [Langtrace](https://www.langtrace.ai/), adding improved semantics and additional functionalities.


## OpenTelemetry Support

Agent Analytics SDK generates traces compliant with [OpenTelemetry](https://opentelemetry.io/docs/) (OTEL) standards. We're also developing semantic conventions for the traces generated by this project.
 

## Installation

You can install **Agent Analytics SDK** directly from the Git repository using `pip`. 


### Install via `pip` from Git Repository


To install the SDK directly from the Git repository, use one of the following methods:

### Install the Latest Version
Install the `release` branch to get the latest stable updates:

```bash
pip install git+ssh://git@github.ibm.com/agent-analytics/sdk.git@release
```
### Install a Specific Version
To install a specific version of the SDK, use a version tag (e.g., v0.3.2):

```bash
pip install git+ssh://git@github.ibm.com/agent-analytics/sdk.git@v0.3.2
```
### Alternative: Clone and Install Locally

If you prefer to work with the source code or contribute to the project, you can clone the repository and install it locally.

1. **Clone the Repository**

   ```bash
   git clone git@github.ibm.com:agent-analytics/sdk.git@your_dev_branch
   ```

2. **Navigate to the Repository Directory**

   ```bash
   cd observability-sdk
   ```

3. **Install the Package**

   - **Standard Installation**

     ```bash
     pip install .
     ```

   - **Editable Installation (Recommended for Development)**

     ```bash
     pip install -e .
     ```

## Quick Start


Before using **Agent Analytics SDK**, ensure you have all the necessary dependencies installed. It's recommended to use a virtual environment to manage your project dependencies.

## Configuration

**Agent Analytics SDK** offers flexible configuration options to suit various tracing backends and logging requirements.

### Tracer Types

- **Default**: Generates a log file.

  
## Local file Usage Example
Below is an example demonstrating how to integrate **Agent Analytics SDK** with your LLM application.

```python
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from agent_analytics.instrumentation import agent_analytics_sdk 

# Load environment variables from .env file
load_dotenv()

# Initialize logging with agent_analytics_sdk
agent_analytics_sdk.initialize_logging()

# LangGraph App code ...
```

#### Explanation

1. **agent_analytics_sdk Initialization**: This is the primary namespace used to initialize logging.
2. **Logs**: The example generates logs stored in the run file directory.

### Specify the log file: 

```python
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from agent_analytics.instrumentation import agent_analytics_sdk 

# Load environment variables from .env file
load_dotenv()

# Logs directory, optional
logs_dir_path = "path/to/your/logs"

# Generated log filename, optional 
log_filename = "my_log"

# Initialize logging with agent_analytics_sdk
agent_analytics_sdk.initialize_logging(
    logs_dir_path=logs_dir_path,
    log_filename=log_filename
)

# LangGraph App code ...

```

#### Explanation
1. **Logs**: this example will generate logs in the specified path. 

## Remote Collector Example
In the example below we are configuring the sdk to work with a `Jeager` collector:
```python

from agent_analytics.instrumentation.configs import OTLPCollectorConfig
from agent_analytics.instrumentation import agent_analytics_sdk

agent_analytics_sdk.initialize_logging(
    tracer_type = agent_analytics_sdk.SUPPORTED_TRACER_TYPES.REMOTE,
    config = OTLPCollectorConfig(
            endpoint='http://localhost:4318/v1/traces',
            app_name='my_app',
    )
)
```

#### Explanation
1. **OTLPCollectorConfig**: This class is used to provide the remote collector configurations to the sdk
2. **Traces**: With this configurations the sdk will stream the `spans` to the specified collector  


### For further and more complete examples, refer to the [examples repo](https://github.ibm.com/agent-analytics/examples).

## Architecture
For information on the architecture of the SDK and the key components, please review [architecture.md](docs/architecture.md)

## Agent Analytics Task Flow Analysis

The `agent_analytics_sdk` instrumentation enables you to generate logs and analyze them using the Agent Analytics online service. With this service, you can:

1. Generate a Flow Graph.
2. Visualize interactive hierarchical task flows.
3. Explore aggregated metrics calculated for each task.


### How to Get Started

1. **Log In with IBM SSO**  
   Access the Agent Analytics service via [Agent Analytics Server](https://dashboard-agent-analytics.agent-analytics-9ca4d14d48413d18ce61b80811ba4308-0000.us-south.containers.appdomain.cloud/). Use your IBM SSO credentials for secure and seamless access.

2. **Complete the Registration Form**  
   On your first login, you’ll be prompted to complete a brief registration form. This form includes an optional survey to help us improve the service and better understand your needs.  
   - **Friendly Reminder**: The survey is optional, but your feedback is highly appreciated. It only takes a moment and directly contributes to enhancing the tools and features.  
  
   After submitting the form, you’ll be granted access within 48 hours.

3. **Upload Your Logs**  
   Once logged in, upload the log files generated by the SDK. These logs are processed to create your task flow visualizations.

4. **Explore and Analyze**  
   - **Flow Graphs**: Dive into interactive, hierarchical task flows to understand the behavior of your applications.  
   - **Aggregated Metrics**: Review metrics calculated for each task, helping you identify trends, issues, and optimization opportunities.

## Known Issues
1. **FastAPI Instrumentation**  
   The SDK automatically instruments all FastAPI applications, but it requires a specific import order to take effect. To ensure proper instrumentation, you can use one of the following approaches:

   **Approach 1**: Import `FastAPI` class after SDK initialization
   ```python
   from agent_analytics.instrumentation import agent_analytics_sdk
   agent_analytics_sdk.initialize_logging()

   from fastapi import FastAPI
   app = FastAPI()
   ```
   **Approach 2**: Import `fastapi` module (order does not matter)
   ```python
   import fastapi

   from agent_analytics.instrumentation import agent_analytics_sdk
   agent_analytics_sdk.initialize_logging()

   app = fastapi.FastAPI()
   ```
   **Important**: Avoid the following import order, as it will prevent FastAPI instrumentation:
   ```python
   from fastapi import FastAPI

   from agent_analytics.instrumentation import agent_analytics_sdk
   agent_analytics_sdk.initialize_logging()

   # app will not be instrumented
   app = FastAPI()
   ```

### Support and Feedback

For any questions, feedback, or assistance, feel free to visit our [Agent Analytics Users Slack Channel](https://ibm.enterprise.slack.com/archives/C082N61GVE1). Our team is here to help ensure you get the most out of the Agent Analytics SDK.

---
