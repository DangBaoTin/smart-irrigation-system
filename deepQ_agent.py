import random
import numpy as np

from collections import deque, Counter
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam

# Build an agent class for APSIM irrigation
class deepQ_agent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size

        # Replay Buffer initialization
        self.replay_buffer = deque(maxlen=50000)

        # Init parameters for agent
        self.gamma = 0.99                   # Discount factor
        self.epsilon = 1.0                  # Initial exploration rate
        self.epsilon_min = 0.01             # Minimum epsilon
        self.epsilon_decay = 0.995          # Decay for epsilon
        self.learning_rate = 0.001          # Learning rate for ADAM
        self.update_targetNN_rate = 10      # Update target network after certain episodes

        self.main_network = self.build_network()
        self.target_network = self.build_network()

        # Update target network weight = main network weight
        self.update_target_network

    def build_network(self):
        # Neural Net for Deep Q Learning model
        model = Sequential()

        # Input layer
        model.add(Dense(32, activation='relu', input_dim=self.state_size))
        # model.add(Dense(16, activation='relu', input_dim=self.state_size))
        # Hidden layer
        model.add(Dense(32, activation='relu'))
        # model.add(Dense(12, activation='relu'))
        # Output layer
        model.add(Dense(self.action_size, activation='linear'))
        
        model.compile(loss="mse", optimizer=Adam(learning_rate=self.learning_rate))
        return model

    # save_experience
    def memorize(self, state, action, reward, next_state, terminal):
        self.replay_buffer.append((state, action, reward, next_state, terminal))

    # support function for replay()
    def get_batch_from_buffer(self, batch_size):
        exp_batch = random.sample(self.replay_buffer, batch_size)
        state_batch = np.array([batch[0] for batch in exp_batch]).reshape(batch_size, self.state_size)
        action_batch = np.array([batch[1] for batch in exp_batch])
        reward_batch = [batch[2] for batch in exp_batch]
        next_state_batch = np.array([batch[3] for batch in exp_batch]).reshape(batch_size, self.state_size)
        terminal_batch = [batch[4] for batch in exp_batch]
        return state_batch, action_batch, reward_batch, next_state_batch, terminal_batch
    
    # train_main_network
    def replay(self, batch_size):
        if len(self.replay_buffer) < batch_size:
            return  # Don't train until there's enough experience in the buffer

        state_batch, action_batch, reward_batch, next_state_batch, terminal_batch = self.get_batch_from_buffer(batch_size)

        # Get current Q values for the current state
        q_values = self.main_network.predict(state_batch, verbose=0)

        # Get max Q values for next state
        next_q_values = self.target_network.predict(next_state_batch, verbose=0)
        max_next_q = np.amax(next_q_values, axis=1)

        # Calculate target Q-values for training
        target_q_values = np.copy(q_values)

        for i in range(batch_size):
            new_q_value = reward_batch[i] if terminal_batch[i] else reward_batch[i] + self.gamma * max_next_q[i]
            target_q_values[i][action_batch[i]] = new_q_value

        # Calculate Q-value loss (Mean Absolute Error)
        q_value_loss = np.mean(np.abs(q_values - target_q_values))

        # Train the main network on the batch of experiences
        loss = self.main_network.fit(state_batch, target_q_values, verbose=0)

        # Track metrics
        action_frequency = Counter(action_batch)

        # Return the metrics so we can log them
        return {
            'q_value_loss': q_value_loss,
            'action_frequency': action_frequency,
            'training_loss': loss.history['loss'][0]
        }

    def make_decision(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.randint(0, self.action_size - 1)
        state = np.array(state).reshape((1, self.state_size))
        q_values = self.main_network.predict(state, verbose=0)
        return np.argmax(q_values[0])

    def update_target_network(self):
        self.target_network.set_weights(self.main_network.get_weights())