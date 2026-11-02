# Friday theory reading map

[Demo index](README.md) · [Code reading guide](code-reading-guide.md)

Use the [main Friday lecture](../5_Fri_ML_Flow.md) as the comprehensive explanation of ML, MLOps, model metrics, lifecycle, streaming ownership, and tracing. This page routes concepts to the hands-on guides instead of maintaining another copy of the same lecture. Each demo's `theory.md` keeps its specific assumptions and limitations next to its code.

| Learn first | Main lecture section | Practice |
| --- | --- | --- |
| Features, target, and record grain | [Features, labels, and record grain](../5_Fri_ML_Flow.md#features-labels-and-record-grain) | Demos 01–04 |
| Supervised versus unsupervised learning | [Learning paradigms](../5_Fri_ML_Flow.md#learning-paradigms) | Clustering, regression, classification |
| Training and generalization | [Training, testing, and inference](../5_Fri_ML_Flow.md#training-testing-and-inference) | Demos 03–06 |
| Numerical prediction error | [Evaluating regression](../5_Fri_ML_Flow.md#evaluating-regression) | Capacity and time-series regression |
| Imbalanced classification | [Evaluating classification](../5_Fri_ML_Flow.md#evaluating-classification) | Fraud training and live monitoring |
| Runs, artifacts, registry, serving | [MLflow records](../5_Fri_ML_Flow.md#hyperparameters-learned-parameters-and-mlflow-records) | Demos 05, 07, and 08 |
| Events versus batch model fitting | [Streaming ownership](../5_Fri_ML_Flow.md#streaming-machine-learning-and-data-ownership) | Demos 07–10 |
| LLM behavior versus response quality | [Explanations, traces, and evaluation](../5_Fri_ML_Flow.md#generative-ai-explanations-traces-and-evaluation) | Flask/OpenAI and MLflow tracing |

The [visual companion](visuals/README.md) collects the original screenshots, a KRaft control/data diagram, the two model-lifecycle paths, and new metric/time illustrations. [Homework](../5.2_Fri_HW.md) remains the instructor's separate theoretical reading and final-presentation assignment.
