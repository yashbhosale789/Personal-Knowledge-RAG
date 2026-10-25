import pytest

import config
from api.core.exceptions import IngestError
from api.routers.ingest import _resolve_and_validate_path


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    root = tmp_path / "documents"
    root.mkdir()
    monkeypatch.setattr(config, "DATA_DIR", root)
    return root


def _pdf(path):
    path.write_bytes(b"%PDF-1.4 fake")
    return path


def test_valid_pdf_inside_data_dir(data_dir):
    pdf = _pdf(data_dir / "manual.pdf")
    assert _resolve_and_validate_path(str(pdf)) == pdf.resolve()


def test_uppercase_extension_is_accepted(data_dir):
    pdf = _pdf(data_dir / "MANUAL.PDF")
    assert _resolve_and_validate_path(str(pdf)) == pdf.resolve()


def test_subdirectory_is_allowed(data_dir):
    (data_dir / "sub").mkdir()
    pdf = _pdf(data_dir / "sub" / "m.pdf")
    assert _resolve_and_validate_path(str(pdf)) == pdf.resolve()


def test_traversal_out_of_data_dir_is_rejected(data_dir, tmp_path):
    outside = _pdf(tmp_path / "secret.pdf")
    with pytest.raises(IngestError, match="outside the allowed"):
        _resolve_and_validate_path(str(data_dir / ".." / outside.name))


def test_absolute_path_elsewhere_is_rejected(data_dir, tmp_path):
    outside = _pdf(tmp_path / "secret.pdf")
    with pytest.raises(IngestError, match="outside the allowed"):
        _resolve_and_validate_path(str(outside))


def test_symlink_escaping_data_dir_is_rejected(data_dir, tmp_path):
    outside = _pdf(tmp_path / "secret.pdf")
    link = data_dir / "link.pdf"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this platform")
    with pytest.raises(IngestError, match="outside the allowed"):
        _resolve_and_validate_path(str(link))


def test_non_pdf_is_rejected(data_dir):
    txt = data_dir / "notes.txt"
    txt.write_text("hello")
    with pytest.raises(IngestError, match="Only .pdf"):
        _resolve_and_validate_path(str(txt))


def test_missing_file_is_rejected(data_dir):
    with pytest.raises(IngestError, match="not found"):
        _resolve_and_validate_path(str(data_dir / "missing.pdf"))


def test_error_carries_the_offending_path(data_dir):
    with pytest.raises(IngestError) as exc:
        _resolve_and_validate_path(str(data_dir / "missing.pdf"))
    assert exc.value.status_code == 422
    assert exc.value.details["file_path"].endswith("missing.pdf")
