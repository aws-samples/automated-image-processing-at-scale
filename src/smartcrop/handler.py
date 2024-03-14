import boto3
from PIL import Image
import io
import os

# Initialize the S3 client
s3_client = boto3.client('s3')

# Global parameters for easy configuration
TARGET_FACE_WIDTH = 818
DISTANCE_FROM_TOP = 532
CANVAS_WIDTH = 3200
CANVAS_HEIGHT = 2450

def fetch_image(bucket_name, object_key):
    """Fetch an image from an S3 bucket."""
    file_byte_string = s3_client.get_object(Bucket=bucket_name, Key=object_key)['Body'].read()
    return Image.open(io.BytesIO(file_byte_string))

def process_image(image, bounding_box):
    """Process the image to ensure the face is centered horizontally and at a specified distance from the top of the canvas after scaling, maintaining transparency if present."""
    width, height = image.size

    # Check if the image has an alpha channel
    has_alpha = image.mode == 'RGBA'

    # Extract face bounding box details
    face_x = bounding_box['Left'] * width
    face_y = bounding_box['Top'] * height
    face_width = bounding_box['Width'] * width
    face_height = bounding_box['Height'] * height

    # Calculate scale factor to make the face width equal to the target face width
    scale_factor = TARGET_FACE_WIDTH / face_width
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    # Resize the image
    scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Calculate the new face position on the scaled image
    new_face_x = face_x * scale_factor
    new_face_y = face_y * scale_factor

    # Calculate the center of the face on the scaled image (horizontally)
    new_face_center_x = new_face_x + TARGET_FACE_WIDTH / 2

    # Calculate the offsets to position the scaled face at the center of the canvas horizontally
    offset_x = (CANVAS_WIDTH / 2) - new_face_center_x

    # Set the vertical offset to position the top of the face at the specified distance from the top of the canvas
    offset_y = DISTANCE_FROM_TOP - new_face_y

    # Create a new canvas and paste the scaled image onto it
    # If the image has an alpha channel, the canvas should support transparency
    canvas_mode = 'RGBA' if has_alpha else 'RGB'
    canvas_background = (255, 255, 255, 0) if has_alpha else 'white'
    canvas = Image.new(canvas_mode, (CANVAS_WIDTH, CANVAS_HEIGHT), canvas_background)
    canvas.paste(scaled_image, (int(offset_x), int(offset_y)), scaled_image if has_alpha else None)

    return canvas



def save_to_s3(image, bucket_name, object_key):
    """Save the processed image to an S3 bucket."""
    output_buffer = io.BytesIO()
    image.save(output_buffer, format='PNG', dpi=(300, 300))
    output_buffer.seek(0)
    s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=output_buffer, ContentType='image/png')

def handler(event, context):
    try:
        source_bucket = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']
        target_bucket = os.environ['SMARTCROPPEDIMAGESBUCKET_BUCKET_NAME']
        
        image = fetch_image(source_bucket, object_key)
        bounding_box = event['dimensions']['FaceDetails'][0]['BoundingBox']
        processed_image = process_image(image, bounding_box)
        save_to_s3(processed_image, target_bucket, object_key)
        
        return {'status': 'SUCCESS'}
    
    except Exception as e:
        # Attempting to get the full traceback to understand the source of 'object' message
        import traceback
        error_message = traceback.format_exc()  # This will give the stack trace as a string
        print(error_message)  # Log the full traceback
        return {'status': 'FAILURE', 'error': 'An error occurred, please check the logs for more details'}
