import random
from faker import Faker

fake = Faker()

class User:
    def __init__(self, user_id):
        # user details
        self.user_id = user_id
        self.home_lat = random.uniform(25, 48)  # latitude in degrees
        self.home_lon = random.uniform(-125, -70)  # longitude in degrees
        self.avg_spending = random.uniform(20, 200)  # average spending in USD
        self.device_id = fake.uuid4()  # device ID
        # last transaction details
        self.last_lat = self.home_lat
        self.last_lon = self.home_lon
        self.last_timestamp = None

