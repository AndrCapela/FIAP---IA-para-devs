import torch
from diffusers import StableDiffusionPipeline

pipeline = StableDiffusionPipeline.from_pretrained("CompVis/stable-diffusion-v1-4")

device = "cuda" if torch.cuda.is_available() else "cpu"
pipeline.to(device)

def generate_image(prompt):
    generated_image = pipeline(prompt).images[0]
    return generated_image

prompt = "a photo of an astronaut riding a horse on mars"
image = generate_image(prompt)
    
image.save("astronaut_rides_horse.png")
