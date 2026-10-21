# Using the Vega SDKs in VS Code

The kits are ordinary Python packages, so they work in VS Code as they are. There is no VS Code extension.

## 1. Install

You need Python 3.10 or newer. In the VS Code terminal, create a virtual environment, then install the kits **in dependency order with `--no-deps`**. The kits are not on PyPI, so pip cannot look their family dependencies up by name; installing them in order from GitHub is what makes them resolve.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$o = "https://github.com/jasonblasiak868-code"
pip install --no-deps git+$o/vega-custody-sdk
pip install --no-deps git+$o/vega-governance-jacket-sdk
pip install --no-deps git+$o/vega-two-gate-sdk
pip install cryptography
```

Install any other kit the same way. The order that always works is the layer order in [ORGANISM.md](ORGANISM.md): custody first, then jacket, then the kits that list them as requirements. Each kit's README names what it depends on. On macOS or Linux, activate with `source .venv/bin/activate` and use a shell variable `o=https://github.com/jasonblasiak868-code`, then `pip install --no-deps git+$o/vega-custody-sdk`.

Do not install a kit with a plain `pip install vega-custody-sdk`. That name is not published here, and installing a package of that name from a package index you do not control is not safe.

## 2. Point VS Code at the environment

Press `Ctrl+Shift+P`, choose **Python: Select Interpreter**, and pick the `.venv` you made. `import vega_custody`, `import vega_jacket` and the other package names then work in any script or notebook.

## 3. Run the tests

Each kit's tests are plain `unittest` files in its `tests` folder. Clone the kit and run, for example:

```powershell
git clone https://github.com/jasonblasiak868-code/vega-custody-sdk
cd vega-custody-sdk
python -m unittest discover -s tests
```

VS Code's Testing panel can discover the same files: **Python: Configure Tests**, choose `unittest`, set the folder to `tests`.

## 4. Read the docs while you work

Every kit has a README (quick start), SPEC, ARCHITECTURE (diagrams of where it fails closed) and CAPABILITIES. VS Code previews Markdown and Mermaid diagrams with the built-in Markdown preview and the Markdown Preview Mermaid Support extension.

## What this is not

It is not an editor extension and it does not put your editor's AI behind the gates. The kits are libraries you call from your own code. See each README for what the kit does and does not do, and the LICENSE for the terms.
