import random
from locust import HttpUser, HttpLocust, TaskSet, task, between


class UserLoadTest(HttpUser):
    wait_time = between(5, 9)

    @task
    def users_api(self):
        self.client.get("/api/v1/auth/users/user-list/")
        # self.client.get("/world")

    # @task(3)
    # def view_post(self):
    #     item_id = random.randint(1, 10000)
    #     self.client.get(f"/item?id={item_id}", name="/item")

    # def on_start(self):
    #     self.client.post("/login", {"username": "foo", "password": "bar"})


class UserTasks(TaskSet):
    wait_time = between(5, 9)

    @task
    def users_api(self):
        self.client.get("/api/v1/auth/users/user-list/")
