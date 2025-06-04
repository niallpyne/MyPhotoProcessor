import os

def create_dot_nomedia(directory_path):
    """
    Creates a .nomedia file in the specified directory to hide media from scanners.
    """
    nomedia_path = os.path.join(directory_path, ".nomedia")
    if not os.path.exists(nomedia_path):
        try:
            with open(nomedia_path, 'w') as f:
                # The file just needs to exist, content doesn't matter
                pass
            # print(f"Created .nomedia file in {directory_path}") # Can be noisy
        except IOError as e:
            print(f"Error creating .nomedia file in {directory_path}: {e}")
    # else:
        # print(f".nomedia file already exists in {directory_path}") # Can be noisy

def ensure_directory_exists(path):
    """Ensures a directory exists, creating it if necessary."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        print(f"Created directory: {path}")
    return path
