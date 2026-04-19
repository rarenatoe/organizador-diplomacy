import json
import os
import sys

# Ensure the backend module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app


def export_openapi():
    # FastAPI automatically generates the schema
    openapi_schema = app.openapi()

    # Dump it to the root of the project
    output_path = os.path.join(os.path.dirname(__file__), "..", "openapi.json")
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)


if __name__ == "__main__":
    export_openapi()
