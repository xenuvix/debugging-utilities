import time
import os
import shutil
import subprocess
import winreg as reg

"""
    Warning: Run this as admin only
    1. Configure Windows Error Reporting crash dumps in registry globally
    2. Start ttd.exe monitoring of the wanted process name
    3. Monitor the local crash dumps directory for new dumps of wanted process
    4. If a new dump is detected, copy the traces to the given output path and deletes the temporary traces (when it didn't crash)
"""

PROCESS_NAME = "myprocess.exe"
TRACES_PATH = r"C:\temp_ttd_traces"
WER_PATH = os.path.expandvars(r"%localappdata%\Local\CrashDumps")
TTD_EXE = "ttd.exe"
CRASH_TRACES_OUTPUT_PATH = r"C:\final_ttd_traces"
LAST_DUMP_TIMESTAMP_FILE = os.path.expandvars(r"%windir%\temp\last_dump_timestamp.txt")


def setup_wer_full_dumps():
    # Open the registry key in read-write mode (KEY_SET_VALUE)
    key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE,
                      r"SOFTWARE\Microsoft\Windows\Windows Error Reporting",
                      0,
                      reg.KEY_SET_VALUE)
    try:

        # Create a new key under the opened key
        local_dumps_key = reg.CreateKey(key, "LocalDumps")
        # Create a new DWORD value under the LocalDumps key
        reg.SetValueEx(local_dumps_key, "DumpType", 0, reg.REG_DWORD, 2)
    finally:
        # Close the registry key
        reg.CloseKey(key)

    print("Windows Error Reporting full dumps configured successfully.")


def start_ttd_monitor():
    if not os.path.exists(TRACES_PATH):
        os.makedirs(TRACES_PATH)
    """Start TTD monitoring for the process."""
    subprocess.Popen([TTD_EXE, "-out", TRACES_PATH, "-monitor", PROCESS_NAME])


def copy_trace_files():
    if not os.path.exists(CRASH_TRACES_OUTPUT_PATH):
        os.makedirs(CRASH_TRACES_OUTPUT_PATH)
    """Copy trace files to the output directory."""
    for root, dirs, files in os.walk(TRACES_PATH):
        for file in files:
            if file.endswith(".out") or file.endswith(".run"):
                src_file_path = os.path.join(root, file)
                dst_file_path = os.path.join(CRASH_TRACES_OUTPUT_PATH, file)
                shutil.copy2(src_file_path, dst_file_path)


def get_last_dump_timestamp():
    """Get the timestamp of the last checked dump from a file."""
    try:
        with open(LAST_DUMP_TIMESTAMP_FILE, "r") as file:
            return float(file.read())
    except FileNotFoundError:
        return 0.0


def set_last_dump_timestamp(timestamp):
    """Set the timestamp of the last checked dump in a file."""
    with open(LAST_DUMP_TIMESTAMP_FILE, "w") as file:
        file.write(str(timestamp))


def check_wer_for_crashes():
    """Check the Windows Error Reporting directory for new crash reports of the monitored process."""
    last_dump_timestamp = get_last_dump_timestamp()
    new_dump_found = False
    new_dump_timestamp = last_dump_timestamp

    for root, dirs, files in os.walk(WER_PATH):
        for file in files:
            if PROCESS_NAME in file:
                file_timestamp = os.path.getmtime(os.path.join(root, file))
                if file_timestamp > last_dump_timestamp:
                    new_dump_found = True
                    new_dump_timestamp = max(new_dump_timestamp, file_timestamp)

    if new_dump_found:
        set_last_dump_timestamp(new_dump_timestamp)

    return new_dump_found


def delete_ttd_traces():
    """Delete all the TTD trace files in the traces output directory."""
    for root, dirs, files in os.walk(TRACES_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                print(f"Deleted TTD trace file: {file_path}")
            except Exception as e:
                print(f"Could not delete TTD trace file: {file_path}. Reason: {e}")


def main():
    setup_wer_full_dumps()
    # Start TTD monitoring
    start_ttd_monitor()

    while True:
        if check_wer_for_crashes():
            # If a crash report is found, save the trace (it is automatically saved to the specified output directory).
            print(f"Crash detected for {PROCESS_NAME}, copying the TTD trace.")
            # Give a few seconds for ttd to finish flushing the traces
            time.sleep(10)
            copy_trace_files()
        else:
            # If no crash report is found, delete the trace to save space.
            # Note: Implement a function to properly identify and delete the unnecessary traces.
            print(f"No crash detected for {PROCESS_NAME}")

        delete_ttd_traces()

        time.sleep(10)  # Adjust the sleep time as needed


if __name__ == "__main__":
    main()