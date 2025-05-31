from connector_simulator import ConnectorSimulator

env = ConnectorSimulator("testsuite/test.csv", "testsuite/dat.csv")

env.fit()

env.score()