"""Setup script for RAGLens."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="raglens",
    version="1.0.0",
    author="RAGLens",
    author_email="team@example.com",
    description="RAGLens — multi-agent RAG evaluation with LangGraph, AWS Bedrock, Ragas, and LLM-as-a-Judge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MaheshSugathan/raglens",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.12.0",
            "moto>=5.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rag-eval=cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml", "tests/data/*"],
    },
    keywords="raglens rag evaluation langchain langgraph aws bedrock ragas llm evaluation",
    project_urls={
        "Bug Reports": "https://github.com/MaheshSugathan/raglens/issues",
        "Source": "https://github.com/MaheshSugathan/raglens",
        "Documentation": "https://github.com/MaheshSugathan/raglens",
    },
)
