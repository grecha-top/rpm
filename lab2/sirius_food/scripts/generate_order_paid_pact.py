"""Generate the committed Pact V4 contract from the kitchen consumer definition."""
from pathlib import Path

from tests.contract.order_paid_pact import build_order_paid_pact


def main() -> None:
    output = Path(__file__).parents[1] / "tests" / "contract" / "pacts"
    output.mkdir(parents=True, exist_ok=True)
    build_order_paid_pact().write_file(output, overwrite=True)
    print(f"Pact written to {output}")


if __name__ == "__main__":
    main()
