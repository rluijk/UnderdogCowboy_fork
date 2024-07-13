from setuptools import setup, find_packages

setup(
    name="underdogcowboy",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "underdogcowboy=underdogcowboy.main:main",
        ],
    },
)

