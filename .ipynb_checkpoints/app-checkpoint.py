from training_script import TrainingSimulator
import pandas as pd


dataset = pd.read_csv('data/cleaned/real_dat/dat_1_month.csv')
# state_attributes = ["current_soil_moisture", "temperature", "rain"]
state_attributes = ["current_soil_moisture", "temperature", "humidity", "rain", "salinity", "ph"]
state_size = len(state_attributes)
# action_size = 6
# action_size = 11
action_size = 16
n_episodes = 1000
batch_size = 32
optimal_moisture = 50.0
# irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}
# irrigation_map = {0: 0, 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80, 9: 90, 10: 100}
irrigation_map = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 14, 8: 16, 9: 18, 10: 20, 11: 22, 12: 24, 13: 26, 14: 28, 15: 30}

env = TrainingSimulator(dataset, state_attributes, state_size, action_size, n_episodes, batch_size, optimal_moisture, irrigation_map)
env.run()
# env.score()