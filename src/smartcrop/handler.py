import boto3
from PIL import Image
import io
import os
import logging
import traceback

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the S3 client
s3_client = boto3.client('s3')

# Global parameters for easy configuration
BOUNDARY_WIDTH = 818
BOUNDARY_HEIGHT = 1037
DISTANCE_FROM_TOP = 532
CANVAS_WIDTH = 3200
CANVAS_HEIGHT = 2450

def fetch_image(bucket_name, object_key):
    """Fetch an image from an S3 bucket."""
    try:
        file_byte_string = s3_client.get_object(Bucket=bucket_name, Key=object_key)['Body'].read()
        return Image.open(io.BytesIO(file_byte_string))
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Error fetching image from {bucket_name}/{object_key}: {e}")
        raise

def process_image(image, bounding_box):
    """Process the image to ensure the face fits within a specified boundary and is centered."""
    try:
        width, height = image.size
        has_alpha = image.mode == 'RGBA'
        
        # Extract face bounding box details
        face_x = bounding_box['Left'] * width
        face_y = bounding_box['Top'] * height
        face_width = bounding_box['Width'] * width
        face_height = bounding_box['Height'] * height
        
        # Calculate scale factors for width and height
        scale_factor_width = BOUNDARY_WIDTH / face_width
        scale_factor_height = BOUNDARY_HEIGHT / face_height
        
        # Use the smaller scale factor to fit the face within the boundary
        scale_factor = min(scale_factor_width, scale_factor_height)
        
        # Scale the image
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Calculate the new face position
        new_face_x = face_x * scale_factor
        new_face_y = face_y * scale_factor
        new_face_center_x = new_face_x + (face_width * scale_factor) / 2
        
        # Offset to center the face horizontally and set its top at the specified distance from the canvas top
        offset_x = (CANVAS_WIDTH / 2) - new_face_center_x
        offset_y = DISTANCE_FROM_TOP - new_face_y
        
        # Create a new canvas and paste the scaled image
        canvas_mode = 'RGBA' if has_alpha else 'RGB'
        canvas_background = (255, 255, 255, 0) if has_alpha else 'white'
        canvas = Image.new(canvas_mode, (CANVAS_WIDTH, CANVAS_HEIGHT), canvas_background)
        canvas.paste(scaled_image, (int(offset_x), int(offset_y)), scaled_image if has_alpha else None)
        
        return canvas
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise

def save_to_s3(image, bucket_name, object_key):
    """Save the processed image to an S3 bucket."""
    try:
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG', dpi=(300, 300))
        output_buffer.seek(0)
        s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=output_buffer, ContentType='image/png')
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Error saving image to {bucket_name}/{object_key}: {e}")
        raise

def handler(event, context):
    """AWS Lambda handler function."""
    try:
        logger.info("Handler started")
        source_bucket = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']
        target_bucket = os.environ['SMARTCROPPEDIMAGESBUCKET_BUCKET_NAME']

        image = fetch_image(source_bucket, object_key)
        bounding_box = event['dimensions']['FaceDetails'][0]['BoundingBox']
        processed_image = process_image(image, bounding_box)
        save_to_s3(processed_image, target_bucket, object_key)

        return {'status': 'SUCCESS'}
    except Exception as e:
        logger.error(f"Unhandled exception in handler: {traceback.format_exc()}")
        return {'status': 'FAILURE', 'error': str(e)}
