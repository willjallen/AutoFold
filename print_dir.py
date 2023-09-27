import os

def has_py_files(dir_path):
    """Check if a directory has .py files in it or in its subdirectories."""
    for root, dirs, files in os.walk(dir_path):
        if '.venv' in dirs:
            dirs.remove('.venv')
        if any(file.endswith('.py') for file in files):
            return True
    return False

def print_py_structure(starting_path, indent=0):
    # Skip .venv folder
    if '.venv' in os.path.basename(starting_path):
        return
    
    # Only proceed if the directory contains .py files
    if not has_py_files(starting_path):
        return

    # Print the directory name
    print("  " * indent + f"+-- {os.path.basename(starting_path)}/" if indent else f"{starting_path}/")
    
    # Get a list of all entries in the directory
    entries = os.listdir(starting_path)
    entries.sort()
    
    # Print all files in the root directory
    if indent == 0:
        for entry in entries:
            if not os.path.isdir(os.path.join(starting_path, entry)):
                print("  " * (indent + 1) + f"+-- {entry}")

    # Loop through each entry
    for entry in entries:
        entry_path = os.path.join(starting_path, entry)
        
        # If entry is a directory, recurse into it
        if os.path.isdir(entry_path):
            print_py_structure(entry_path, indent + 1)
        
        # If entry is a Python file, print its name
        elif entry.endswith(".py"):
            print("  " * (indent + 1) + f"+-- {entry}")

# Starting path of your project
starting_path = "."  # Set this to the path of your Python project if not running the script from there

# Start the printing
print_py_structure(starting_path)

