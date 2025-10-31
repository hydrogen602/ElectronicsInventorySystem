from sys import argv, stderr
from os import environ

from fastapi.testclient import TestClient


if __name__ == "__main__":
    if "ENV" not in environ:
        environ["ENV"] = "dev"

    from electronic_inv_sys import app

    client = TestClient(app)

    match argv:
        case [_, p]:
            out_path = p
        case _:
            print("Usage: python openapi.py <output path>", file=stderr)
            exit(1)

    response = client.get("/openapi.json")
    assert response.status_code == 200

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(response.text)
