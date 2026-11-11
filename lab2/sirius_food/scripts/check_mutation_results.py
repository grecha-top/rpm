"""Fail CI when mutmut reports surviving, suspicious, or untested mutations."""
import subprocess
import xml.etree.ElementTree as ET


def main() -> None:
    result = subprocess.run(
        [
            "mutmut",
            "junitxml",
            "--suspicious-policy=ignore",
            "--untested-policy=failure",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    root = ET.fromstring(result.stdout)
    tests = sum(int(suite.attrib.get("tests", 0)) for suite in root.findall("testsuite"))
    failures = sum(int(suite.attrib.get("failures", 0)) for suite in root.findall("testsuite"))
    errors = root.findall(".//error")
    non_timeout_errors = [error for error in errors if error.attrib.get("type") != "timeout"]
    timeouts = len(errors) - len(non_timeout_errors)
    if tests == 0:
        raise SystemExit("mutmut produced no mutations")
    print(
        f"mutants={tests} killed_or_timed_out={tests - failures - len(non_timeout_errors)} "
        f"timeouts={timeouts} failures={failures} errors={len(non_timeout_errors)}"
    )
    if failures or non_timeout_errors:
        raise SystemExit("Mutation testing has surviving or untested mutants")


if __name__ == "__main__":
    main()
