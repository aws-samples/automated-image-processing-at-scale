# Automated image processing at scale
This application uses AWS Serverless and Adobe API endpoints to automate image manipulation at scale. It was designed to process player photos for sporting industries but can be modified for many other uses. When images are dropped into the raw-image bucket they are sent to Adobe to have the background removed and run an auto crop process to reduce the image to just the subject. We then use Rekognition to identify the face of the player and crop the photo according to the desired height of the body. The result is uniform sizing across all the images.

The entire process is event driven. When images are furst dropped in the RawImagesBucket, this triggers the CutOutStateMachine to call the Adobe API to process the image. The updated image is then dropped in the CutOutImagesBucket which triggers the next step and so on.

*Note: this application was built using AWS Application Composer. If you are using VSCode and have the latest AWS Toolkit installed. There is an icon in the top left that will open this project in a local version of App Composer.*

![App Composer Icon](static/icon.png)

**AWS services used**
* AWS Step Functions
* AWS Lambda
* Amazon EventBridge
* Amazon S3
* AWS Secrets Manager
* AWS App Composer (for building)
* Amazon Rekognition

**Adobe APIs used**
* Adobe Photoshop CutOut API
* Adobe Photoshop Crop API

## Preparing to install

### Requirements
* An Adobe developer account https://developer.adobe.com/
* An AWS account https://aws.amazon.com/free/
* AWS CLLI https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
* AWS SAM https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
* Docker

### Steps
**Adobe**
1. Create a new project in the Adobe Developer console.
1. Add the Photoshop API
1. Retrieve the ClientId, Client Secret, and Organization ID from the Credentials (Oauth server to server) section

**AWS**
1. Create a secret in AWS Secrets Manager called `aip/oauth` with the following information:
    ```
    {
        "client_id":"<Adobe client id>>",
        "client_secret":"<Adobe client secret",
        "org_id":"<Adobe org id>"
    }
    ```
1. From within the root of the project, build the stack using AWS SAM (--use-container tells SAM to build using containers instead of you having to configure node and python.)
    ```
    sam build --use-container
    ```
1. The deploy the stack using AWS SAM (The -g is a guided deploy)
    ```
    sam deploy -g
    ```
    * Choose your desired stack name
    * Choose your region
    * take defaults for the rest

## Testing the service
After deployment, the following resources are in place. These are logical names to help understand what they are doing.

![Application Architecture](static/arch.png "Application Architecture")

The stack will also output the list of buckets for your files. It will look similar to this:

![Outputs](static/outputs.png "Output list of buckets")

Copy as many raw images into the RawImagesBucket as you like. Each one will run through the entire process.

1. Background removed: saved to CutOutImagesBucket
1. Image cropped: saved to the CroppedImagesBucket
1. Image smart cropped: saved to the SmartCroppedBucket

## Tear down
1. First, make sure all buckets are empty
1. Run the following AWS SAM command:
    ```
    sam delete
    ```