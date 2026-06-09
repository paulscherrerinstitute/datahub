import os
from setuptools import setup, find_packages
from pathlib import Path

PACKAGE_PREFIX = "psi-"
PACKAGE_NAME = "datahub"

version_ns = {}
exec(Path("datahub/_version.py").read_text(), version_ns)
__version__ = version_ns["__version__"]

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
        "numpy", "h5py", "requests", "python-dateutil", "pytz", "cbor2"
    ],
    entry_points={
        'console_scripts': [
            f'{PACKAGE_NAME} = {PACKAGE_NAME}.main:main',
        ],
    },
)