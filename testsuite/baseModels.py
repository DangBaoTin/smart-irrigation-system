# Machine Learning Models for Smart Irrigation Comparison

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Regression models
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor


class BaseModels:
    def __init__(self, datapath, features, target_features):
        self.df = pd.read_csv(datapath)
        self.features = features
        self.target_features = target_features

        # Define models
        self.models = {
            "Linear Regression": LinearRegression(),
            "Decision Tree": DecisionTreeRegressor(random_state=42),
            "Random Forest": RandomForestRegressor(random_state=42),
            "Gradient Boosting": GradientBoostingRegressor(random_state=42),
            "Support Vector Regressor": SVR(),
            "KNN Regressor": KNeighborsRegressor(),
            "MLP Regressor": MLPRegressor(random_state=42, max_iter=1000)
        }
    
    def fit(self):
        X = self.df[self.features]
        y = self.df[self.target_features]
        
        # # Standardize features
        # scaler = StandardScaler()
        # X_train_scaled = scaler.fit_transform(X_train)
        # X_test_scaled = scaler.transform(X_test)
        
        for _, model in self.models.items():
            model.fit(X, y)

        return self.models
