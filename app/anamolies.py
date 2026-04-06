import random
from faker import Faker
import math
from datetime import datetime

fake = Faker()

# calculate the distance between two points on the earth's surface
def haversine(lat1, lon1, lat2, lon2):
    R = 6371 # radius of the earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# calculate the number of hours between two timestamps
def hours_between(timestamp1, timestamp2):
    return abs(timestamp1 - timestamp2).total_seconds() / 3600 # in hours

# inject anamoly into the transaction
def inject_anamoly(transaction, user):
    anamoly_type = random.choices(
        ['none', 'high_amount', 'impossible_travel', 'rapid_fire', 'new_device'],
        weights=[0.85, 0.05, 0.03, 0.04, 0.03],
        k=1,
    )[0]

    current_timestamp = datetime.now()

    if anamoly_type == 'high_amount':
        if 'amount' in transaction:
            transaction['amount'] = round(transaction['amount'] * 10, 2)
        transaction['fraud_flag'] = 'high_amount'
    
    elif anamoly_type == 'impossible_travel' and user.last_timestamp:
        #force the transaction to be outside the user's home range
        new_lat = random.uniform(35, 40) # latitude in degrees
        new_lon = random.uniform(130, 140) # longitude in degrees (intentionally far)

        # check if the transaction is physically possible
        distance = haversine(user.last_lat, user.last_lon, new_lat, new_lon)
        hours = hours_between(user.last_timestamp, current_timestamp)

        speed = distance / max(hours, 0.01) # avoid division by zero

        transaction['latitude'] = new_lat
        transaction['longitude'] = new_lon
        if speed > 600:
            transaction['fraud_flag'] = 'impossible_travel'

    elif anamoly_type == 'rapid_fire' and user.last_timestamp:
        hours = hours_between(user.last_timestamp, current_timestamp)
        if hours < (1 / 60):  # < 1 minute
            transaction['fraud_flag'] = 'rapid_fire'
        
    elif anamoly_type == 'new_device':
        transaction['device_id'] = fake.uuid4()
        transaction['fraud_flag'] = 'new_device'

    
    user.last_lat = transaction['latitude']
    user.last_lon = transaction['longitude']
    user.last_timestamp = current_timestamp

    transaction['anamoly_type'] = anamoly_type

    return transaction, anamoly_type
