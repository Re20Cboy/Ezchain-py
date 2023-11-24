import os

def ensure_directory_exists(file_path):
    """
    Ensures that the directory for the given file path exists, creates it if not.
    """
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def write_data_to_file(file_path, data):
    """
    Writes data to a file, handles IOError.
    """
    try:
        with open(file_path, "wb") as f:
            f.write(data)
    except IOError as e:
        print(f"Error writing to file {file_path}: {e}")
        raise