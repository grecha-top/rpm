import os

from locust import HttpUser, between, task


class SiriusUser(HttpUser):
    """70% menu, 20% card, 10% order creation."""

    wait_time = between(1, 3)
    item_id = int(os.getenv("LOCUST_ITEM_ID", "1"))

    def on_start(self):
        token = os.getenv("LOCUST_ACCESS_TOKEN", "")
        self.auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(7)
    def get_menu(self):
        self.client.get("/menu/items", name="GET /menu/items")

    @task(2)
    def get_menu_item(self):
        self.client.get(
            f"/menu/items/{self.item_id}",
            name="GET /menu/items/{id}",
        )

    @task(1)
    def create_order(self):
        if not self.auth_headers:
            return
        self.client.post(
            "/orders/create",
            name="POST /orders/create",
            headers=self.auth_headers,
            json={"item_id": self.item_id, "quantity": 1},
        )
