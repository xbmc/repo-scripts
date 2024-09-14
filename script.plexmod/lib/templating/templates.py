# coding=utf-8

# unused right now
TEMPLATES = {
    "episodes": {
        "controls": {
            "buttons": [
                {
                    "visible": "String.IsEmpty(Window.Property(use_bg_fallback))",
                    "posx": 0,
                    "posy": 0,
                    "width": 1920,
                    "height": 1080,
                    "texture": "$INFO[Window.Property(background_static)]"
                },
            ]
        }
    }
}
