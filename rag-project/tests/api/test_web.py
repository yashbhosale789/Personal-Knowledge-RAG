"""The React build is served at / and /assets without changing any API path (Phase 14.1)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import mount_web
from api.routers import query


def test_serves_the_build_and_leaves_api_paths_alone(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (tmp_path / "assets" / "index-abc.js").write_text(
        "console.log(1)", encoding="utf-8"
    )
    app = FastAPI()
    app.include_router(query.router)
    mount_web(app, tmp_path)
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200
    assert '<div id="root">' in index.text
    assert index.headers["cache-control"] == "no-cache"
    assert client.get("/assets/index-abc.js").text == "console.log(1)"
    assert client.get("/query").status_code == 405
    assert client.get("/nope").json() == {"detail": "Not Found"}
