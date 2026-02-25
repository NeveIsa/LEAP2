#!/usr/bin/env python3
"""Seed the default experiment with demo students and sample log entries."""

from pathlib import Path

from leap.core.experiment import ExperimentInfo
from leap.core import storage, rpc

EXPERIMENT = "default"
ROOT = Path(__file__).resolve().parent.parent.parent
EXP_PATH = ROOT / "experiments" / EXPERIMENT

STUDENTS = [
    ("s001", "Alice", "alice@demo.edu"),
    ("s002", "Bob", "bob@demo.edu"),
    ("s003", "Charlie", None),
]

SAMPLE_CALLS = [
    ("s001", "square", [7]),
    ("s001", "square", [3]),
    ("s001", "cubic", [2]),
    ("s002", "square", [5]),
    ("s002", "rosenbrock", [1.0, 1.0]),
    ("s002", "add", [10, 20]),
    ("s003", "square", [0]),
    ("s003", "gradient_step", [5.0, 2.0, 0.1]),
]


def main():
    exp = ExperimentInfo(EXPERIMENT, EXP_PATH)
    session = storage.get_session(EXPERIMENT, exp.db_path)

    print(f"Seeding experiment '{EXPERIMENT}'...")

    for sid, name, email in STUDENTS:
        try:
            storage.add_student(session, sid, name, email)
            print(f"  Added student: {sid} ({name})")
        except ValueError:
            print(f"  Student already exists: {sid}")

    for sid, func_name, args in SAMPLE_CALLS:
        try:
            result = rpc.execute_rpc(
                exp, session,
                func_name=func_name, args=args,
                student_id=sid, trial="seed",
            )
            print(f"  {sid}.{func_name}({args}) = {result}")
        except Exception as e:
            print(f"  {sid}.{func_name}({args}) failed: {e}")

    echo_result = rpc.execute_rpc(
        exp, session,
        func_name="echo", args=["hello from seed"],
        student_id="anonymous", trial="seed",
    )
    print(f"  anonymous.echo() = {echo_result}  (@noregcheck)")

    print(f"\nDone. Students: {len(STUDENTS)}, Log entries: {len(SAMPLE_CALLS) + 1}")
    session.close()


if __name__ == "__main__":
    main()
