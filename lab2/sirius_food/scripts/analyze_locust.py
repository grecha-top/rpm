"""Convert Locust CSV statistics into a compact lab report."""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path


def as_float(row: dict, key: str) -> float:
    return float(row.get(key) or 0)


def main(source: str, destination: str) -> None:
    with Path(source).open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["Name"] != "Aggregated"]
    if not rows:
        raise SystemExit("Locust statistics contain no endpoints")

    bottleneck = max(rows, key=lambda row: as_float(row, "95%"))
    total_requests = sum(int(row["Request Count"]) for row in rows)
    total_failures = sum(int(row["Failure Count"]) for row in rows)
    generated_at = datetime.now(timezone.utc).isoformat()

    lines = [
        "# Практическая работа №10 — нагрузочный тест",
        "",
        f"Отчёт сформирован: `{generated_at}`.",
        "",
        f"Всего запросов: **{total_requests}**, ошибок: **{total_failures}**.",
        "",
        "| Endpoint | Requests | Failures | RPS | Avg, ms | p95, ms | p99, ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {Name} | {Request Count} | {Failure Count} | {Requests/s} | "
            "{Average Response Time} | {95%} | {99%} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Вывод",
            "",
            f"Узкое место по p95: **{bottleneck['Name']}** "
            f"({bottleneck['95%']} мс). Это endpoint с наибольшей задержкой "
            "на 95-м процентиле в смешанном профиле 70/20/10.",
            "",
            "Исходные результаты: `results/lab10-current_stats.csv` и "
            "`results/lab10-current.html`.",
        ]
    )
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
