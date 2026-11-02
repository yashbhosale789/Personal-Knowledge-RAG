"""POST/GET/DELETE /documents (Phase 15.0 PR 2). Ingest, Chroma and Redis are faked;
tests/integration covers the real index."""

import threading

import pytest
from langchain_core.documents import Document

import config
from api.core.exceptions import IngestError
from api.routers import ingest as ingest_router
from src.ingestion.ingest import IngestRejected, ingest_file

PDF = b"%PDF-1.4 new"


@pytest.fixture
def docs(tmp_path, monkeypatch):
    root = tmp_path / "documents"
    root.mkdir()
    monkeypatch.setattr(config, "DATA_DIR", root)
    monkeypatch.setattr(ingest_router, "is_rate_limited", lambda key, bucket: False)
    return root


@pytest.fixture
def ingest(monkeypatch):
    """Fake ingest_file; set .error to make it raise. Records (path, max_chars, bytes on disk)."""

    class Fake:
        def __init__(self):
            self.calls: list = []
            self.error: Exception | None = None

        def __call__(self, path, *, max_chars=None):
            self.calls.append((path, max_chars, path.read_bytes()))
            if self.error:
                raise self.error
            return [Document(page_content="c")] * 3

    fake = Fake()
    monkeypatch.setattr(ingest_router, "ingest_file", fake)
    return fake


def upload(client, headers, name="manual.pdf", content=PDF):
    return client.post(
        "/documents",
        files={"file": (name, content, "application/pdf")},
        headers=headers,
    )


def leftovers(root):
    return sorted(p.name for p in root.iterdir())


# --- upload ------------------------------------------------------------------


def test_upload_requires_auth(client, docs, ingest):
    assert upload(client, {}).status_code == 401
    assert leftovers(docs) == []


def test_upload_saves_the_file_and_ingests_it_from_its_final_path(
    client, auth_headers, docs, ingest
):
    r = upload(client, auth_headers)
    assert r.status_code == 200
    assert r.json()["file_path"] == "manual.pdf"
    assert r.json()["chunks_created"] == 3
    path, max_chars, content = ingest.calls[0]
    assert path == (docs / "manual.pdf").resolve()  # `source` is the final path
    assert max_chars == config.MAX_UPLOAD_CHARS
    assert content == PDF
    assert leftovers(docs) == ["manual.pdf"]  # no .part or .bak left


def test_upload_over_the_size_cap_is_413_and_leaves_nothing(
    client, auth_headers, docs, ingest, monkeypatch
):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", len(PDF) - 1)
    r = upload(client, auth_headers)
    assert r.status_code == 413
    assert ingest.calls == []
    assert leftovers(docs) == []


def test_upload_at_the_size_cap_is_accepted(
    client, auth_headers, docs, ingest, monkeypatch
):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", len(PDF))
    assert upload(client, auth_headers).status_code == 200


@pytest.mark.parametrize("content", [b"", b"%PDF", b"hello world", b" %PDF-1.4"])
def test_upload_without_a_pdf_header_is_400(
    client, auth_headers, docs, ingest, content
):
    r = upload(client, auth_headers, content=content)
    assert r.status_code == 400
    assert ingest.calls == []
    assert leftovers(docs) == []


@pytest.mark.parametrize(
    "name",
    [
        "notes.txt",
        "manual.pdf.exe",
        "../manual.pdf",
        "../../etc/manual.pdf",
        "sub/manual.pdf",
        "sub\\manual.pdf",
        "..\\manual.pdf",
        "..",
        ".",
        "a" * 252 + ".pdf",
    ],
)
def test_upload_with_an_unsafe_or_wrong_name_is_rejected(
    client, auth_headers, docs, ingest, name
):
    r = upload(client, auth_headers, name=name)
    assert r.status_code == 400
    assert r.json()["detail"].startswith(
        "Invalid file name"
    )  # the name reached the check
    assert ingest.calls == []
    assert leftovers(docs) == []
    assert leftovers(docs.parent) == ["documents"]


# httpx percent-encodes control characters in a multipart filename, so test the check directly.
@pytest.mark.parametrize(
    "name", ["line\nbreak.pdf", "nul\x00.pdf", "tab\t.pdf", "", None]
)
def test_names_with_control_characters_or_no_name_are_rejected(name):
    with pytest.raises(IngestError) as e:
        ingest_router._check_name(name)
    assert e.value.status_code == 400


def test_upload_accepts_an_uppercase_extension(client, auth_headers, docs, ingest):
    assert upload(client, auth_headers, name="MANUAL.PDF").status_code == 200


def test_same_name_upload_replaces_the_old_file(client, auth_headers, docs, ingest):
    (docs / "manual.pdf").write_bytes(b"%PDF-1.4 old")
    r = upload(client, auth_headers)
    assert r.status_code == 200
    assert (docs / "manual.pdf").read_bytes() == PDF
    assert leftovers(docs) == ["manual.pdf"]


def test_rejected_upload_is_removed(client, auth_headers, docs, ingest):
    ingest.error = IngestRejected(
        "Document rejected: possible prompt injection detected (x)"
    )
    r = upload(client, auth_headers)
    assert r.status_code == 422
    assert "prompt injection" in r.json()["detail"]
    assert leftovers(docs) == []


def test_rejected_same_name_upload_keeps_the_old_file(
    client, auth_headers, docs, ingest
):
    (docs / "manual.pdf").write_bytes(b"%PDF-1.4 old")
    ingest.error = IngestRejected("No content could be extracted from this document.")
    r = upload(client, auth_headers)
    assert r.status_code == 422
    assert (docs / "manual.pdf").read_bytes() == b"%PDF-1.4 old"
    assert leftovers(docs) == ["manual.pdf"]


def test_unexpected_ingest_failure_restores_the_old_file_without_leaking_internals(
    client, auth_headers, docs, ingest
):
    (docs / "manual.pdf").write_bytes(b"%PDF-1.4 old")
    ingest.error = RuntimeError("secret internal detail")
    r = upload(client, auth_headers)
    assert r.status_code == 422
    assert "secret internal detail" not in r.text
    assert (docs / "manual.pdf").read_bytes() == b"%PDF-1.4 old"
    assert leftovers(docs) == ["manual.pdf"]


def test_upload_is_rate_limited(client, auth_headers, docs, ingest, monkeypatch):
    seen = []
    monkeypatch.setattr(
        ingest_router,
        "is_rate_limited",
        lambda key, bucket: seen.append(bucket) or True,
    )
    assert upload(client, auth_headers).status_code == 429
    assert seen == ["documents"]
    assert leftovers(docs) == []


@pytest.fixture
def busy():
    """Another thread holds the write lock, as a running ingest would."""
    taken, release = threading.Event(), threading.Event()

    def hold():
        with ingest_router._write_lock:
            taken.set()
            release.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    taken.wait(5)
    yield
    release.set()
    t.join()


def test_upload_while_another_write_runs_is_409_and_touches_nothing(
    client, auth_headers, docs, ingest, busy
):
    (docs / "manual.pdf").write_bytes(b"%PDF-1.4 old")
    r = upload(client, auth_headers)
    assert r.status_code == 409
    assert ingest.calls == []
    assert (docs / "manual.pdf").read_bytes() == b"%PDF-1.4 old"
    assert leftovers(docs) == ["manual.pdf"]


# --- list --------------------------------------------------------------------


def test_list_requires_auth(client, docs):
    assert client.get("/documents").status_code == 401


def test_list_shows_pdfs_on_disk_with_their_chunk_counts(
    client, auth_headers, docs, monkeypatch
):
    for name in ("b.pdf", "a.pdf", ".c.pdf.part", "notes.txt"):
        (docs / name).write_bytes(PDF)
    monkeypatch.setattr(
        ingest_router, "chunk_counts", lambda: {str((docs / "a.pdf").resolve()): 4}
    )
    r = client.get("/documents", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {
        "documents": [{"name": "a.pdf", "chunks": 4}, {"name": "b.pdf", "chunks": 0}]
    }


# --- delete ------------------------------------------------------------------


@pytest.fixture
def deletes(monkeypatch):
    calls = {"sources": [], "index_changed": 0}
    monkeypatch.setattr(
        ingest_router, "delete_by_source", lambda s: calls["sources"].append(s) or 5
    )
    monkeypatch.setattr(
        ingest_router,
        "index_changed",
        lambda: calls.__setitem__("index_changed", calls["index_changed"] + 1),
    )
    return calls


def test_delete_requires_auth(client, docs, deletes):
    (docs / "manual.pdf").write_bytes(PDF)
    assert client.delete("/documents/manual.pdf").status_code == 401
    assert (docs / "manual.pdf").exists()


def test_delete_removes_the_file_and_its_chunks(client, auth_headers, docs, deletes):
    (docs / "manual.pdf").write_bytes(PDF)
    r = client.delete("/documents/manual.pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["chunks_deleted"] == 5
    assert r.json()["file_path"] == "manual.pdf"
    assert deletes["sources"] == [str((docs / "manual.pdf").resolve())]
    assert deletes["index_changed"] == 1
    assert leftovers(docs) == []


def test_delete_of_a_missing_document_is_404(client, auth_headers, docs, deletes):
    assert client.delete("/documents/gone.pdf", headers=auth_headers).status_code == 404
    assert deletes["sources"] == []


@pytest.mark.parametrize("name", ["..%5Cmanual.pdf", "..", "notes.txt", "%2E%2E"])
def test_delete_with_an_unsafe_name_removes_nothing(
    client, auth_headers, docs, deletes, tmp_path, name
):
    (docs / "manual.pdf").write_bytes(PDF)
    (tmp_path / "manual.pdf").write_bytes(PDF)
    (tmp_path / "notes.txt").write_bytes(PDF)
    r = client.delete(f"/documents/{name}", headers=auth_headers)
    assert r.status_code in (400, 404, 405)
    assert deletes["sources"] == []
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "documents",
        "manual.pdf",
        "notes.txt",
    ]
    assert leftovers(docs) == ["manual.pdf"]


def test_delete_is_rate_limited(client, auth_headers, docs, deletes, monkeypatch):
    (docs / "manual.pdf").write_bytes(PDF)
    monkeypatch.setattr(ingest_router, "is_rate_limited", lambda key, bucket: True)
    assert (
        client.delete("/documents/manual.pdf", headers=auth_headers).status_code == 429
    )
    assert (docs / "manual.pdf").exists()


def test_delete_while_another_write_runs_is_409(
    client, auth_headers, docs, deletes, busy
):
    (docs / "manual.pdf").write_bytes(PDF)
    assert (
        client.delete("/documents/manual.pdf", headers=auth_headers).status_code == 409
    )
    assert (docs / "manual.pdf").exists()


# --- the text cap inside ingest_file -------------------------------------------


def test_ingest_file_rejects_too_much_text_before_deleting_anything(
    tmp_path, monkeypatch
):
    deleted = []
    monkeypatch.setattr(
        "src.ingestion.loader.load_documents",
        lambda p: [Document(page_content="x" * 11, metadata={})],
    )
    monkeypatch.setattr("src.vectorstore.store.delete_by_source", deleted.append)
    with pytest.raises(IngestRejected, match="too long"):
        ingest_file(tmp_path / "big.pdf", max_chars=10)
    assert deleted == []
