"""
CLI entry point to run the EKASUTRA benchmark evaluation.

This script simply invokes the evaluation logic in evaluate.py, which:
  1. Cleans the database
  2. Ingests the synthetic CSV (which now auto-triggers matching)
  3. Computes precision / recall against ground truth
"""

from evaluate import main

if __name__ == "__main__":
    main()
