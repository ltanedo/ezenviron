from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ezenviron",
    version="0.2.0",
    author="ltanedo",
    author_email="lloydtan@buffalo.edu",
    description="A python module enabling crud on windows user env vars enabling safe API development",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ltanedo/ezenviron",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        # Add dependencies here as needed
    ],
)
