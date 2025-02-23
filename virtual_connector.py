from kafka import KafkaConsumer
from pymongo import MongoClient
import json
from datetime import datetime

class VirtualGardenEnv:
    def __init__(self, kafka_topic, kafka_servers, mongo_uri, db_name, collection_name, prediction_cutoff=5):
        # làm theo kafka trên mạng
        self.consumer = KafkaConsumer(
            kafka_topic, 
            bootstrap_servers=kafka_servers, 
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        # for example for storing
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[db_name]
        self.collection = self.db[collection_name]
        
        self.paused = False  # Track if Kafka is paused
        self.prediction_cutoff = prediction_cutoff
        self.missing_data_count = 0
        
        self.latest_sensors = {
            'soil_moisture': None,
            'soil_temperature': None,
            'soil_salinity': None,
            'soil_ph': None
        }
        self.last_received_time = None
    
    def pause_kafka(self):
        """Pause Kafka consumer to stop receiving new messages."""
        self.consumer.pause()
        self.paused = True
        print("Kafka consumption paused.")

    def resume_kafka(self):
        """Resume Kafka consumer to start receiving messages again."""
        self.consumer.resume()
        self.paused = False
        print("Kafka consumption resumed.")

    def get_latest_state(self):
        """Retrieve the latest values from different sensors and return a complete state."""
        if self.paused:
            return None, True  # If paused, don't fetch new data

        for message in self.consumer:
            sensor_data = message.value
            current_time = datetime.utcnow()
            
            if sensor_data:
                sensor_type = sensor_data.get("type")  # Example: "soil_moisture"
                sensor_value = sensor_data.get("value")  # Example: 23.5

                if sensor_type in self.latest_sensors:
                    self.latest_sensors[sensor_type] = sensor_value
                
                self.last_received_time = current_time
                
                if all(value is not None for value in self.latest_sensors.values()):
                    state = self.latest_sensors.copy()
                    self.store_to_db(state, current_time)

                    self.latest_sensors = {key: None for key in self.latest_sensors}  # Reset buffer

                    return state, False  # False means real data
            
            elif self.missing_data_count < self.prediction_cutoff:
                self.missing_data_count += 1
                predicted_state = self.predict_next_state()
                return predicted_state, True  # True means predicted data
            
            else:
                return None, True  # No data available, beyond prediction cutoff

    def predict_next_state(self):
        """Simple trend-based prediction using last known values."""
        trend_factor = 0.98  
        return {
            key: value * trend_factor if value is not None else 0 
            for key, value in self.latest_sensors.items()
        }

    def store_to_db(self, state, timestamp):
        """Store the latest sensor state in MongoDB."""
        self.collection.insert_one({
            'timestamp': timestamp,
            'sensor_data': state
        })

    def run(self):
        """Continuously fetch state, either from Kafka or via prediction."""
        while True:
            state, is_predicted = self.get_latest_state()
            if state:
                print("Using {} data: {}".format("Predicted" if is_predicted else "Real", state))
            else:
                print("No data available, stopping predictions.")
                break
