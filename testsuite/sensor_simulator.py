import zmq
import time
import random

import numpy as np
import pandas as pd

# Create a ZeroMQ context
context = zmq.Context()
socket = context.socket(zmq.PUB)  # Publisher socket
socket.bind("tcp://*:5555")  # Bind to port 5555

test_data = pd.read_csv('lab4/test.csv')

humi_seq_test = np.array(test_data['Relative_humidity_room'])
co2_seq_test = np.array(test_data['CO2_room'])


print("Sensor Simulator started. Sending data...")

try:
    while True:
        # Simulate sensor data
        random_num = random.randint(0, len(test_data)-4)
        
        humidity = humi_seq_test[random_num]
        co2 = co2_seq_test[random_num]

        sensor_data = {
            "humidity": humidity,
            "co2": co2,
        }

        # Send data as a string
        socket.send_json(sensor_data)
        print(f"Sent: {sensor_data}")

        time.sleep(2)  # Adjust frequency of sending data
except KeyboardInterrupt:
    print("\nSensor Simulator stopped.")
finally:
    socket.close()
    context.term()
