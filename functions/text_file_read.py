text_file_data = ""

def ai_read_file(filepath: str) -> None:
    """
    Reads the content of a file and stores it in the global variable 'text_file_data'.

    Args:
        filepath (str): The path to the file to be read.

    Returns:
        None

    Effects:
        Modifies the global variable 'text_file_data' by assigning the file's content to it.
        If the file does not exist or cannot be read, an exception will be raised.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        PermissionError: If the user does not have permission to read the file.
        UnicodeDecodeError: If the file contains invalid characters and the default encoding is used.
        Other I/O related exceptions.
    """
    global text_file_data
    with open(filepath, 'r') as file:
        text_file_data = file.read()
        return text_file_data


if __name__ == "__main__":
    # Example usage:
    ai_read_file("todo.txt")

    # Prints the content of the file that was read.
    print(text_file_data)

