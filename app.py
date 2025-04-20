from training_script import TrainingSimulator
import pandas as pd


dataset = pd.read_csv('data/cleaned/dup_test.csv')
# state_attributes = ["current_soil_moisture", "temperature", "rain"]
state_attributes = ["current_soil_moisture", "temperature", "humidity", "rain", "salinity", "ph"]
state_size = len(state_attributes)
action_size = 6
# action_size = 11
n_episodes = 100
batch_size = 32
optimal_moisture = 50.0
irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}
# irrigation_map = {0: 0, 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80, 9: 90, 10: 100}

env = TrainingSimulator(dataset, state_attributes, state_size, action_size, n_episodes, batch_size, optimal_moisture, irrigation_map)
env.run()
env.score()