import torch
from diffusers import AutoPipelineForText2Image, DiffusionPipeline
from PIL import Image
import os

def load_model():


    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    model_id = "black-forest-labs/FLUX.1-dev"
    
    try:
        # Load the base model
        pipeline = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=torch.float16)
        pipeline = pipeline.to(device)

        pipeline.load_lora_weights("XLabs-AI/flux-RealismLora", weight=1)
        print(f"Realism LoRA weights loaded!")

        
        print("Model loaded successfully!")
        return pipeline
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def calculate_dimensions(aspect_ratio):
    # Base resolution
    base_res = 1080
    
    if aspect_ratio == "16:9":
        return (16 * base_res) // 9, base_res
    elif aspect_ratio == "4:3":
        return (4 * base_res) // 3, base_res
    elif aspect_ratio == "1:1":
        return base_res, base_res
    else:
        print(f"Unsupported aspect ratio: {aspect_ratio}. Using default 16:9.")
        return (16 * base_res) // 9, base_res

def generate_images_batch(pipeline, prompts, output_dir, start_sequence_number, aspect_ratio="16:9"):
    try:
        width, height = calculate_dimensions(aspect_ratio)
        
        # Generate images in batch
        images = pipeline(
            prompt=prompts, 
            num_inference_steps=30, 
            guidance_scale=7.5,
            width=width,
            height=height
        ).images
        
        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the images
        for i, (image, prompt) in enumerate(zip(images, prompts)):
            sequence_number = start_sequence_number + i
            filename = f"{sequence_number:03d}_{prompt[:20].replace(' ', '_')}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)
            print(f"Image saved as {filepath}")
        
    except Exception as e:
        print(f"An error occurred during image generation: {e}")

def main():
    print("FLUX Image Generator using Diffusers (Batch Processing)")
    
    print("Loading model... This may take a few minutes.")
    pipeline = load_model()
    if pipeline is None:
        print("Failed to load the model. Exiting.")
        return

    output_dir = "generated_images"
    sequence_number = 1

    print("\nModel loaded and ready for use!")
    print("Enter your prompts to generate images. Enter an empty line to process the batch.")
    print("Type 'quit' to exit.")
    
    while True:
        prompts = []
        aspect_ratio = input("Enter aspect ratio (16:9, 4:3, or 1:1) [default: 16:9]: ").strip()
        if not aspect_ratio:
            aspect_ratio = "16:9"
        
        while True:
            prompt = input(f"Enter prompt {len(prompts) + 1} (or press Enter to process batch): ")
            if prompt.lower() in ['quit', 'exit']:
                print("Thank you for using the FLUX Image Generator. Goodbye!")
                return
            if prompt == "":
                break
            prompts.append(prompt)
        
        if prompts:
            generate_images_batch(pipeline, prompts, output_dir, sequence_number, aspect_ratio)
            sequence_number += len(prompts)
        else:
            print("No prompts entered. Please try again or type 'quit' to exit.")

if __name__ == "__main__":
    main()
