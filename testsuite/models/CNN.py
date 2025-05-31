import zmq
import time
import numpy as np
import pandas as pd

import time
import json

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Flatten
from keras.layers import Conv1D
from keras.layers import MaxPooling1D

class BaseCNN:
    def __init__(self, datapath, seq_feature, n_steps, n_features):
        self.datapath = datapath
        self.seq_feature = seq_feature
        self.n_steps = n_steps
        self.n_features = n_features

        # Define model
        self.model = Sequential()
        self.model.add(Conv1D(filters=64, kernel_size=2, activation='relu', input_shape=(n_steps, n_features)))
        self.model.add(MaxPooling1D(pool_size=2))
        self.model.add(Flatten())
        self.model.add(Dense(50, activation='relu'))
        self.model.add(Dense(1))
        self.model.compile(optimizer='adam', loss='mse')

    # Data preprocessing
    def split_sequence(self, sequence, n_steps):
        X, y = list(), list()
        for i in range(len(sequence)):
            # Find the end of this pattern
            end_ix = i + n_steps
            # Check if we are beyond the sequence
            if end_ix > len(sequence)-1:
                break
            # Gather input and output parts of the pattern
            seq_x, seq_y = sequence[i:end_ix], sequence[end_ix]
            X.append(seq_x)
            y.append(seq_y)
        return np.array(X), np.array(y)
    
    def fit(self):
        train_data = pd.read_csv(self.datapath)
        seq_train = train_data[self.seq_feature].tolist()

        # Preprocessing steps
        # Split into samples
        X, y = self.split_sequence(seq_train, self.n_steps)
        # Reshape from [samples, timesteps] into [samples, timesteps, features]
        n_features = 1
        X = X.reshape((X.shape[0], X.shape[1], n_features))

        # Fit model
        self.model.fit(X, y, epochs=200, verbose=1)

    