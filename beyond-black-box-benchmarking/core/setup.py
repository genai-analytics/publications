from setuptools import setup, find_packages

setup(
    name='agent-analytics-core',
    version='0.1',
    packages=find_packages(where="src", include=["agent_analytics_core*"]),
    package_dir={'': 'src'},
     install_requires=[        
        "pydantic>=2.9.2",
    ],
)