



class SetRedis:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "redisKey": ("STRING", {"default": ""}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "notify"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "utils"

    def notify(self, text, unique_id=None, redisKey=None):
        #设置 更新redis

        return {"ui": {"text": text}, "result": (text,)}


NODE_CLASS_MAPPINGS = {
    "SetRedis|clh": SetRedis,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SetRedis|clh": "SetRedis Text ",
}
