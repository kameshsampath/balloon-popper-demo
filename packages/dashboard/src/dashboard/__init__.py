# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

from streamlit.web import cli as stcli
import sys
from pathlib import Path
def main():
    path = Path(__file__).resolve().parent.joinpath("streamlit_app.py")
    sys.argv = ["streamlit", "run", str(path)]
    sys.exit(stcli.main())

