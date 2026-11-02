# Kafka fraud training: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Use local Kafka KRaft on `localhost:9092` and the local MLflow tracking server on port 5000. No AWS access, API key, SQL database, or real financial data is needed. Run the collector and trainer from this demo directory. Run one trainer at a time; keep the same evaluation files across candidate runs.

## Finalized steps

1. From `friday-ml-demos`, activate the environment and install the packages. Start MLflow using shared setup in another terminal:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 07-kafka-fraud-training/requirements.txt
   ```

2. In a terminal with `KAFKA_HOME` configured, create the input topic:

   ```bash
   "$KAFKA_HOME/bin/kafka-topics.sh" \
     --bootstrap-server localhost:9092 --create --if-not-exists \
     --topic fraud-transactions --partitions 1 --replication-factor 1
   ```

3. In an activated terminal, start the collector:

   ```bash
   cd 07-kafka-fraud-training
   python fraud_training_consumer.py
   ```

4. In another activated terminal starting from `friday-ml-demos`, start the producer:

   ```bash
   cd 07-kafka-fraud-training
   python fraud_producer.py --rate 10
   ```

5. Allow several hundred labeled records to accumulate, including at least five examples of each class. In a third activated terminal starting from `friday-ml-demos`, train a candidate:

   ```bash
   cd 07-kafka-fraud-training
   wc -l fraud_training_data.csv
   python train_streaming_fraud.py --max-depth 4
   ```

   The line count includes the header. The trainer freezes a complete CSV snapshot under a shared file lock. The first run creates fixed `evaluation/validation.csv` and `evaluation/test.csv` papers from the initial dataset, approximately 20% each. Their IDs are excluded from every training run. Remaining initial rows and later new transactions can be training examples.

6. Train other configurations sequentially:

   ```bash
   python train_streaming_fraud.py --max-depth 8
   python train_streaming_fraud.py --max-depth 12
   ```

   With the producer running, both data size and configuration can change. To isolate depth alone, stop the producer, allow the collector to finish pending messages, then stop the collector before all three runs. Otherwise, describe the comparison as changing both data volume and depth. The validation paper stays fixed in either case.

7. In `kafka-streaming-fraud-training`, compare `validation_precision`, `validation_recall`, `validation_f1`, and `validation_accuracy`, together with row counts and depth. Confirm the compared runs have the same `validation_sha256`. Newest is not automatically best. Choose the balance appropriate for the lesson and record that registered version number.

8. After choosing, evaluate that version once on the reserved test paper:

   ```bash
   python evaluate-final-model.py --version YOUR_SELECTED_VERSION
   ```

   Replace the placeholder with the actual number. Review `fraud-final-evaluation` in MLflow. Do not try multiple models on the test paper to choose the winner: that would make it another validation set. The script records that version's final test locally and refuses to overwrite its report.

9. Continue to [demo 08](../08-kafka-fraud-inference/README.md) to select and serve the reviewed version. Training registers candidates but does not change `champion` or the running model server.

## Files and outputs

| File | Responsibility |
| --- | --- |
| `fraud_producer.py` | Continuous labeled synthetic events |
| `fraud_training_consumer.py` | Complete CSV rows, file locks, and explicit next-offset commits |
| `training_data.py` | Immutable snapshots, replay checks, and fixed validation/test partitions |
| `train_streaming_fraud.py` | Candidate fitting and validation metrics; no automatic promotion |
| `evaluate-final-model.py` | Final evaluation of the already chosen numbered model |
| Generated `fraud_training_data.csv`, `runs/`, `evaluation/` | Local working state, excluded from Git |

Do not delete or recreate the evaluation papers between candidate runs and then describe the scores as a fixed benchmark. To begin a different exercise cohort, preserve the old files in a separate working directory and identify it as a different comparison.

## Why the reliability changes help

The collector finishes writing and syncing a complete row before marking that exact Kafka record as processed. A trainer briefly locks the file while copying it, then works on an immutable snapshot while collection resumes. This prevents a changing input file from changing halfway through a training read. A crash can still replay a row, so stable transaction IDs support deduplication. No distributed exactly-once guarantee is claimed.

## Verification

See the [verification record](../verification.md). Fixed-paper separation, snapshot immutability, conflicting replay detection, and commit ordering have offline tests. A real Kafka-driven training session remains a separate runtime checkpoint.

## Learning checkpoints

**Before running:** Local Kafka and MLflow are running. Collection contains at least 100 complete rows and five examples of each class.

**Expected output:** A frozen input under `runs/`, persistent evaluation papers, candidate versions, and `validation_*` metrics with matching validation hashes.

**Interpret it:** A complete source snapshot stops the input changing during a run. Fixed validation examples let candidates take the same exam; final test examples are reserved.

**Check your understanding:**

1. Does Kafka receiving another transaction automatically refit the served forest?
2. Why must you not choose the winner by repeatedly checking final-test scores?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
