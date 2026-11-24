from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_every_operation_is_described(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path, methods in paths.items():
        for method, operation in methods.items():
            name = f"{method.upper()} {path}"
            assert operation.get("operationId"), name
            assert operation.get("description"), name
            assert "\n" not in operation["description"].strip(), name
            for parameter in operation.get("parameters", []):
                assert parameter["required"], name


def test_request_bodies_have_no_optional_fields(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for name, schema in schemas.items():
        if name.endswith("In"):
            assert set(schema["required"]) == set(schema["properties"]), name


def test_the_answer_key_stays_out():
    sources = [
        path
        for folder in ("backend", "agent")
        for path in (ROOT / folder).rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".md"}
        and "tests" not in path.parts
    ]
    assert sources
    for path in sources:
        assert "evals" not in path.read_text(encoding="utf-8"), path
