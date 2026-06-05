from setuptools import setup, find_packages

setup(
    name="horizonx-tracker",
    version="0.1.0",
    description="Lightweight ML experiment tracker for the HorizonX trading system",
    author="HorizonX",
    python_requires=">=3.10",
    packages=find_packages(exclude=["tests*", "examples*"]),
    install_requires=[
        "streamlit>=1.30",
        "pandas>=2.0",
        "plotly>=5.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-cov"],
    },
)
