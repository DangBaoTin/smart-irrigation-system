from system_env.training_environment import TrainingEnvironment
from system_env.virtual_connector import VirtualGardenEnv

class TrainingSimulator:
    def __init__(self, dataset, state_size, action_size, n_episodes, n_timesteps, batch_size, optimal_moisture, n_step):
        self.dataset = dataset
        self.state_size = state_size
        self.action_size = action_size
        self.n_episodes = n_episodes
        self.n_timesteps = n_timesteps
        self.batch_size = batch_size
        self.optimal_moisture = optimal_moisture
        self.n_step = n_step