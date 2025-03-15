import numpy as np

def target_moisture(t, M_opt=35.0, decay_rate=0.05):
    """Compute the target moisture at time t based on exponential decay."""
    return M_opt * np.exp(-decay_rate * t)

# def get_reward(row, optimal_min=30.0, optimal_max=40.0):
def get_reward(soil_moisture, irrigation, optimal_min=30.0, optimal_max=40.0):
    """
    Calculates the reward for each row based on the soil moisture and irrigation amount.
    
    Parameters:
    row (Series): Row of the DataFrame.
    optimal_min (float): Minimum of the optimal soil moisture range.
    optimal_max (float): Maximum of the optimal soil moisture range.
    
    Returns:
    float: Reward based on the proximity of soil moisture to the optimal range.
    """
    # soil_moisture = row['soil_moisture']
    # irrigation = row['irrigated']
    
    # Simulate the new soil moisture after irrigation
    new_soil_moisture = soil_moisture + irrigation
    
    # Define the reward based on how close the new soil moisture is to the optimal range
    if optimal_min <= new_soil_moisture <= optimal_max:
        reward = 1.0  # High reward for being within the optimal range
    else:
        # Penalize based on the distance from the optimal range
        reward = -abs(new_soil_moisture - (optimal_min + optimal_max) / 2) / 10.0
    
    return reward

def compute_reward(M_t, M_t_next, t, M_opt=35.0, decay_rate=0.05):
    """
    Compute the reward based on the integral of deviation from the target moisture.

    Parameters:
    - M_t: Current soil moisture level
    - M_t_next: Next soil moisture after irrigation
    - t: Time step
    - M_opt: Optimal soil moisture level
    - decay_rate: Rate at which soil moisture naturally decreases

    Returns:
    - Reward value (higher when moisture is close to the target)
    """
    M_target_t = target_moisture(t, M_opt, decay_rate)  # Ideal moisture at time t
    M_target_next = target_moisture(t+1, M_opt, decay_rate)  # Ideal moisture at next step

    # Compute the integral approximation (discrete sum)
    deviation_t = abs(M_t - M_target_t)
    deviation_next = abs(M_t_next - M_target_next)

    # Trapezoidal approximation of the integral
    integral_deviation = 0.5 * (deviation_t + deviation_next)

    # Reward is negative deviation to encourage staying close to target
    reward = -integral_deviation

    return reward