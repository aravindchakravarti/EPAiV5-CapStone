import os
import requests
import logging

# Supported image formats for compression
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}

# reSmush.it API URL for image compression
API_URL = "https://api.resmush.it/ws.php"

def compress_image(image_path, output_path, quality=80) -> None:
    """
    Compress a single image using the reSmush.it API.

    Args:
        image_path (str): Path to the image file to be compressed.
        output_path (str): Path where the compressed image will be saved.
        quality (int): Compression quality (1-100), with higher values meaning better quality.
    
    Returns:
        None
    """
    try:
        # Open the image file in binary mode
        with open(image_path, "rb") as img_file:
            files = {"files": img_file}
            params = {"qlty": quality}  # Set quality parameter for the API request
            
            # Send POST request to the reSmush.it API
            response = requests.post(API_URL, files=files, params=params)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # If compression is successful, download the optimized image
            if "dest" in data:
                img_data = requests.get(data["dest"]).content
                with open(output_path, "wb") as out_file:
                    out_file.write(img_data)
                logging.info(f"Compressed: {image_path} -> {output_path}")
            else:
                logging.info(f"Failed to compress {image_path}: {data}")
        else:
            logging.info(f"Error {response.status_code} while processing {image_path}")
    except Exception as e:
        logging.info(f"An error occurred while compressing {image_path}: {e}")

def ai_compress_images_in_folder(folder_path: str) -> None:
    """
    Recursively compress all images in the specified folder and subdirectories.

    Parameters:
        folder_path (str): Path to the folder containing images to be compressed.
    """
    for root, _, files in os.walk(folder_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            ext = os.path.splitext(filename)[-1].lower()
            
            if ext in VALID_EXTENSIONS:
                output_file = os.path.join(root, 'compressed_' + filename)
                compress_image(file_path, output_file)

if __name__ == "__main__":
    # Specify the folder containing images and start compression
    ai_compress_images_in_folder("un_organized")
