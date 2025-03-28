from training_script import TrainingSimulator
import pandas as pd


dataset = pd.read_csv('data/cleaned/tested.csv')
state_attributes = ["current_soil_moisture", "temperature", "rain"]
state_size = len(state_attributes)
action_size = 6
n_episodes = 100
batch_size = 32
optimal_moisture = 50.0
irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}

env = TrainingSimulator(dataset, state_attributes, state_size, action_size, n_episodes, batch_size, optimal_moisture, irrigation_map)
env.run()
env.score()