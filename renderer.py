import os
import asyncio
from minepi import Skin
from PIL import Image
from pathlib import Path

async def main(save_path: Path, file_name: str) -> Path:
    """
    Renders a raw Minecraft skin PNG using minepi and saves the result to uploads/rendered_skins/.
    The filename has '_raw' replaced with '_rendered'. Returns the Path of the rendered file.
    """
    raw_skin = Image.open(save_path)
    s = Skin(raw_skin=raw_skin)

    await s.render_skin(hr=28, vr=-8, vrll=20, vrrl=-20, vrla=-20, vrra=20,
                        ratio=24, aa=True, display_second_layer=True, display_hair=True)
    
    # Show the skin render locally on machine.
    # s.skin.show()  

    # Construct new path to save rendered skin
    os.makedirs("uploads/rendered_skins", exist_ok=True)
    new_file_name = file_name.replace("_raw", "_rendered")
    new_save_path = Path("uploads/rendered_skins") / new_file_name
    s.skin.save(new_save_path)
    return new_save_path

if __name__ == "__main__":
    asyncio.run(main())