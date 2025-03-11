from system_env.training_environment import TrainingEnvironment

class TrainingSimulator:
    def __init__(self, dataset, state_attributes, state_size, action_size, n_episodes, n_timesteps, batch_size, optimal_moisture, n_step, irrigation_map):
        self.state_size = state_size
        self.action_size = action_size
        self.n_episodes = n_episodes
        self.n_timesteps = n_timesteps
        self.batch_size = batch_size
        self.irrigation_map = irrigation_map

        self.env = TrainingEnvironment(dataset, state_attributes, optimal_moisture, n_step)

        # Metrics for evaluations
        self.metrics = []
        self.total_time = 0

    def run(self):
        for ep in range(self.n_episodes):
            print(f"Episode {ep + 1}/{self.n_episodes}")

            ep_rewards = 0
            ep_losses = []

            
            # Iterate over training data
            for i in range(self.n_timesteps):
                self.total_time += 1
                state = state_data[i]

                # Take action, observe reward and next state
                irrigation_action = my_agent.make_decision(state)
                action = irrigation_map[irrigation_action]  # Map irrigation to action index
                next_state = state_data[i + 1]
                reward = get_reward(reward_data[i], action)

                # Check if terminal state (last row)
                terminal = i == len(train_df) - 2

                # Store the experience in replay buffer
                my_agent.memorize(state, irrigation_action, reward, next_state, terminal)

                # Perform training step with batch size
                if len(my_agent.replay_buffer) > batch_size:
                    metrics_from_replay = my_agent.replay(batch_size)
                    if metrics_from_replay:
                        ep_losses.append(metrics_from_replay['training_loss'])
                
                # Cập nhật lại target NN mỗi my_agent.update_targetnn_rate
                if total_time % my_agent.update_targetNN_rate == 0:
                    my_agent.update_target_network()

                state = next_state
                ep_rewards += reward

                if terminal:
                    print("Ep ", ep + 1, " reach terminal with reward = ", ep_rewards)
                    break

            if my_agent.epsilon > my_agent.epsilon_min:
                my_agent.epsilon = my_agent.epsilon * my_agent.epsilon_decay

            # Log metrics for the episode
            metrics.append({
                'episode': ep + 1,
                'total_reward': ep_rewards,
                'average_loss': np.mean(ep_losses) if ep_losses else 0,
            })