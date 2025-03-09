from setuptools import setup, find_packages
import os

# Get the current file directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the sibling 'core' directory (one level up from current dir)
core_package_path = os.path.normpath(os.path.join(current_dir, '..', 'core'))

setup(
    name="agent_analytics",
    version="0.3.2",
    description="Agent Analytics observability SDK package",
    package_dir={"": "src"},
    packages=find_packages(where="src", include=["agent_analytics*"]),
    install_requires=[
        f"agent-analytics-core @ file://{core_package_path}",
        "traceloop-sdk>=0.33.3,<0.34.0",
        "langtrace-python-sdk>=3.3.4",
        "pydantic>=2.8.2",
        "botocore",
        "packaging",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.10,<3.13',
)