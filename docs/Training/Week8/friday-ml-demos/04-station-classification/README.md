# Station classification: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Use the [local Citi Bike export](../data-preparation.md). No SQL database or AWS credentials are required after export. The default file locations are resolved automatically; CSV and Parquet overrides are described in [setup](../setup.md).

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 04-station-classification/requirements.txt
   cd 04-station-classification
   ```

2. Run the recovered script:

   ```bash
   python classification.py
   ```

3. Read accuracy and the classification report. Inspect the confusion matrix and map of predicted station-size categories. Close the plot window when finished.

## Files and outputs

- `station-view.sql`: retained SQL reference; not required for this workflow.
- `classification.py`: complete classifier, report, and plots.
- Generated locally: `classification_results.png`.

## Source and verification

Recovered from the opening “Classification with scikit-learn” section of `chat2.md`; the conversation then moved to MLflow deployment. Corrections are incorporated into this guide; troubleshooting exchanges are omitted. These examples now use the local AWS-derived export. See [verification](../verification.md) for current executed checks and their limits.

## Learning checkpoints

**Before running:** The station file includes positive capacities and enough rows for three teaching classes.

**Expected output:** A classification report and `classification_results.png`; the local verification accuracy was about 64.99%, not a promised future result.

**Interpret it:** The target is a category derived from capacity; coordinates are inputs. The confusion-matrix diagonal represents correct predictions.

**Check your understanding:**

1. Why must capacity stay out of X when it defines the target label?
2. Can equal capacities fall into different categories with rank-based tie breaking?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
