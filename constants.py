from copy import deepcopy

styles = {
    "pixar": {
        "start": "front-facing pixar animation of ",
        "end": ", animation render by Pixar and Disney, au naturel, PS2, PS1, hyper detailed, digital art, trending in artstation, cinematic lighting, studio quality, smooth render, unreal engine 5 rendered, octane rendered.",
    },
    "impressionist": {
        "start": "front-facing impressionist painting of ",
        "end": ", art style by claude monet, bright colored surroundings, colorful and flat, concept art, highly detailed, intricate details, blotchy application, visible brush strokes, clear application, masterpiece, intricate",
    },
    "pop": {
        "start": "((pop-art painting)) of ",
        "end": ", art style by andy warhol and roy lichtenstein, colorful flat, silkscreen, pixabay, pop art, cinematic view, vaporwave",
    },
    "pencil": {
        "start": "pencil sketch of ",
        "end": ", a pencil sketch by Melissa Benson, trending on deviantart, fine art, pencil sketch, art on instagram, charcoal drawing",
    },
    "bw_photo": {
        "start": "a realistic black and white photo ",
        "end": ", a black and white photo by Ettore Tit and George Bogart and Claude Rogers, deviantart, flickr, massurrealism, movie still, american romanticism, criterion collection, filmic",
    },
    "claymation": {
        "start": "a claymation of ",
        "end": ", claymation by John E. Berninger and Nick Park and Wallace and Gromit, trending on zbrush central, regionalism, reimagined by industrial light and magic, cgsociety, criterion collection, colorized, adafruit",
    },
    "anime": {
        "start": "a realistic anime drawing of ",
        "end": ", an anime drawing by Rei Kamoi, trending on cg society, dau-al-set, anime, official art, toonami",
    },
    "south_park": {
        "start": "a south park cartoon drawing of ",
        "end": ", concept art by Michelangelo, reddit, rayonism, featured on deviantart, antipodeans, official art, concept art, colorized",
    },
    "spiderverse": {
        "start": "hand drawn colorful comic book panel of ",
        "end": ", set against handpainted bright cool pink background of abstract watercolor bright colors, panfuturism, a hand drawn comic book panel by Jerry Eisenberg and Alberto Mielgo, trending on cgsociety, harlem renaissance, trending on polycount, official comic art, reimagined by industrial light and magic",
    },
    "rickandmorty": {
        "start": "a cartoon drawing of ",
        "end": ", drawing by Rick and Morty, trending on tumblr, Artstation, neoplasticism, altermodern, official art, bioluminescence, furaffinity, colorized",
    },
    "marvel": {
        "start": "a marvel cinematic movie poster of ",
        "end": ", a poster by Zack Snyder, behance, assemblage, marvel comics, cinematic, imax, reimagined by industrial light and magic, soft light, movie poster",
    },
    "graffiti": {
        "start": "graffiti spray painting of ",
        "end": ", explosion of colors, graffiti spray art by Mac Conner and Keith Haring and Banksy, trending on deviantart, lyco art, airbrush art, apocalypse art",
    },
    "minecraft": {
        "start": "minecraft video game poster of ",
        "end": ", computer graphics poster by Minecraft, reddit, sots art, blocky, pixelated, rendered in cinema4d, prerendered graphics",
    },
    "2d": {
        "start": "2d drawing of ",
        "end": ", a screenshot by Hanna-Barbera, featured on deviantart, primitivism, official art, 2d sketched game art, flat, concept art",
    },
    "ghibli": {
        "start": "studio ghibli movie still of ",
        "end": ", a screenshot by Studio Ghibli, cgsociety, official art, flat, pixiv, cloisonnism, anime aesthetic, anime",
    },
    "magritte": {
        "start": "zoomed-out portrait of ",
        "end": ", portrait by rene magritte and laurie greasley, etching by gustave dore, bright colors, colorful flat surreal, ethereal, intricate, sharp focus, illustration, highly detailed, digital painting, concept art, masterpiece",
    },
    "magic": {
        "start": "portrait of ",
        "end": ", highly detailed, fantasy concept art, intricate details and textures, magical, olorful, art by wlop, greg rutkowski, charlie bowater, magali villeneuve, alphonse mucha, surreal.",
    },
    "stick_figure": {"full_prompt": "a stick figure drawing", "no_prompt": True},
}

random_animal_styles = ["mooing cow", "stupid looking llama"]
extra_boy_styles = random_animal_styles + [
    "ukj person as the three blind mice from the movie shrek",
    "ukj person as a princess from a disney movie",
]
extra_girl_styles = random_animal_styles + []

girl_styles = deepcopy(styles)
for style in extra_girl_styles:
    girl_styles[style] = {
        "full_prompt": styles["pixar"]["start"] + style + styles["pixar"]["end"],
        "no_prompt": True,
    }

boy_styles = deepcopy(styles)
for style in extra_boy_styles:
    boy_styles[style] = {
        "full_prompt": styles["pixar"]["start"] + style + styles["pixar"]["end"],
        "no_prompt": True,
    }


default_negative = "zoomed in, words, distortions, nude, naked, back, multiple crowns, multiple faces, extra characters, closed eyes, even eyes, wild eyes, deformed face, words, blurred background, nude, naked, cropped, unreal, animate, framed, disfigured, angled, mutated, rotated"
