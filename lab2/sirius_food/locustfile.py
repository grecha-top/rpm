from locust import HttpUser, between, task


class MenuUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def get_menu(self):
        self.client.get("/menu/items", name="GET /menu/items")
