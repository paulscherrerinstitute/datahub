import os
import sys
import datahub

ref = os.environ["GITHUB_REF"]

if not ref.startswith("refs/tags/"):
    print(f"Skipping version check for {ref}")
    sys.exit(0)

tag = os.environ["GITHUB_REF_NAME"].lstrip("v")
pkg = datahub.__version__

if tag != pkg:
    print(f"ERROR: tag ({tag}) != package version ({pkg})")
    sys.exit(1)

print("Version match OK")