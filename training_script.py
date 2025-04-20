from system_env.training_environment import TrainingEnvironment
from deepQ_agent import deepQ_agent

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import time

class TrainingSimulator:
    def __init__(self, dataset, state_attributes, state_size, action_size, n_episodes, batch_size, optimal_moisture, irrigation_map):
        self.dataset = dataset
        self.state_attributes = state_attributes
        self.state_size = state_size
        self.action_size = action_size
        self.n_episodes = n_episodes
        self.batch_size = batch_size
        self.optimal_moisture = optimal_moisture
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
        env = TrainingEnvironment(self.dataset, self.state_attributes, self.optimal_moisture, self.irrigation_map)
        env.fit()

        metrics = []
        update_time = 0

        start = time.time()
        for ep in range(self.n_episodes):
            print(f"Episode {ep + 1}/{self.n_episodes}")
            
            state = env.reset()
            ep_rewards = 0
            ep_losses = []
            
            # Iterate over training data
            while 1:
                update_time += 1

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
                if update_time % self.my_agent.update_targetNN_rate == 0:
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
        end = time.time()
        self.total_time = end - start

        self.timenow = '{date:%Y-%m-%d_%H-%M-%S}'.format(date = datetime.datetime.now())
        self.metrics_df = pd.DataFrame(metrics, columns = ['episode', 'total_reward', 'average_loss'])
        self.metrics_df.to_csv("results/details/tracking_ep" + str(self.n_episodes) + "dat" + str(len(self.dataset)) + "_" + self.timenow + ".csv")

        print("Training batch ends with ", self.total_time, " seconds")
        pd.DataFrame({
            "Number of Episodes": [self.n_episodes],
            "Average Rewards": [np.mean(self.metrics_df['total_reward'].values)],
            "Total training time": [self.total_time]
            }).to_csv("results/results_ep" + str(self.n_episodes) + "dat" + str(len(self.dataset)) + "_" + self.timenow + ".csv")

        # Save weights
        self.my_agent.main_network.save("saved_models/agent_ep" + str(self.n_episodes) + "dat" + str(len(self.dataset)) + "_" + self.timenow + ".keras")

    def score(self):
        episodes = self.metrics_df['episode'].values
        total_rewards = self.metrics_df['total_reward'].values
        average_loss = self.metrics_df['average_loss'].values

        # First plot: Total Reward per Episode
        plt.figure(figsize=(10, 6))
        plt.plot(episodes, total_rewards, label='Total Reward')
        plt.xlabel('Episode')
        plt.ylabel('Total Reward')
        plt.title('Total Reward per Episode')
        plt.legend()
        plt.grid()
        plt.savefig("results/figures/totalreward_ep" + str(self.n_episodes) + "dat" + str(len(self.dataset)) + "_" + self.timenow + ".png")

        # Second plot: Average Loss per Episode
        plt.figure(figsize=(10, 6))
        plt.plot(episodes, average_loss, label='Average Loss', color='orange')
        plt.xlabel('Episode')
        plt.ylabel('Average Loss')
        plt.title('Average Loss per Episode')
        plt.legend()
        plt.grid()
        plt.savefig("results/figures/averageloss_ep" + str(self.n_episodes) + "dat" + str(len(self.dataset)) + "_" + self.timenow + ".png")