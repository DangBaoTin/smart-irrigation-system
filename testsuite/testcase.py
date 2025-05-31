import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from statsmodels.tsa.arima.model import ARIMA

from sklearn.metrics import mean_squared_error
from sklearn.linear_model import LinearRegression
from models.CNN import BaseCNN


class ConnectorSimulator:
    def __init__(self, datapath, training_datapath):
        self.datapath = datapath                        # for simulate sensor data
        self.training_datapath = training_datapath      # for fitting the model to predict when lose signals

        self.init_model()

        # Metrics for evaluate the predictions
        self.pred_metrics = None

        # Metrics for evaluate the deep Q model and other base models



    def init_model(self):
        """Support function for testing time series"""
        self.train_data = pd.read_csv(self.training_datapath)
        feature = "current_soil_moisture"
        series = self.train_data[feature]

        # Init ARIMA model (auto_arima can help find best p,d,q)
        self.model_ARIMA = ARIMA(series, order=(5, 1, 0))
        
        # Init Linear Regression model
        self.model_Linear = LinearRegression()

        # Init CNN model
        self.model_CNN = BaseCNN(self.training_datapath, feature, 3, 1)


    def fit(self):
        """Support function for testing time series"""
        # Fit ARIMA model
        self.model_ARIMA_fit = self.model_ARIMA.fit()

        # Fit Linear Regression model
        X_COLUMNS = ["temperature", "humidity", "rain", "salinity", "ph"]
        Y_COLUMNS = ["current_soil_moisture"]

        X = self.train_data[X_COLUMNS].values
        y = self.train_data[Y_COLUMNS]

        self.model_Linear.fit(X,y)

        # Fit CNN model
        self.model_CNN.fit()

    def test_time_series(self):
        """Scoring function for the lost signal mitigation"""
        self.fit()

        test_data = pd.read_csv(self.datapath)
        y_observed = test_data["current_soil_moisture"].values
        
        # Test using linear
        X_test = test_data[["temperature", "humidity", "rain", "salinity", "ph"]].values
        y_pred_Linear = self.model_Linear.predict(X_test)

        # Test using ARIMA
        y_forcast_ARIMA = self.model_ARIMA_fit.forecast(steps=len(test_data))

        # Test using CNN
        y_pred_CNN = []
        moisture_buffer = []
        last_moisture = self.train_data["current_soil_moisture"].values
        moisture_buffer = np.append(moisture_buffer, [last_moisture[len(self.train_data) - 3], last_moisture[len(self.train_data) - 2], last_moisture[len(self.train_data) - 1]])
        for i in range(len(test_data) - 1):
            x_input = moisture_buffer
            x_input = x_input.reshape((1, 3, 1))
            
            predicted_value = self.model_CNN.predict(x_input, verbose=0)
            y_pred_CNN = np.append(y_pred_CNN, predicted_value)
            
            moisture_buffer.append(predicted_value)
            if len(moisture_buffer) > 3:
                moisture_buffer.pop(0)

        self.pred_metrics.append({
            'linear': y_pred_Linear,
            'ARIMA': y_forcast_ARIMA,
            'CNN': y_pred_CNN,
            'true_observation': y_observed,
        })

        self.pred_metrics_df = pd.DataFrame(self.pred_metrics, columns = ['linear', 'ARIMA', 'CNN', 'true_observation'])
        self.pred_metrics_df.to_csv("testsuite/results_time_series/pred_metrics_df.csv")

        # Plot the original and predicted time series
        plt.figure(figsize=(12, 6))
        plt.plot(range(len(len(test_data))), y_observed, label='True')
        plt.plot(range(len(len(test_data))), y_pred_Linear, label='Linear Regression')
        plt.plot(range(len(len(test_data))), y_forcast_ARIMA, label='ARIMA')
        plt.plot(range(len(len(test_data))), y_pred_CNN, label='CNN')
        plt.legend()
        plt.grid()
        plt.xlabel('Time')
        plt.ylabel('Moisture')
        plt.title('Moisture Prediction')
        plt.savefig("testsuite/results_time_series/figures/hehe.png")
        

    def test_model():
        """Scoring function for testing the performance of Deep Q value"""
        pass