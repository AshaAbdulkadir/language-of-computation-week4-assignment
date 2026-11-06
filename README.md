# Language of Computation: Week 4 Assignment

This is my Module 4 assignment for MSAI-5523: Language of Computation.

Partner: George (GitHub: Georgec4444)

## Running the tests

The tests use pytest. These commands are for macOS with the built-in `python3` (Python 3.9).

Open Terminal and go to the project folder:

```
cd ~/workspace/language-of-computation/week4-assignment
```

Install pytest (only needed once):

```
python3 -m pip install --user pytest
```

Run all the tests:

```
python3 -m pytest
```

Run them with each test's name and result listed:

```
python3 -m pytest -v
```

The tests use a temporary `test.db` and their own log, and delete them when they finish. They never read or change `books.db` or `ingestion-log.json`.

## Running the ingestion

Run these three commands in order, from the project folder:

```
cd ~/workspace/language-of-computation/week4-assignment
python3 ingest.py books.csv
python3 ingest.py books.csv
python3 ingest.py books-batch2.csv
```

The first command loads `books.csv`, the second loads the same file again, and the third loads `books-batch2.csv` (rules.md R39). Each run writes to `books.db` and adds an entry to `ingestion-log.json`, both kept in the same folder as `ingest.py`. To see the results, open `report.html` in a browser and choose `ingestion-log.json`.
