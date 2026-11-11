"""Create a paid order and prove its distributed trace through Jaeger."""
import json
import os
import time
from uuid import uuid4

import httpx


def main() -> None:
    correlation_id = os.getenv("LAB9_CORRELATION_ID", f"lab9-{uuid4()}")
    api = httpx.Client(base_url=os.getenv("LAB9_API_URL", "http://127.0.0.1:8000"))
    token = api.post(
        "/auth/login",
        json={"email": "demo.admin@example.com", "password": "demo-password"},
    ).raise_for_status().json()["access_token"]
    item_id = api.get("/menu/items").raise_for_status().json()[0]["id"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": correlation_id,
    }
    created = api.post(
        "/orders/create",
        headers=headers,
        json={"item_id": item_id, "quantity": 1},
    ).raise_for_status().json()
    api.post(f"/orders/{created['order_id']}/pay", headers=headers).raise_for_status()

    jaeger_url = os.getenv("LAB9_JAEGER_URL", "http://jaeger:16686")
    for _ in range(15):
        traces = httpx.get(
            f"{jaeger_url}/api/traces",
            params={
                "service": "sirius-api",
                "lookback": "1h",
                "limit": 20,
                "tags": json.dumps({"correlation_id": correlation_id}),
            },
        ).raise_for_status().json()["data"]
        for trace in traces:
            services = sorted(
                {process["serviceName"] for process in trace["processes"].values()}
            )
            if {"sirius-api", "sirius-outbox", "sirius-kitchen"}.issubset(services):
                print(
                    json.dumps(
                        {
                            "order_id": created["order_id"],
                            "correlation_id": correlation_id,
                            "trace_id": trace["traceID"],
                            "services": services,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return
        time.sleep(1)
    raise SystemExit("Distributed trace was not exported to Jaeger in 15 seconds")


if __name__ == "__main__":
    main()
