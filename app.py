import platform
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import torch
from diffusers import StableDiffusion3Pipeline
from transformers import CLIPTokenizer
from PIL import Image
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load the env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect the operating system
OPERATING_SYSTEM = platform.system()
logger.info(f"Detected operating system: {OPERATING_SYSTEM}")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Swagger UI
api = Api(app, version='1.0', title='Image Generation API',
          description='API for generating, listing, and downloading images using Stable Diffusion 3')

# Initialize model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

try:
    # Initialize the fast tokenizer
    tokenizer = CLIPTokenizer.from_pretrained("stabilityai/stable-diffusion-3-medium-diffusers", subfolder="tokenizer")
    
    pipe = StableDiffusion3Pipeline.from_pretrained(
        "stabilityai/stable-diffusion-3-medium-diffusers",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        use_safetensors=True,
        variant="fp16" if torch.cuda.is_available() else None,
        tokenizer=tokenizer  # Use the fast tokenizer
    ).to(device)
    
    # Enable model optimization
    if torch.cuda.is_available():
        pipe.enable_model_cpu_offload()
    
    logger.info("Model loaded successfully with optimizations and fast tokenizer")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

# Define the expected input model
generate_model = api.model('GenerateImage', {
    'prompt': fields.String(required=True, description='The prompt for image generation'),
    'negative_prompt': fields.String(description='The negative prompt for image generation'),
    'steps': fields.Integer(default=30, description='Number of inference steps'),
    'guidance_scale': fields.Float(default=7.5, description='Guidance scale for generation')
})

# Define the response model for the generate endpoint
generate_response = api.model('GenerateResponse', {
    'filename': fields.String(description='Filename of the generated image on the server')
})

# Define the response model for the list files endpoint
list_files_response = api.model('ListFilesResponse', {
    'files': fields.List(fields.String, description='List of generated image filenames')
})

@api.route('/')
class Home(Resource):
    @api.doc(description="Check if the server is running")
    @api.response(200, 'Success')
    def get(self):
        """Check if the server is running"""
        return {"message": "Image Generation Server is running"}

@api.route('/generate')
class GenerateImage(Resource):
    @api.expect(generate_model)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error',
        500: 'Internal Server Error'
    })
    @api.response(200, 'Success', generate_response)
    def post(self):
        """Generate an image based on the provided prompt and save it on the server"""
        try:
            data = request.json
            prompt = data.get('prompt', '')
            if not prompt:
                api.abort(400, "No prompt provided")

            negative_prompt = data.get('negative_prompt', '')
            steps = int(data.get('steps', 30))
            guidance_scale = float(data.get('guidance_scale', 7.5))

            logger.info(f"Generating image with prompt: {prompt}")

            try:
                with torch.inference_mode():
                    output = pipe(prompt=prompt, negative_prompt=negative_prompt,
                                  num_inference_steps=steps, guidance_scale=guidance_scale)
                
                image = output.images[0]
                
                # Save the image on the server
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_image_{timestamp}.png"
                save_path = os.path.join("generated_images", filename)
                os.makedirs("generated_images", exist_ok=True)
                image.save(save_path)
                logger.info(f"Image saved on server: {save_path}")
                
                return jsonify({"filename": filename})
            except Exception as e:
                logger.error(f"Error during image generation: {str(e)}")
                api.abort(500, f"Error during image generation: {str(e)}")

        except Exception as e:
            logger.error(f"Error in generate_image route: {str(e)}")
            api.abort(500, f"Internal Server Error: {str(e)}")

@api.route('/download/<filename>')
@api.doc(params={'filename': 'Filename of the image to download'})
class DownloadImage(Resource):
    @api.doc(responses={
        200: 'Success',
        404: 'Image not found'
    })
    @api.produces(['image/png'])
    def get(self, filename):
        """Download a generated image"""
        try:
            return send_from_directory("generated_images", filename, as_attachment=True)
        except FileNotFoundError:
            api.abort(404, "Image not found")

@api.route('/list')
class ListFiles(Resource):
    @api.doc(description="List all generated image files")
    @api.response(200, 'Success', list_files_response)
    def get(self):
        """List all generated image files"""
        try:
            files = os.listdir("generated_images")
            # Filter out any non-image files if necessary
            image_files = [f for f in files if f.endswith('.png')]
            return jsonify({"files": image_files})
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            api.abort(500, f"Error listing files: {str(e)}")

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return {"error": "Not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Allow connections from any IP
    logger.info(f"Starting server on {host}:{port}")
    app.run(debug=False, port=port, host=host)
