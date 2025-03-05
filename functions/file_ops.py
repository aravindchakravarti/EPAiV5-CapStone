'''
This file contains function for which can organize the files into organized way.
It first scans all the files in the folder, then it creates folders based on extension,
for example, all file with extension .jpg, .bmp, .png etc are considered as images.
Then, all the un-organized files are moved to their respective folders.
'''

import os
import shutil
import stat
from typing import List, Set, Dict
from pathlib import Path
import logging

# Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define file type mappings
FILE_TYPE_MAPPINGS = {
    'images': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'ico'},
    'documents': {'txt', 'doc', 'docx', 'pdf', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'},
    'codes': {'py', 'ipynb'}
}

file_list = []
unique_file_types = set()
folder_paths = {}

def ai_get_file_list(path: str) -> None:
    """
    Returns a list of files in a directory and its subdirectories.
    
    Args:
        path (str): Path to the directory to scan.

    Returns:
        List[str]: List of absolute paths to all files in the directory.

    Raises:
        FileNotFoundError: If the specified path doesn't exist.
        PermissionError: If there are insufficient permissions to access the directory.
    """
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        for root, _, files in os.walk(path):
            for file in files:
                file_list.append(os.path.join(root, file))
        
        logging.info(f"Found {len(file_list)} files in {path}")
        return None
    
    except PermissionError as e:
        logging.error(f"Permission denied accessing {path}: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Error scanning directory {path}: {str(e)}")
        raise

def ai_get_unique_file_types() -> None:
    """
    Extracts unique file extensions from a list of file paths.

    Args:
        file_list (List[str]): List of file paths.

    Returns:
        Set[str]: Set of unique file extensions (lowercase).
    """
    for file in file_list:
        # Handle files without extensions
        if '.' in file:
            file_type = file.split('.')[-1].lower()
            unique_file_types.add(file_type)
    
    logging.info(f"Found {len(unique_file_types)} unique file types: {unique_file_types}")
    return None

def remove_readonly(func, path, _):
    """
    Clears the read-only attribute and retries the file operation.
    
    Args:
        func: The original function that failed (typically os.remove or os.rmdir)
        path (str): Path to the file/directory
        _: ExcInfo triple (not used)
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logging.error(f"Failed to remove read-only file/directory {path}: {str(e)}")
        raise

def ai_create_folders(base_path: str = ".") -> None:
    """
    Creates organized folders based on file types and returns their paths.
    
    Args:
        unique_file_types (Set[str]): Set of file extensions to organize
        base_path (str): Base directory for creating organized folders

    Returns:
        Dict[str, str]: Mapping of folder categories to their paths

    Raises:
        PermissionError: If there are insufficient permissions to create directories
    """
    
    try:
        # Create base path if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        
        # Determine which folders need to be created based on file types
        needed_folders = set()
        for folder_name, extensions in FILE_TYPE_MAPPINGS.items():
            if any(ext in unique_file_types for ext in extensions):
                needed_folders.add(folder_name)
        
        # Remove and recreate needed folders
        for folder in needed_folders:
            folder_path = os.path.join(base_path, folder)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, onerror=remove_readonly)
            os.makedirs(folder_path)
            folder_paths[folder] = folder_path
            logging.info(f"Created folder: {folder_path}")
        
        return None
    
    except PermissionError as e:
        logging.error(f"Permission denied creating folders in {base_path}: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Error creating folders: {str(e)}")
        raise

def ai_move_files_to_folder(source_folder: str) -> None:
    """
    Moves files from source folder to their respective organized folders.
    
    Args:
        source_folder (str): Path to the source folder containing files to organize
        folder_paths (Dict[str, str]): Mapping of folder categories to their paths

    Raises:
        FileNotFoundError: If source folder doesn't exist
        PermissionError: If there are insufficient permissions
    """
    try:
        if not os.path.exists(source_folder):
            raise FileNotFoundError(f"Source folder not found: {source_folder}")
        
        for filename in os.listdir(source_folder):
            if '.' not in filename:
                continue
                
            file_extension = filename.split('.')[-1].lower()
            source_path = os.path.join(source_folder, filename)
            
            # Determine destination folder
            dest_folder = None
            for folder_name, extensions in FILE_TYPE_MAPPINGS.items():
                if file_extension in extensions:
                    dest_folder = folder_paths.get(folder_name)
                    break
            
            if dest_folder:
                dest_path = os.path.join(dest_folder, filename)
                shutil.move(source_path, dest_path)
                logging.info(f"Moved {filename} to {dest_folder}")
    
    except (FileNotFoundError, PermissionError) as e:
        logging.error(f"Error accessing files: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Error moving files: {str(e)}")
        raise

def organize_files(source_path: str, base_path: str = ".") -> None:
    """
    Main function to organize files from source directory into categorized folders.
    
    Args:
        source_path (str): Path to the source directory containing files to organize
        base_path (str): Base directory for creating organized folders
    """
    try:
        files_list = ai_get_file_list(source_path)
        unique_file_types = ai_get_unique_file_types()
        folder_paths = ai_create_folders(base_path)
        ai_move_files_to_folder(source_path)
        logging.info("File organization completed successfully")
    
    except Exception as e:
        logging.error(f"File organization failed: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    organize_files("../un_organized")