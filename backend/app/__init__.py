import time

# Read by app.main's startup_timing: the gap to create_app() is the cost of importing the app.
IMPORT_T0 = time.perf_counter()
