# ABBench Benchmark

ABBench (Agent Analytics Behavioral Benchmark) includes three folders: trace logs of an agentic systems, ground truth analytics outputs and TAMAS (Task-oriented Analytics for Multi-Agentic Systems) analytics outputs.

## Logs folder

Includes a dataset of 30 structured logs, designed to capture various types of agentic system issues. The logs were generated from runs of the calculator agentic system, see **examples** folder.

## ground_truth folder

### summaries folder

For each log, **gt_summary.csv** includes key trace metrics such as execution time, number of input and output tokens, and the number of LLM and tool calls. It also contains the number and severity of failures, both overall and categorized by failure type.

### failure_lists folder

30 files that include lists of failures with descriptions.

### task_flows folder

30 files with structured task-oriented representations of an agentic system’s trace.

## TAMAS folder

### summaries folder

For each log, **summary.csv** includes TAMAS outputs of key trace metrics.

### failure_lists folder

30 files that include TAMAS outputs of lists of failures.

### task_flows folder

30 files with  TAMAS outputs of structured task-oriented representations of an agentic system’s trace.

## How to use ABBench?

Using your agent analytics systems, access and analyze ABBench logs. Then compare your analytics outcomes with the Ground Truth.

### ABBENCH will be extended with additional logs and tools.