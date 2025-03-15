from utils import *
from rain import *
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

import numpy as np
import pandas as pd

class TrainingEnvironment:
    def __init__(self, dataset, state_attributes, optimal_moisture, timestep):
        self.df = dataset
        self.state_attributes = state_attributes
        self.optimal_moisture = optimal_moisture
        self.timestep = timestep

        self.state_data = self.df[state_attributes].values
        self.current_index = 0              # track position in dataset
        self.EoS = len(self.df) - 1         # length of dataset (End of Season - EoS)

        self.model = LinearRegression()
        self.irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}

        self.current_state = np.append(self.state_data[0], call_rain())
    
    def fit(self):
        X_COLUMNS = ['temperature','humidity', 'pH', 'current_soil_moisture', 'irrigation_amount', 'duration']
        Y_COLUMNS = ['soil_moisture_after']

        X = self.df[X_COLUMNS]
        y = self.df[Y_COLUMNS]

        self.model.fit(X, y)

    def reset(self):
        """Reset the environment to the start of the dataset."""
        self.current_index = 0
        return np.append(self.state_data[0], call_rain())
    
    def step(self, action):
        """Move to the next state based on dataset order."""
        irrigation_amount = self.irrigation_map[action]
        next_state_moisture = self.model.predict(self.current_state)
        next_state = np.append(self.state_data[self.current_index + 1], [irrigation_amount, next_state_moisture])
        reward = compute_reward(self.state_data['current_soil_moisture'][self.current_index], next_state_moisture, 1)

        if self.current_index >= self.n_timesteps:
            return None, 0, True  # End of dataset
        
        # sample = self.data[self.current_index]
        # next_sample = self.data[self.current_index + 1]
        # next_state = self.extract_state(next_sample)
        # reward = self.get_reward(sample, action)
        self.current_state = next_state
        self.current_index += 1
        done = self.current_index >= self.EoS
        
        return next_state, reward, done
    
    def get_total_timesteps(self):
        """Return the total number of timesteps."""
        return self.EoS