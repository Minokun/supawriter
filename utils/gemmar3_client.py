import requests
import base64
import os
import json
API_URL = "http://localhost:1234/v1/chat/completions"
sample_prompt = """
    Translate into English: View the image. If it is a promotional image, advertisement, icon, or any other type of image that does not convey specific information, mark its status as deleted with `is_deleted` set to `True`.  
    For other images, provide a detailed description of the image content in `describe` by Chinese. Then, compare it with the theme {theme} to determine relevance. If relevant, mark `is_related` as `True`; otherwise, mark it as `False`.  
    The final output format should be json format not markdown:  
        {
            "is_deleted": true/false,
            "describe": "",
            "is_related": true/false
        }
    """
def call_gemma3_api(prompt: str, image_path: str):
    """
    Calls the gemmar3 multimodal API with a prompt and an image file path.
    The image will be converted to base64 internally.

    Args:
        prompt: The text prompt to send to the model.
        image_path: The path to the local image file.

    Returns:
        The JSON response from the API or None if an error occurs.
    """
    image_base64 = base64.b64encode(open(image_path, 'rb').read()).decode('utf-8')

    headers = {
        "Content-Type": "application/json",
        # Add any other necessary headers, like Authorization if required
        # "Authorization": "Bearer YOUR_API_KEY"
    }

    payload = {
        "model": "gemmar3", # Or the specific model name your server expects
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."   
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 5000  # Optional: Adjust as needed
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemmar3 API: {e}")
        return None

if __name__ == '__main__':
    # Example usage (requires a running server and a sample image)
    
    # Point to the specific image in the project's images directory
    # Script's directory: os.path.dirname(__file__) (e.g., /Users/wxk/Desktop/workspace/supawriter/utils)
    # Project root is one level up from the script's directory.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    image_dir = "images/task_191976"
    theme = "数字货币"
    
    for image_filename in os.listdir(image_dir):
        image_path = os.path.join(image_dir, image_filename)
        if os.path.exists(image_path):
            print(f"[INFO] Sending request to {API_URL} with image {image_path}...")
            # To run this example, you need to have the server at API_URL running.
            result = call_gemma3_api(sample_prompt, image_path=image_path)
            if result:
                print("[SUCCESS] API Response:")
                print(result)
            else:
                print("[ERROR] Failed to get response from API.")
        print(f"[INFO] Example API call with '{image_path}' executed. Ensure server was running to see results.")
    else:
        print(f"[WARNING] Dummy image '{image_path}' not found or could not be created. Skipping example API call.")
