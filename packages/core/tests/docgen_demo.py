"""Demo: register node specs and output markdown docs."""

from deepeye.workflows.docgen import render_markdown
from deepeye.workflows.examples import build_registry


def main() -> None:
    registry = build_registry()
    markdown = render_markdown(registry.all())
    print(markdown)


if __name__ == "__main__":
    main()
