import os
import pathlib
from setuptools import setup, find_packages

PACKAGE_PREFIX = "psi-"
PACKAGE_NAME = "datahub"
VERSION_FILE = "package_version.txt"

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def version():
    p = pathlib.Path(__file__).parent.joinpath(PACKAGE_NAME).joinpath(VERSION_FILE)
    with open(p, "r") as f1:
        return f1.read()[:-1]


setup(
    name=PACKAGE_PREFIX + PACKAGE_NAME,
    version=version(),
    packages=find_packages(),
    author="Paul Scherrer Institute",
    author_email="daq@psi.ch",
    description="Utilities to retrieve data from PSI sources.",
    license="GPLv3",
    keywords="",
    url="https://github.com/paulscherrerinstitute/" + PACKAGE_NAME,
    long_description=read('Readme.md'),
    long_description_content_type="text/markdown",
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            f'{PACKAGE_NAME} = {PACKAGE_NAME}.main:main',
        ],
    },
    # Include the non-code file (package_version.txt) in the package folder
    include_package_data=True,
    package_data={
        # Include the text file in the package directory
        PACKAGE_NAME: [VERSION_FILE],
    },
)