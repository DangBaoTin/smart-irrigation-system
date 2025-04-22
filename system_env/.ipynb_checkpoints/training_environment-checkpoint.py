from utils__ import *
from rain import *
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

import numpy as np
import math

class TrainingEnvironment:
    def __init__(self, dataset, state_attributes, optimal_moisture, irrigation_map):
        self.dataset = dataset
        self.state_attributes = state_attributes
        self.optimal_moisture = optimal_moisture

        self.state_data = self.dataset[state_attributes].values
        self.current_index = 0                  # track position in dataset
        self.EoS = len(self.dataset) - 1        # length of dataset (End of Season - EoS)

        self.model = LinearRegression()
        self.irrigation_map = irrigation_map

        self.current_state = self.state_data[0]
    
    def fit(self):
        # Reshape the data
        df = self.dataset
        # df["soil_moisture_after"] = df["current_soil_moisture"].shift(-1)
        # df["soil_moisture_after"].fillna(-1, inplace=True)
        # df.drop(df.index[-1], inplace=True)

        # X_COLUMNS = ['temperature','humidity', 'pH', 'current_soil_moisture', 'irrigation_amount', 'duration']
        X_COLUMNS = np.append(self.state_attributes, "irrigation_amount")
        # Y_COLUMNS = ['soil_moisture_after']
        # Y_COLUMNS = [col for col in df.columns if col.startswith("next_smoist_")]
        Y_COLUMNS = ['next_smoist_0']

        X = df[X_COLUMNS].values
        y = df[Y_COLUMNS]

        self.model.fit(X, y)

    def reset(self):
        """Reset the environment to the start of the dataset."""
        self.current_index = 0
        self.current_state = self.state_data[0]
        return self.state_data[0]
    
    def step(self, action):
        """Move to the next state based on dataset order."""
        """[current_soil_moisture, ..., irrigation_amount]"""
        irrigation_amount = self.irrigation_map[action]
        next_state_moisture = self.model.predict([np.append(self.current_state, irrigation_amount)])[0]
        # reward = compute_reward(self.current_state[0], next_state_moisture, 1)
        # reward = get_reward(self.current_state[0], irrigation_amount, 40, 50)
        next_soil_moist_arr = gen_smoist_array(next_state_moisture, irrigation_amount, 0.3, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        # reward = -math.log(abs(test_get_reward(next_soil_moist_arr)))
        reward = test_get_reward(next_soil_moist_arr)
        # reward = get_reward(self.current_state[0], irrigation_amount)
        next_state = self.state_data[self.current_index + 1]
        # next_state[0] = next_state_moisture
        # next_state[0] = next_soil_moist_arr[-1]
        # print(f"Next moist: {next_soil_moist_arr}, reward: {reward}")
        self.current_state = next_state
        self.current_index += 1
        done = self.current_index >= self.EoS
        return next_state, reward, done
    
    def get_total_timesteps(self):
        # """Return the total number of timesteps."""
        return self.EoS