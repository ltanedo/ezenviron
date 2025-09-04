from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ezenviron",
    version="0.3.0",
    author="ltanedo",
    author_email="lloydtan@buffalo.edu",
    description="A python module enabling CRUD on Windows user env vars for safe API development",
    url="https://github.com/ltanedo/ezenviron",
    license="MIT",
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "ezenviron=ezenviron.__init__:main",
        ],
    },
    install_requires=[],
    keywords=["windows", "environment", "variables", "cli", "utilities"],
    classifiers=["Development Status :: 3 - Alpha", "Intended Audience :: Developers", "License :: OSI Approved :: MIT License", "Operating System :: Microsoft :: Windows", "Programming Language :: Python :: 3", "Programming Language :: Python :: 3.7", "Programming Language :: Python :: 3.8", "Programming Language :: Python :: 3.9", "Programming Language :: Python :: 3.10", "Programming Language :: Python :: 3.11"],
    project_urls={"Bug Reports": "https://github.com/ltanedo/ezenviron/issues","Source": "https://github.com/ltanedo/ezenviron","Documentation": "https://github.com/ltanedo/ezenviron#readme"},
    long_description=long_description,
    packages=find_packages(),
)
