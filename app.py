import platform
import sys
from flask import Flask, request, jsonify, send_file, Response
import torch
from diffusers import StableDiffusion3Pipeline
from transformers import CLIPTokenizerFast
from PIL import Image
import io
import base64
import uuid
import json
from huggingface_hub import login
import os
import traceback

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect the operating system
OPERATING_SYSTEM = platform.system()
logger.info(f"Detected operating system: {OPERATING_SYSTEM}")

try:
    login(token="")
except Exception as e:
    logger.error(f"Failed to login to Hugging Face: {str(e)}")
    raise

app = Flask(__name__)

# Initialize model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

try:
    # Load the fast tokenizer
    #tokenizer = CLIPTokenizerFast.from_pretrained("stabilityai/stable-diffusion-3-base")

    # Initialize the pipeline with the fast tokenizer
    pipe = StableDiffusion3Pipeline.from_pretrained(
        "stabilityai/stable-diffusion-3-medium-diffusers", 
        torch_dtype=torch.float32,
    #    tokenizer=tokenizer
    ).to(device)
    pipe.text_encoder.to("cpu")
    pipe.text_encoder_2.to("cpu")
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

def get_image_url(image_path):
    if OPERATING_SYSTEM == "Windows":
        return f"/images/{image_path.replace(os.path.sep, '/')}"
    else:
        return f"/images/{image_path}"

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
                    # Decode and preprocess the initial image
                    init_image = Image.open(io.BytesIO(base64.b64decode(init_image_str))).convert("RGB")
                    init_image = init_image.resize((512, 512))
                    
                    # Generate the image
                    for i, _ in enumerate(pipe(prompt=prompt, image=init_image, strength=strength,
                                               negative_prompt=negative_prompt, num_inference_steps=steps, 
                                               guidance_scale=guidance_scale)):
                        yield f"data: {json.dumps({'progress': (i + 1) / steps * 100})}\n\n"
                else:
                    # Generate the image without initial image
                    for i, _ in enumerate(pipe(prompt=prompt, negative_prompt=negative_prompt,
                                               num_inference_steps=steps, guidance_scale=guidance_scale)):
                        yield f"data: {json.dumps({'progress': (i + 1) / steps * 100})}\n\n"

                # Save the image
                image = pipe.images[0]
                image_id = str(uuid.uuid4())
                image_path = os.path.join("generated_images", f"{image_id}.png")
                os.makedirs("generated_images", exist_ok=True)
                image.save(image_path)

                image_url = get_image_url(image_path)
                yield f"data: {json.dumps({'image_path': image_url})}\n\n"
            except Exception as e:
                logger.error(f"Error during image generation: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        logger.error(f"Error in generate_image route: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/images/<path:image_path>')
def serve_image(image_path):
    full_path = os.path.join("generated_images", image_path)
    return send_file(full_path, mimetype='image/png')

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Determine the appropriate host based on the operating system
    if OPERATING_SYSTEM == "Windows":
        host = '127.0.0.1'  # Use localhost for Windows
    else:
        host = '0.0.0.0'  # Bind to all interfaces for macOS and Linux
    
    app.run(debug=False, port=5000, host=host)