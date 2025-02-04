# mtflow

Machine Trading Lifecycle
- Data management
- Strategy development
- Backtesting
- Model development (if use machine learning)
- Model training (if use machine learning)
- Parameter training / hyperparameter tuning
- MLOps setup (if use machine learning)
- Strategy & Model(s) deployment
- Portfolio monitoring
- Performance analysis


`mtflow` brainstorming:
- data management: Svelte Web UI to visualize data stored in `pfeed`
- StratOps: store strategy scripts and the corresponding backtest results in `pfeed`, can register/retire a strategy, manage its configs, versions, etc.
e.g. register a strategy version that produces the same result as the vectorized one, so that one can safely build on top of that.
- backtesting: save the analytical notebooks/dashboards (`pfund-plot`) used for calculating the backtest results
- MLOps: similar to strategy management, but see if it can be tightly integrated with mlflow, or even build on top of it
- ML training: ...
- deployment: assign dashboards to strategies for monitoring, GUI-based deployment, deployment type (local (single machine), cloud (clusters) etc. ), choose if use kafka in `pfeed` for streaming data
- live trading: monitoring & on-going analysis


`mlflow` reference:
- Experiment Tracking 📝: A set of APIs to log models, params, and results in ML experiments and compare them using an interactive UI.
- Model Packaging 📦: A standard format for packaging a model and its metadata, such as dependency versions, ensuring reliable deployment and strong reproducibility.
- Model Registry 💾: A centralized model store, set of APIs, and UI, to collaboratively manage the full lifecycle of MLflow Models.
- Serving 🚀: Tools for seamless model deployment to batch and real-time scoring on platforms like Docker, Kubernetes, Azure ML, and AWS SageMaker.
- Evaluation 📊: A suite of automated model evaluation tools, seamlessly integrated with experiment tracking to record model performance and visually compare results across multiple models.
- Observability 🔍: Tracing integrations with various GenAI libraries and a Python SDK for manual instrumentation, offering smoother debugging experience and supporting online monitoring.