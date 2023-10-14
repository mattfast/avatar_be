import json
import numpy as np
import torch
import triton_python_backend_utils as pb_utils

from diffusers import StableDiffusionImg2ImgPipeline
from diffusers import DDIMScheduler
from transformers import CLIPTokenizer
from io import BytesIO
import base64
from PIL import Image


def decode_image(img):
    buff = BytesIO(base64.b64decode(img.encode("utf8")))
    image = Image.open(buff)
    return image


def encode_images(images):
    encoded_images = []
    for image in images:
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue())
        encoded_images.append(img_str.decode("utf8"))

    return encoded_images


def prep_image(im: Image) -> Image:
    size = im.size
    if size[0] > size[1]:
        mult = 512 / im.size[1]
        side = mult * im.size[0]
        return im.resize(((int(side), 512)))

    mult = 512 / im.size[0]
    side = mult * im.size[1]
    return im.resize((512, int(side)))


class TritonPythonModel:

    def initialize(self, args):

        self.model_dir = args['model_repository']
        self.model_ver = args['model_version']
        model_id = f'{self.model_dir}/{self.model_ver}/outputs/1000'

        tokenizer = CLIPTokenizer.from_pretrained(
            model_id,
            subfolder="tokenizer",
            use_fast=False,
        )
        self.pipe = StableDiffusionImg2ImgPipeline.from_pretrained(model_id, tokenizer=tokenizer,
                                                                   torch_dtype=torch.float16, use_safetensors=True).to(
            "cuda")

    def execute(self, requests):

        logger = pb_utils.Logger
        responses = []
        for request in requests:
            prompt = pb_utils.get_input_tensor_by_name(request, "prompt").as_numpy().item().decode("utf-8")
            negative_prompt = pb_utils.get_input_tensor_by_name(request, "negative_prompt")
            image = pb_utils.get_input_tensor_by_name(request, "image").as_numpy().item().decode("utf-8")
            gen_args = pb_utils.get_input_tensor_by_name(request, "gen_args")

            image = prep_image(decode_image(image))

            input_args = dict(prompt=prompt, image=image)

            if negative_prompt:
                input_args["negative_prompt"] = negative_prompt.as_numpy().item().decode("utf-8")

            if gen_args:
                gen_args = json.loads(gen_args.as_numpy().item().decode("utf-8"))
                input_args.update(gen_args)

            images = self.pipe(**input_args).images
            encoded_images = encode_images(images)

            responses.append(pb_utils.InferenceResponse(
                [pb_utils.Tensor("generated_image", np.array(encoded_images).astype(object))]))

        return responses