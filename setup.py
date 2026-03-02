import os
from setuptools import setup, find_packages
from datahub._version import __version__

PACKAGE_PREFIX = "psi-"
PACKAGE_NAME = "datahub"


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def version():
    return __version__

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
)