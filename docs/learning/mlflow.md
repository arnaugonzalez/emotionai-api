# MLflow — EmotionAI study guide

## What is it and why do we use it here

MLflow is an open-source platform for tracking machine learning experiments. It records everything that matters when you train a model: the hyperparameters you chose, the metrics that came out, the artifacts you produced (plots, saved models, confusion matrices), and the exact code version that ran. It stores all of that and makes it browsable through a web UI.

Without MLflow, you track experiments the wrong way: you print accuracy to the terminal, forget what hyperparameters you used two runs ago, save a model file with a name like `model_v3_final_FINAL.pkl`, and have no idea whether the version deployed last week is better or worse than what you have locally. This is fine for a first prototype. It breaks down the moment you run more than a handful of experiments.

In EmotionAI, MLflow is introduced in Milestone 3 to support the emotion classifier experiment. The classifier is a sklearn model that takes a user's mood label history and predicts emotional state categories. We need to compare:

- different feature engineering choices (bag-of-words vs TF-IDF vs embedding features)
- different model families (logistic regression vs random forest vs gradient boosting)
- different hyperparameter values (regularization strength, tree depth, etc.)
- per-class F1 scores, since the mood label distribution is imbalanced

If you run 20 variants of that without MLflow, you will lose track of what produced the best result. MLflow keeps every run, makes them comparable side by side, and lets you promote the best one to a named version in the model registry.

The planned entry point for this work is `scripts_emotionai/ml_experiments/emotion_classifier.py`. That script does not live inside the FastAPI application — it is a standalone experiment runner. MLflow is not a production serving layer here; it is a development and evaluation tool. The tracking server runs locally via docker-compose at `localhost:5000`.

---

## How it works conceptually

The mental model has three levels: experiments → runs → logged data.

**Experiments** are the top-level grouping. An experiment is a named project — for example, `emotion-classifier-v1`. Every time you train a model inside that project, you create a run.

**Runs** are individual training executions. Each run has a unique ID and captures a snapshot of one attempt: which parameters you passed in, what metrics came out, which artifacts were saved. Runs are independent — you can compare them directly in the UI.

**Logged data** inside a run comes in three types:

- **Parameters** (`mlflow.log_param`): inputs you controlled. Model family, learning rate, number of estimators, feature type. These are the knobs you turned. Logged once per run.
- **Metrics** (`mlflow.log_metric`): outputs you measured. Accuracy, F1, precision, recall. Metrics can also be logged at each training step (epoch, fold) — MLflow plots them as time-series charts.
- **Artifacts** (`mlflow.log_artifact`): files you produced. A PNG of the confusion matrix, a serialized model file, a CSV of predictions, a feature importance plot. Artifacts are stored in a configurable backend — SQLite locally, S3 in production.

**Model registry** is a layer on top of runs. Once you have logged a model artifact, you can register it under a name and give it a lifecycle stage: `Staging`, `Production`, or `Archived`. The registry is how you answer "which version of the emotion classifier is in production right now?" without digging through file paths.

**Tracking URI** tells MLflow where to store data. By default it writes to `./mlruns` on disk. When you run `mlflow.set_tracking_uri("http://localhost:5000")`, it sends data to a running MLflow server instead, which means the web UI stays populated between runs and multiple people can share results.

Compared to TensorBoard, which is deep-learning oriented and primarily tracks training curves, MLflow is framework-agnostic. It works equally well with sklearn, PyTorch, XGBoost, or anything else. The UI is also more experiment-management focused — searching, filtering, and comparing runs across parameter choices is more central to the interface.

A junior developer way to think about it: MLflow is a structured logbook for model training. Every time you run `python emotion_classifier.py`, instead of printing results to a terminal you will never scroll back to, MLflow writes a row in a database with every detail of that run, and the UI lets you sort by F1 score to find your best attempt instantly.

---

## Key patterns used in this project

### 1. Set tracking URI before any experiment code

The tracking URI must be set before `mlflow.set_experiment()`. In the emotion classifier script, this comes from `settings.py` once the M3 `mlflow_tracking_uri` field is added:

```python
import mlflow
from src.infrastructure.config.settings import settings

# Point to the MLflow server running in docker-compose
mlflow.set_tracking_uri(settings.mlflow_tracking_uri)  # "http://localhost:5000"

# Create or reuse an experiment by name
mlflow.set_experiment("emotion-classifier")
```

When `ENVIRONMENT=development` and docker-compose is running, the tracking URI will be `http://localhost:5000`. When running the script standalone without the docker-compose MLflow service, you can fall back to the local filesystem default by omitting `set_tracking_uri` — MLflow will write to `./mlruns`.

### 2. Use a context manager for every run

The safest way to create a run is with `mlflow.start_run()` as a context manager. This guarantees the run is ended and marked as `FINISHED` even if an exception occurs:

```python
with mlflow.start_run(run_name="random-forest-tfidf"):
    # Log parameters (what you chose)
    mlflow.log_param("model_type", "random_forest")
    mlflow.log_param("n_estimators", 200)
    mlflow.log_param("max_depth", 10)
    mlflow.log_param("feature_type", "tfidf")
    mlflow.log_param("train_size", len(X_train))

    # Train the model
    model = RandomForestClassifier(n_estimators=200, max_depth=10)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    # Log metrics (what came out)
    mlflow.log_metric("accuracy", acc)
    mlflow.log_metric("f1_weighted", f1)

    # Log per-class F1 because mood labels are imbalanced
    report = classification_report(y_test, y_pred, output_dict=True)
    for label, scores in report.items():
        if isinstance(scores, dict):
            mlflow.log_metric(f"f1_{label}", scores["f1-score"])

    # Log artifacts (files you produced)
    _save_and_log_confusion_matrix(y_test, y_pred)
    mlflow.sklearn.log_model(model, artifact_path="emotion_classifier_model")
```

### 3. Log the confusion matrix as an artifact

For a multi-class classifier over mood labels, the confusion matrix is more informative than a single accuracy number. Save it as a PNG and log it:

```python
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay
import tempfile
import os

def _save_and_log_confusion_matrix(y_true, y_pred) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ConfusionMatrixDisplay.from_predictions(y_true, y_pred, ax=ax)
    ax.set_title("Emotion Classifier — Confusion Matrix")

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "confusion_matrix.png")
        fig.savefig(path, bbox_inches="tight")
        mlflow.log_artifact(path)  # uploads file to artifact store
    plt.close(fig)
```

The artifact appears under the run in the MLflow UI at `localhost:5000`. Click the run, then the Artifacts tab.

### 4. Use mlflow.sklearn.log_model for the registered model

`mlflow.sklearn.log_model` does more than save a pickle. It records the sklearn version, saves a `MLmodel` descriptor that MLflow understands, and makes the artifact loadable via `mlflow.sklearn.load_model` by run ID — no manual file paths needed:

```python
mlflow.sklearn.log_model(
    model,
    artifact_path="emotion_classifier_model",
    registered_model_name="EmotionClassifier",  # registers in the model registry
)
```

Setting `registered_model_name` automatically creates a registered model entry. You can then promote it to `Production` stage via the UI or the MLflow client:

```python
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="EmotionClassifier",
    version=1,
    stage="Production",
)
```

### 5. Viewing results

With docker-compose running (after M3 adds the MLflow service):

```bash
# Open the MLflow UI
open http://localhost:5000

# Or run the standalone UI against a local mlruns directory
mlflow ui --port 5000 --backend-store-uri ./mlruns
```

The UI shows all experiments on the left panel. Click an experiment to see all runs, sortable by any metric. Click a run to see its parameters, metrics chart, and artifact list.

To compare runs programmatically:

```python
client = mlflow.tracking.MlflowClient()
runs = client.search_runs(
    experiment_ids=["1"],
    order_by=["metrics.f1_weighted DESC"],
    max_results=10,
)
for run in runs:
    print(run.info.run_id, run.data.metrics["f1_weighted"])
```

---

## Common mistakes and how to avoid them

### Not using the context manager

Bad outcome: if your training script raises an exception or you kill it with Ctrl+C, the run stays in `RUNNING` state permanently. The UI fills up with zombie runs that never finished.

Avoid it by always wrapping experiment code in `with mlflow.start_run():`. The context manager calls `mlflow.end_run()` for you, even on exception.

If you cannot use a context manager (nested logic, callbacks), call `mlflow.end_run()` explicitly in a `finally` block.

### Tracking URI mismatch between local and docker

Bad outcome: you run the experiment script locally without pointing at the docker-compose MLflow server. Runs go to `./mlruns` on your filesystem. The server at `localhost:5000` shows nothing. You think MLflow is broken.

Avoid it by always calling `mlflow.set_tracking_uri(...)` at the top of your script, and reading the URI from an environment variable or `settings.mlflow_tracking_uri` rather than hardcoding it. During M3 development:

```bash
# Run against the docker-compose server
MLFLOW_TRACKING_URI=http://localhost:5000 python scripts_emotionai/ml_experiments/emotion_classifier.py

# Or fall back to local mlruns (no server needed)
python scripts_emotionai/ml_experiments/emotion_classifier.py
```

### Artifact path confusion

Bad outcome: `mlflow.log_artifact("/absolute/path/to/file.png")` logs the file but MLflow stores it under the filename only, not the full path. Calling it twice with different files of the same name overwrites the first.

Avoid it by using `artifact_path` to organize artifacts into subdirectories:

```python
mlflow.log_artifact("confusion_matrix.png", artifact_path="plots")
mlflow.log_artifact("feature_importances.png", artifact_path="plots")
mlflow.log_artifact("model.pkl", artifact_path="model")
```

This mirrors the directory structure inside the artifact store.

### Nested runs when you do not intend them

Bad outcome: you call `mlflow.start_run()` inside a loop without ending the outer run. MLflow creates nested runs instead of sibling runs. The UI nests them under the parent, which is confusing and hard to compare.

Avoid it by structuring loops so each iteration uses its own clean `with mlflow.start_run():` block and no outer run is active:

```python
for config in hyperparameter_grid:
    with mlflow.start_run(run_name=f"rf-{config['n_estimators']}"):
        # Each iteration is a sibling run, not a nested run
        mlflow.log_params(config)
        ...
```

If you intentionally want nested runs (e.g., a parent run for a cross-validation sweep with child runs per fold), pass `nested=True` explicitly: `mlflow.start_run(nested=True)`.

### Model registry vs just saving artifacts

Bad outcome: you log the model as an artifact (`mlflow.log_artifact("model.pkl")`) but never register it. You have no way to answer "which run produced the model file I should load for inference" without reading run IDs from a spreadsheet.

Avoid it by using `mlflow.sklearn.log_model(..., registered_model_name="EmotionClassifier")` for any model you might actually use. The registry gives you named versions with lifecycle stages. Artifact-only logging is fine for intermediate outputs like plots and CSVs.

### Logging params inside a loop

Bad outcome: calling `mlflow.log_param("key", value)` repeatedly with the same key overwrites the value silently. You think you logged all fold results but only the last fold's param is stored.

Avoid it by logging params once before training, and using metrics (with `step=`) for per-iteration values:

```python
mlflow.log_param("n_folds", 5)           # logged once
for fold, (acc, f1) in enumerate(fold_results):
    mlflow.log_metric("fold_accuracy", acc, step=fold)  # logged per step
    mlflow.log_metric("fold_f1", f1, step=fold)
```

---

## Further reading

- MLflow documentation: https://mlflow.org/docs/latest/index.html
- MLflow tracking API reference: https://mlflow.org/docs/latest/python_api/mlflow.html
- MLflow model registry guide: https://mlflow.org/docs/latest/model-registry.html
- MLflow sklearn integration: https://mlflow.org/docs/latest/python_api/mlflow.sklearn.html
- MLflow vs Weights & Biases: W&B is more polished for deep learning — richer real-time dashboards, better team collaboration features, hosted SaaS by default. MLflow is self-hosted, framework-agnostic, and integrates naturally with sklearn and tabular ML workflows. For EmotionAI's sklearn emotion classifier, MLflow is the right fit. For a transformer fine-tuning project, W&B would offer more.
- MLflow vs DVC: DVC (Data Version Control) focuses on versioning datasets and pipelines as git-tracked artifacts. MLflow focuses on experiment tracking and model registry. They solve different problems and are often used together — DVC for data lineage, MLflow for run comparison and model promotion. EmotionAI does not need DVC at this stage because the training dataset is small and derived from the PostgreSQL database at experiment time.
