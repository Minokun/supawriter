import requests
import base64
import os
import json
API_URL = "http://localhost:1234/v1/chat/completions"
sample_prompt = """
Analyze this image. If it is a promotional image, advertisement, icon, or any other type of image that does not convey specific information, mark its status as deleted with `is_deleted` set to `true`.  
For other images, provide a detailed description of the image content in `describe` in Chinese. Then, compare it with the theme '{theme}' to determine relevance. If relevant, mark `is_related` as `true`; otherwise, mark it as `false`.

Respond ONLY with a valid JSON object in this exact format (use true/false):
{
    "is_deleted": false,
    "describe": "Description of the image in Chinese",
    "is_related": false
}
"""
def call_gemma3_api(prompt=sample_prompt, image_path: str = None, image_url: str = None, image_content: bytes = None):
    """
    Calls the gemmar3 multimodal API with a prompt and an image.
    The image can be provided in one of three ways:
    1. As a local file path
    2. As a URL to download from
    3. As raw binary content already retrieved

    Args:
        prompt: The text prompt to send to the model.
        image_path: The path to the local image file (optional).
        image_url: The URL of the image to download (optional).
        image_content: Raw binary image content already retrieved (optional).

    Returns:
        Parsed JSON content from the API response or None if an error occurs.
    """
    
    # Check that exactly one image source is provided
    sources_provided = sum(x is not None for x in [image_path, image_url, image_content])
    if sources_provided == 0:
        print("Error: One of image_path, image_url, or image_content must be provided")
        return None
    elif sources_provided > 1:
        print("Warning: Multiple image sources provided. Using the first available in order: image_path, image_url, image_content")
    
    # Get image content as base64
    try:
        if image_path is not None:
            # Load from local file
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
        elif image_url is not None:
            # Download from URL
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            image_base64 = base64.b64encode(response.content).decode('utf-8')
        elif image_content is not None:
            # Use already retrieved content
            image_base64 = base64.b64encode(image_content).decode('utf-8')
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

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
                "content": "You are a helpful assistant specialized in image analysis and description. Analyze images thoroughly and provide detailed descriptions. Always respond with valid, properly formatted JSON. Avoid markdown formatting in your responses. If asked to evaluate or classify images, be precise and consistent in your assessments. Focus on visual elements, text content, and contextual information present in the image."   
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
        
        # Get the raw API response
        api_response = response.json()
        
        # Extract the content from the response
        if api_response and 'choices' in api_response and len(api_response['choices']) > 0:
            content = api_response['choices'][0]['message']['content']
            # print(f"Raw API response content: {content}")
            
            # Clean up the content if it's wrapped in markdown code blocks or has extra whitespace
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Handle potential leading/trailing characters that might break JSON parsing
            # Remove any non-JSON text before the first { and after the last }
            try:
                start_idx = content.index('{')
                end_idx = content.rindex('}') + 1
                content = content[start_idx:end_idx]
            except ValueError:
                print("Could not find valid JSON markers in content")
            
            # Try to parse the JSON content
            try:
                result = json.loads(content)
                # print(f"Successfully parsed JSON: {result}")
                return result
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from API response: {e}")
                # Try a more lenient approach - handle Python style booleans and quotes
                try:
                    import re
                    # Replace Python True/False with JSON true/false
                    content = re.sub(r"True", "true", content)
                    content = re.sub(r"False", "false", content)
                    # Replace 'true' and 'false' with true and false (without quotes)
                    content = re.sub(r"'true'", "true", content)
                    content = re.sub(r"'false'", "false", content)
                    # Replace remaining single quotes with double quotes
                    content = content.replace("'", '"')
                    result = json.loads(content)
                    print(f"Successfully parsed JSON after cleanup: {result}")
                    return result
                except json.JSONDecodeError as e2:
                    print(f"Still failed to parse JSON after cleanup: {e2}")
                    return {"error": "JSON parsing failed", "raw_content": content}
        
        print("Invalid or incomplete API response structure")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemmar3 API: {e}")
        return None