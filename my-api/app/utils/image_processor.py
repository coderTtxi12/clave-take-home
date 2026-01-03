"""
Image processing utilities for coding agent
"""
import base64
from pathlib import Path
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


def extract_image_paths_from_results(results: List[Dict[str, Any]]) -> List[str]:
    """
    Extract IMAGE: markers from execution results
    
    Args:
        results: List of execution results from code executor
        
    Returns:
        List of image paths found in results
    """
    image_paths = []
    
    for result in results:
        # Check for IMAGE: markers in results
        for result_line in result.get("results", []):
            if isinstance(result_line, str) and "IMAGE:" in result_line:
                # Extract image path from each line
                for line in result_line.split("\n"):
                    if line.strip().startswith("IMAGE:"):
                        image_path = line.replace("IMAGE:", "").strip()
                        image_paths.append(image_path)
                        logger.info(f"Found image marker: {image_path}")
    
    return image_paths


def convert_image_to_base64(image_path: str) -> Dict[str, Any]:
    """
    Convert an image file to base64 string
    
    Args:
        image_path: Relative path to image (e.g., 'outputs/chart.png')
        
    Returns:
        Dictionary with:
            - success: bool
            - base64_data: str (if success)
            - filename: str (if success)
            - mime_type: str (if success)
            - error: str (if failure)
    """
    try:
        # Construct full path
        full_path = Path(settings.BASE_DIR) / image_path
        
        if not full_path.exists():
            logger.warning(f"Image not found: {full_path}")
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        # Read image and convert to base64
        with open(full_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Determine MIME type from extension
        extension = full_path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
        }
        mime_type = mime_types.get(extension, 'image/png')
        
        logger.info(f"Successfully converted image: {image_path}")
        
        return {
            "success": True,
            "base64_data": img_data,
            "filename": full_path.name,
            "mime_type": mime_type,
            "original_path": image_path
        }
        
    except Exception as e:
        logger.error(f"Failed to convert image {image_path}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def embed_images_in_markdown(markdown_text: str, image_paths: List[str]) -> str:
    """
    Replace IMAGE: markers in markdown with base64 embedded images
    
    Args:
        markdown_text: Original markdown text with IMAGE: markers
        image_paths: List of image paths to embed
        
    Returns:
        Markdown text with embedded base64 images
    """
    result_text = markdown_text
    
    for img_path in image_paths:
        # Convert image to base64
        conversion = convert_image_to_base64(img_path)
        
        if conversion["success"]:
            # Create markdown image with base64
            img_markdown = f"\n\n![{conversion['filename']}](data:{conversion['mime_type']};base64,{conversion['base64_data']})\n\n"
            
            # Replace IMAGE: marker with actual embedded image
            result_text = result_text.replace(f"IMAGE:{img_path}", img_markdown)
            
            logger.info(f"Embedded image in markdown: {img_path}")
        else:
            # Replace with error message
            result_text = result_text.replace(
                f"IMAGE:{img_path}", 
                f"\n\n*[Image Error: {conversion.get('error', 'Unknown error')}]*\n\n"
            )
            logger.error(f"Failed to embed image: {conversion.get('error')}")
    
    return result_text


def process_agent_response_with_images(
    final_answer: str, 
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Main function to process agent response and extract image data
    
    Args:
        final_answer: The LLM's final answer text
        results: List of execution results from code executor
        
    Returns:
        Dictionary with:
            - answer: Final answer text (Markdown without IMAGE: markers)
            - image_base64: Base64 encoded image data (if any)
            - image_mime: MIME type of the image (if any)
    """
    # Extract image paths from results
    image_paths = extract_image_paths_from_results(results)
    
    if not image_paths:
        logger.info("No images found in results")
        return {
            "answer": final_answer,
            "image_base64": None,
            "image_mime": None
        }
    
    logger.info(f"Processing {len(image_paths)} image(s)")
    
    # Process only the first image (for now, can be extended to support multiple)
    first_image = image_paths[0]
    conversion = convert_image_to_base64(first_image)
    
    # Remove IMAGE: markers from the answer
    cleaned_answer = final_answer
    for img_path in image_paths:
        cleaned_answer = cleaned_answer.replace(f"IMAGE:{img_path}", "").strip()
    
    if conversion["success"]:
        return {
            "answer": cleaned_answer,
            "image_base64": conversion["base64_data"],
            "image_mime": conversion["mime_type"]
        }
    else:
        logger.error(f"Failed to convert image: {conversion.get('error')}")
        return {
            "answer": cleaned_answer,
            "image_base64": None,
            "image_mime": None
        }

