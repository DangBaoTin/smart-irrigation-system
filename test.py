from deepQ_agent import deepQ_agent
from utils__ import *
from sklearn.linear_model import LinearRegression

# Khởi tạo môi trường
import keras
import numpy as np
import pandas as pd

state_attributes = ["current_soil_moisture", "temperature", "humidity", "rain", "salinity", "ph"]

state_size = len(state_attributes)
action_size = 6

irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}

# Load your cleaned dataset
train_df = pd.read_csv("data/cleaned/sandy_train_data.csv")  # Replace with your file path
test_df = pd.read_csv("data/cleaned/sandy_test_data.csv")

# Feature and target selection
features = ["current_soil_moisture", "temperature", "humidity", "rain", "salinity", "ph"]
target = ["irrigation_amount"]

# MODELS FOR MIMIC THE ENVIRONMENT
env_model = LinearRegression()

X_COLUMNS = np.append(features, "irrigation_amount")
Y_COLUMNS = ['next_smoist_0']

X = train_df[X_COLUMNS]
y = train_df[Y_COLUMNS]

env_model.fit(X, y)

# Load agent đã train
saved_model = keras.models.load_model("saved_models/agent_action6_ep1000dat100_2025-04-28_16-44-41.keras")
test_agent = deepQ_agent(state_size, action_size, saved_model, 0.0)
n_timesteps = len(test_df) - 1
total_reward = 0

metrics = []
ep_rewards = 0

for i in range(n_timesteps):
    # Lấy state hiện tại đưa vào predict
    test_state = test_df.iloc[i][state_attributes].values

    test_action = test_agent.make_decision(test_state)
    irrigation_amount = irrigation_map[test_action]  # Map irrigation to action index

    # Observe reward and next moist
    next_state_moisture = env_model.predict([np.append(test_state, irrigation_amount)])[0]
    next_soil_moist_arr = gen_smoist_array(next_state_moisture, irrigation_amount, 0.3, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    reward = test_get_reward(next_soil_moist_arr)
    

    metrics.append({
        'irrigation_amount': irrigation_amount,
        'reward': reward,
        })
    
    # Action vào env và lấy thông số
    total_reward += (reward / len(test_df))

metrics_df = pd.DataFrame(metrics, columns = ['irrigation_amount', 'reward'])
metrics_df.to_csv('results/deepQ_result.csv')

print(total_reward)