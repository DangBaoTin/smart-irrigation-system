from system_env.training_environment import TrainingEnvironment
from deepQ_agent import deepQ_agent

class TrainingSimulator:
    def __init__(self, dataset, state_attributes, state_size, action_size, n_episodes, n_timesteps, batch_size, optimal_moisture, n_step, irrigation_map):
        self.dataset = dataset
        self.state_attributes = state_attributes
        self.state_size = state_size
        self.action_size = action_size
        self.n_episodes = n_episodes
        self.n_timesteps = n_timesteps
        self.batch_size = batch_size
        self.optimal_moisture = optimal_moisture
        self.n_step = n_step
        self.irrigation_map = irrigation_map

        self.my_agent = deepQ_agent(state_size, action_size)

        # Metrics for evaluations
        self.metrics = []
        self.total_time = 0

    def reset(self, dataset, retrain = False, saved_model = None):
        if retrain:
            self.my_agent = deepQ_agent(self.state_size, self.action_size, saved_model, 0.5)
            self.dataset = dataset
        else:
            self.my_agent = deepQ_agent(self.state_size, self.action_size)
            self.dataset = dataset

    def run(self):
        env = TrainingEnvironment(self.dataset, self.state_attributes, self.optimal_moisture, self.n_step)
        env.fit()

        state = env.reset()

        for ep in range(self.n_episodes):
            print(f"Episode {ep + 1}/{self.n_episodes}")

            ep_rewards = 0
            ep_losses = []
            
            # Iterate over training data
            for i in range(self.n_timesteps):
                self.total_time += 1
                # state = state_data[i]

                # Take action, observe reward and next state
                action = self.my_agent.make_decision(state)
                # action = self.irrigation_map[irrigation_action]  # Map irrigation to action index
                # next_state = state_data[i + 1]
                next_state, reward, terminal = env.step(action)

                # reward = get_reward(reward_data[i], action)

                # Check if terminal state (last row)
                # terminal = i == len(train_df) - 2

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
            self.metrics.append({
                'episode': ep + 1,
                'total_reward': ep_rewards,
                'average_loss': np.mean(ep_losses) if ep_losses else 0,
            })

    def score(self):
        pass