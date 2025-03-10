from kafka import KafkaConsumer
import json
from datetime import datetime
import keras
from utils import *
import numpy as np

class VirtualGardenEnv:
    def __init__(self, kafka_topic, kafka_servers, end_of_season, trained_model, steps):
        self.consumer = KafkaConsumer(
            kafka_topic, 
            bootstrap_servers=kafka_servers, 
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        self.paused = False  # track if Kafka is paused
        self.missing_data_count = 0

        self.model = keras.models.load_model(trained_model)
        
        self.latest_sensors = {
            'soil_moisture': None,
            'soil_temperature': None,
            'soil_salinity': None,
            'soil_ph': None
        }
        self.last_received_time = None
        self.buffer = []
        self.EoS = end_of_season
        self.irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}
        self.steps = steps
        self.score_buffer = []
        self.M_opt = 35.0
    
    def pause_kafka(self):
        """Pause Kafka consumer to stop receiving new messages."""
        self.consumer.pause()
        self.paused = True
        print("Kafka consumption paused.")

    def resume_kafka(self, new_trained_model):
        """Resume Kafka consumer to start receiving messages again."""
        self.consumer.resume()
        self.paused = False
        self.model = keras.models.load_model(new_trained_model)
        print("Kafka consumption resumed.")

    def get_latest_state(self):
        """Retrieve the latest values from different sensors and return a complete state."""
        if self.paused:
            return None, True  # If paused, don't fetch new data

        for message in self.consumer:
            sensor_data = message.value
            current_time = datetime.now()
            
            if sensor_data:
                sensor_type = sensor_data.get("type")
                sensor_value = sensor_data.get("value")

                if sensor_type in self.latest_sensors:
                    self.latest_sensors[sensor_type] = sensor_value
                
                self.last_received_time = current_time
                
                if all(value is not None for value in self.latest_sensors.values()):
                    state = self.latest_sensors.copy()
                    self.buffer.append(state)
                    self.store_to_db(state, current_time)

                    self.latest_sensors = {key: None for key in self.latest_sensors}  # Reset buffer

                    return state, False  # False means real data
            
            elif self.missing_data_count < self.prediction_cutoff:
                self.missing_data_count += 1
                predicted_state = self.predict_next_state()
                return predicted_state, True  # True means predicted data
            
            else:
                return None, True  # No data available, beyond prediction cutoff
            
    def score(self, state, action=None):
        state = self.get_latest_state()
        if not action:
            self.score_buffer.append(state)
            return state
        else:
            self.score_buffer.append(state)
            score = 0
            for s in self.score_buffer:
                score += abs(s['soil_moisture'] - self.M_opt)
            self.score_buffer = [state]
            return score


    def predict_next_state(self, flag):
        """Simple trend-based prediction using last known values."""
        pass

    def store_to_db(self, state, current_time):
        """Store the latest sensor state in SQL db."""
        pass

    def run(self):
        """Continuously fetch state, either from Kafka or via prediction."""
        while True:
            state, is_predicted = self.get_latest_state()
            if state:
                print("Using {} data: {}".format("Predicted" if is_predicted else "Real", state))
            else:
                print("No data available, stopping predictions.")
                break
