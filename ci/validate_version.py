import os
import sys
import datahub

ref = os.environ["GITHUB_REF"]
is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

if is_manual:
    tag = os.environ.get("VERSION_TAG").lstrip("v")
    if not tag:
        print(f"Skipping version check")
        sys.exit(0)
else:
    tag = os.environ["GITHUB_REF_NAME"].lstrip("v")

pkg = datahub.__version__

if tag != pkg:
    print(f"ERROR: tag ({tag}) != package version ({pkg})")
    sys.exit(1)

print(f"Version match OK: {tag}")