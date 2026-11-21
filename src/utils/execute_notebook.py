"""Execute a notebook with the current Python environment and save its outputs."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager


def execute(path):
    path = Path(path).resolve()
    notebook = nbformat.read(path, as_version=4)
    # Use a temporary kernel spec so execution never depends on a global kernel.
    with tempfile.TemporaryDirectory(prefix="prison-notebook-") as temporary:
        directory = Path(temporary)
        kernel = directory / "kernels" / "python3"
        kernel.mkdir(parents=True)
        spec = {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "India Prison Analytics", "language": "python"}
        (kernel / "kernel.json").write_text(json.dumps(spec))
        manager = AsyncKernelManager(kernel_name="python3", kernel_spec_manager=KernelSpecManager(
            kernel_dirs=[str(directory / "kernels")]), connection_file=str(directory / "connection.json"))
        environment = dict(os.environ, IPYTHONDIR=str(directory / "ipython"),
                           JUPYTER_RUNTIME_DIR=str(directory / "runtime"))
        client = NotebookClient(notebook, km=manager, timeout=300, startup_timeout=60, allow_errors=False,
                                resources={"metadata": {"path": str(path.parent)}})
        client.execute(env=environment)
        nbformat.validate(notebook)
        nbformat.write(notebook, path)
    print(f"Executed and saved {path.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    execute(parser.parse_args().notebook)


if __name__ == "__main__":
    main()
