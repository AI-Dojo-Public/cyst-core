import subprocess
import os
import glob
import sys

from pathlib import Path

root_path = os.path.dirname(os.path.realpath(__file__))
test_path = os.path.normpath(root_path + "/tests/integration/")
test_file = "bronze_butler.py"

test_case = "BronzeButlerScenarios"
test_items = [
    "test_0000_cto_scenario_omniscient",
    "test_0001_cto_scenario_random",
    "test_0002_cto_scenario_modular",
    "test_0003_vpn_scenario_omniscient",
    "test_0004_vpn_scenario_random",
    "test_0005_vpn_scenario_modular",
    "test_0006_employee_scenario_omniscient",
    "test_0007_employee_scenario_random",
    "test_0008_employee_scenario_modular"
]

env = os.environ
env["PYTHONPATH"] = root_path

test_file_module = os.path.splitext(test_file)[0]

# ------------------------------------------------------------------------------
print("Depending on the set number of runs, this evaluation can run for hours. Beware!")

# -----------------------------------------------------------------------------
# Run specified tests in parallel
processes = []
for test in test_items:
    module = test_file_module + "." + test_case + "." + test
    args = [sys.executable, "-m", "unittest", module]
    processes.append(subprocess.Popen(args, env=env, cwd=test_path, stderr=subprocess.DEVNULL))

exit_codes = [p.wait() for p in processes]

if 1 in exit_codes:
    print("There was an error running the tests.")
    exit(1)

# -----------------------------------------------------------------------------
# Combine median data
# - random
random_output = open(os.path.normpath(test_path + "/median_random.data"), "w")
glob_path = Path(test_path)
random_median_paths = list(glob_path.glob("median_random_*.data"))
random_median_paths.sort(key=lambda x: x.name)
for f in random_median_paths:
    with f.open() as item:
        random_output.write(item.read())
    item.close()
    f.unlink()
random_output.close()

# - modular
modular_output = open(os.path.normpath(test_path + "/median_modular.data"), "w")
glob_path = Path(test_path)
modular_median_paths = list(glob_path.glob("median_modular_*.data"))
random_median_paths.sort(key=lambda x: x.name)
for f in modular_median_paths:
    with f.open() as item:
        modular_output.write(item.read())
    item.close()
    f.unlink()
modular_output.close()

# -----------------------------------------------------------------------------
# Create plots