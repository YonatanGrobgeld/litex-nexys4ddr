import importlib.metadata as metadata
import sys


def main() -> int:
    try:
        import litex  # type: ignore

        litex_path = getattr(litex, "__file__", "(unknown)")
        try:
            litex_version = metadata.version("litex")
        except metadata.PackageNotFoundError:
            litex_version = "(unknown)"

        print("LiteX import OK")
        print(f"Python: {sys.executable}")
        print(f"LiteX version: {litex_version}")
        print(f"LiteX path: {litex_path}")
        return 0
    except Exception as exc:
        print(f"LiteX import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
