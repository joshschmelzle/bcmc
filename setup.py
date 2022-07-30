# -*- coding: utf-8 -*-
#
# setup.py for bcmc

import os

try:
    from setuptools import find_packages, setup
except:
    raise ImportError("setuptools is required to install bcmc ...")

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, "bcmc", "__version__.py")) as f:
    exec(f.read(), about)

try:
    with open("README.md", "r") as f:
        readme = f.read()
except FileNotFoundError:
    long_description = about["__description__"]

extras = {
    "test": [
        "tox",
        "black",
        "isort",
        "autoflake",
        "mypy",
        "pytest",
        "pytest-cov",
        "coverage-badge",
    ],
}

setup(
    name=about["__title__"],
    version=about["__version__"],
    packages=find_packages(exclude=("tests", "test")),
    description=about["__description__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    url=about["__url__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    python_requires=">=2.7",
    extras_require=extras,
    entry_points={"console_scripts": ["bcmc=bcmc.__main__:main"]},
    license=about["__license__"],
    platforms=["win32", "linux", "macos"],
    keywords=[
        "bcmc",
        "broadcast",
        "multicast",
    ],
    classifiers=[
        "Natural Language :: English",
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
        "Topic :: Utilities",
        "Topic :: System :: Networking",
        "Topic :: System :: Networking :: Monitoring",
    ],
)
