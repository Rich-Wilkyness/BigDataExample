"""Build a reproducible Lambda archive without downloading dependencies."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def main():
    source = Path(__file__).resolve().parent
    for filename, archive_name, handler_name in [
        ("prepare_batch.py", "prepare-batch.zip", "prepare_batch.py"),
        ("ingestion.py", "ingestion.zip", "lambda_function.py"),
    ]:
        target = source.parent / "terraform/.build" / archive_name
        target.parent.mkdir(parents=True, exist_ok=True)
        info = ZipInfo(handler_name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        with ZipFile(target, "w") as archive:
            archive.writestr(info, (source / filename).read_bytes())
        print(target)


if __name__ == "__main__":
    main()
