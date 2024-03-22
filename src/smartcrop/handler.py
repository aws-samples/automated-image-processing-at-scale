import io
import os
import boto3
from PIL import Image

s3_client = boto3.client('s3')

def download_image(bucket, key):
    """Download an image from S3 and return a PIL Image object."""
    image_buffer = io.BytesIO()
    s3_client.download_fileobj(Bucket=bucket, Key=key, Fileobj=image_buffer)
    image_buffer.seek(0)
    return Image.open(image_buffer)

def upload_image(image, object_key):
    """Upload an image to the specified S3 bucket using an in-memory bytes buffer."""
    target_bucket = os.environ['SMARTCROPPEDIMAGESBUCKET_BUCKET_NAME']
    output_buffer = io.BytesIO()
    image.save(output_buffer, format='PNG')
    output_buffer.seek(0)
    s3_client.put_object(Bucket=target_bucket, Key=object_key, Body=output_buffer, ContentType='image/png')

def process_image(image, landmarks):
    canvas_width, canvas_height = 3200, 2450
    target_eye_distance = 170
    target_eye_level = 988

    # Extract eye landmark positions
    left_eye_right = next(item for item in landmarks if item['Type'] == 'leftEyeRight')
    right_eye_left = next(item for item in landmarks if item['Type'] == 'rightEyeLeft')

    # Calculate the initial scale factor for the eye distance
    eye_distance = (right_eye_left['X'] - left_eye_right['X']) * image.width
    scale_factor = target_eye_distance / eye_distance

    # Apply the initial scaling
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    # Calculate the eye center position after initial scaling
    avg_eye_y_scaled = (((left_eye_right['Y'] + right_eye_left['Y']) / 2) * new_height)
    image_top = target_eye_level - int(avg_eye_y_scaled)

    # Adjust scaling if the image doesn't reach the canvas bottom
    if image_top + new_height < canvas_height:
        # Calculate the additional scale factor required
        additional_scale_factor = ((canvas_height - target_eye_level) + avg_eye_y_scaled) / new_height
        new_width = int(image.width * additional_scale_factor)
        new_height = int(image.height * additional_scale_factor)
        resized_image = resized_image.resize((new_width, new_height), Image.LANCZOS)
        
        # Recalculate the eye position and image top after additional scaling
        avg_eye_y_scaled = (((left_eye_right['Y'] + right_eye_left['Y']) / 2) * new_height)
        image_top = target_eye_level - int(avg_eye_y_scaled)

    # Center the image horizontally
    eye_center_x_scaled = ((left_eye_right['X'] + right_eye_left['X']) / 2) * new_width
    image_left = (canvas_width // 2) - int(eye_center_x_scaled)

    # Create a new canvas and paste the resized image
    canvas = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
    canvas.paste(resized_image, (int(image_left), int(image_top)), resized_image)

    return canvas

def handler(event, context):
    try:
        source_bucket = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']
        landmarks = event['dimensions']['FaceDetails'][0]['Landmarks']

        image = download_image(source_bucket, object_key)
        processed_image = process_image(image, landmarks)
        upload_image(processed_image, object_key)

        return {'status': 'success', 'body': 'Image processing and upload successful'}
    except Exception as e:
        return {'status': 'fail', 'error': str(e)}
