from system_env.training_environment import TrainingEnvironment
from deepQ_agent import deepQ_agent

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime

class TrainingSimulator:
    def __init__(self, dataset, state_attributes, state_size, action_size, n_episodes, batch_size, optimal_moisture, n_step, irrigation_map):
        self.dataset = dataset
        self.state_attributes = state_attributes
        self.state_size = state_size
        self.action_size = action_size
        self.n_episodes = n_episodes
        self.batch_size = batch_size
        self.optimal_moisture = optimal_moisture
        self.n_step = n_step
        self.irrigation_map = irrigation_map

        self.my_agent = deepQ_agent(state_size, action_size)

        # Metrics for evaluations
        self.metrics_df = None
        self.total_time = 0

    def reset(self, dataset, retrain = False, saved_model = None, n_episodes = None):
        self.metrics_df = None
        self.total_time = 0
        
        if retrain:
            self.my_agent = deepQ_agent(self.state_size, self.action_size, saved_model, 0.5)
            self.dataset = dataset
        else:
            self.my_agent = deepQ_agent(self.state_size, self.action_size)
            self.dataset = dataset

        if n_episodes:
            self.n_episodes = n_episodes

    def run(self):
        env = TrainingEnvironment(self.dataset, self.state_attributes, self.optimal_moisture, self.n_step)
        env.fit()

        state = env.reset()
        metrics = []

        for ep in range(self.n_episodes):
            print(f"Episode {ep + 1}/{self.n_episodes}")

            ep_rewards = 0
            ep_losses = []
            
            # Iterate over training data
            while 1:
                self.total_time += 1

                # Take action, observe reward and next state
                action = self.my_agent.make_decision(state)
                next_state, reward, terminal = env.step(action)

                # Store the experience in replay buffer
                self.my_agent.memorize(state, action, reward, next_state, terminal)

                # Perform training step with batch size
                if len(self.my_agent.replay_buffer) > self.batch_size:
                    metrics_from_replay = self.my_agent.replay(self.batch_size)
                    if metrics_from_replay:
                        ep_losses.append(metrics_from_replay['training_loss'])
                
                # Cập nhật lại target NN mỗi my_agent.update_targetnn_rate
                if self.total_time % self.my_agent.update_targetNN_rate == 0:
                    self.my_agent.update_target_network()

                state = next_state
                ep_rewards += reward

                if terminal:
                    print("Ep ", ep + 1, " reach terminal with reward = ", ep_rewards)
                    break

            if self.my_agent.epsilon > self.my_agent.epsilon_min:
                self.my_agent.epsilon = self.my_agent.epsilon * self.my_agent.epsilon_decay

            # Log metrics for the episode
            metrics.append({
                'episode': ep + 1,
                'total_reward': ep_rewards,
                'average_loss': np.mean(ep_losses) if ep_losses else 0,
            })

        self.timenow = '{date:%Y-%m-%d_%H-%M-%S}'.format(date = datetime.datetime.now())
        self.metrics_df = pd.DataFrame(metrics, columns = ['episode', 'total_reward', 'average_loss'])
        self.metrics_df.to_csv("results/tracking_ep" + self.n_episodes + "dat" + len(self.dataset) + "_" + self.timenow + ".csv")

        # Save weights
        self.my_agent.main_network.save("saved_models/agent_ep" + self.n_episodes + "dat" + len(self.dataset) + "_" + self.timenow + ".keras")

    def score(self):
        episodes = self.metrics_df['episodes'].values
        total_rewards = self.metrics_df['total_rewards'].values
        average_loss = self.metrics_df['average_loss'].values

        # Create a figure with two subplots (1 row, 2 columns)
        _, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # First plot: Total Reward per Episode
        ax1.plot(episodes, total_rewards, label='Total Reward')
        ax1.set_xlabel('Episode')
        ax1.set_ylabel('Total Reward')
        ax1.set_title('Total Reward per Episode')
        ax1.legend()
        ax1.grid()

        # Second plot: Average Loss per Episode
        ax2.plot(episodes, average_loss, label='Average Loss', color='orange')
        ax2.set_xlabel('Episode')
        ax2.set_ylabel('Average Loss')
        ax2.set_title('Average Loss per Episode')
        ax2.legend()
        ax2.grid()

        # Adjust layout to avoid overlap
        plt.tight_layout()

        # Show the combined figure
        plt.show()

        # Save evaluation figure
        plt.savefig("results/figures/tracking_ep" + self.n_episodes + "dat" + len(self.dataset) + "_" + self.timenow + ".png")