import platform
import sys
from flask import Flask, request, jsonify, send_file, Response
import torch
from diffusers import StableDiffusion3Pipeline
from transformers import CLIPTokenizerFast
from PIL import Image
import io
import base64
import json
from huggingface_hub import login
import os
import traceback
from dotenv import load_dotenv

# Load the env file
load_dotenv()

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect the operating system
OPERATING_SYSTEM = platform.system()
logger.info(f"Detected operating system: {OPERATING_SYSTEM}")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

try:
    login(token=os.getenv("HF_TOKEN"))
except Exception as e:
    logger.error(f"Failed to login to Hugging Face: {str(e)}")
    raise

app = Flask(__name__)

# Initialize model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

try:
    pipe = StableDiffusion3Pipeline.from_pretrained(
        "stabilityai/stable-diffusion-3-medium-diffusers", 
        torch_dtype=torch.float16,
    ).to(device)
    pipe.text_encoder.to("cpu")
    pipe.text_encoder_2.to("cpu")
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise
    
@app.route('/')
def home():
    logger.info("Root route accessed")
    return "Image Generation Server is running"

@app.route('/generate', methods=['POST'])
def generate_image():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        negative_prompt = data.get('negative_prompt', '')
        steps = int(data.get('steps', 28))
        guidance_scale = float(data.get('guidance_scale', 7.0))
        init_image_str = data.get('init_image')
        strength = float(data.get('strength', 0.8))

        def generate():
            try:
                if init_image_str:
                    init_image = Image.open(io.BytesIO(base64.b64decode(init_image_str))).convert("RGB")
                    init_image = init_image.resize((512, 512))
                    
                    for i, _ in enumerate(pipe(prompt=prompt, image=init_image, strength=strength,
                                               negative_prompt=negative_prompt, num_inference_steps=steps, 
                                               guidance_scale=guidance_scale)):
                        yield f"data: {json.dumps({'progress': (i + 1) / steps * 100})}\n\n"
                else:
                    for i, _ in enumerate(pipe(prompt=prompt, negative_prompt=negative_prompt,
                                               num_inference_steps=steps, guidance_scale=guidance_scale)):
                        yield f"data: {json.dumps({'progress': (i + 1) / steps * 100})}\n\n"

                # Get the generated image
                image = pipe.images[0]
                
                # Convert PIL Image to base64
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                yield f"data: {json.dumps({'image': img_str})}\n\n"
            except Exception as e:
                logger.error(f"Error during image generation: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        logger.error(f"Error in generate_image route: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    host = '127.0.0.1' if OPERATING_SYSTEM == "Windows" else '0.0.0.0'
    app.run(debug=False, port=5000, host=host)
