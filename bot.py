from discord.ext import commands
import discord
import random
import os
import asyncio
import re 
from pathlib import Path
from wiki_client import get_csrf_token,get_login_token,attempt_login,assert_logged_in, upload_file
from config import BOT_TOKEN, CHANNEL_ID, OWNER_ID, UPLOAD_CH_ID
from renderer import main as render_skin
from dotenv import load_dotenv
from PIL import Image
load_dotenv()

UPLOAD_TIMEOUT = 60 # seconds

"""
Notes: API Endpoint of this Miraheze wiki is: https://cvscraft.miraheze.org/w/api.php
       which combines both the server + scriptpath which can be found on the MediaWiki 
       API Helper page, which is found under the same link, but to view it in JSON format
       enter: https://cvscraft.miraheze.org/w/api.php?action=query&meta=siteinfo&format=json

       The Bot will use User's account on Miraheze to upload the images. A Bot Password has to
       additionally be created and saved by the human user. All sensitive information
       has been saved and protected locally by the user!

       Login Token can be obtained with the following link:
       https://cvscraft.miraheze.org/w/api.php?action=query&meta=tokens&type=login&format=json

       Wiki client functions have been implemented and imported from a separate file wiki_client.py.
       See wiki_client.py for details.
"""

# This lets us define the prefix for getting a command to run. The Intents part means we want the bot to
# use all features of discord!
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ------------------ Console -> Discord Relay -------------------------

console_task_started = False

async def console_relay(initial_channel_id: int):
    """
    Type in your terminal and the bot posts to Discord.
    Commands:
      /ch <channel_id>      switch target channel
      /quit                 shutdown bot
    """
    await bot.wait_until_ready()

    current_channel = bot.get_channel(initial_channel_id)
    if current_channel is None:
        print(f"[console_relay] Could not find channel {initial_channel_id}. Is the bot in that server?")
        return

    print("[console_relay] Ready.")
    print("  Type text to send it to Discord.")
    print("  Commands: /ch <channel_id>, /quit")

    while not bot.is_closed():
        # input() blocks -> run in a thread
        text = await asyncio.to_thread(input, ">> ")
        if text is None:
            continue

        text = text.strip()
        if not text:
            continue

        # local console commands
        if text.lower() in ("/quit", "/exit"):
            print("[console_relay] Shutting down bot...")
            try:
                await current_channel.send("Console requested shutdown.")
            except Exception:
                pass
            await bot.close()
            return

        if text.lower().startswith("/ch "):
            try:
                new_id = int(text.split(maxsplit=1)[1])
                new_channel = bot.get_channel(new_id)
                if new_channel is None:
                    print(f"[console_relay] Can't find channel {new_id}.")
                else:
                    current_channel = new_channel
                    print(f"[console_relay] Now sending to channel {new_id}.")
            except Exception as e:
                print(f"[console_relay] Bad /ch usage. Example: /ch 1234567890 ({e})")
            continue

        # default: send exactly what you typed
        await current_channel.send(text)
# ---------------------- End Console Relay -------------------------------


@bot.event
async def on_ready(): # When the bot is started, it will do the following: 
    print("Beep Boop. I am a clanker.")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Beep Boop. I am a clanker.")

    # Start console relay once (avoids restarting on reconnects)
    global console_task_started

    if not console_task_started:
        console_task_started = True
        asyncio.create_task(console_relay(CHANNEL_ID))

# --------------- Main Function -------------------------

# Discord command helper function for cleaning name string on input
def clean_part(s: str) -> str:
    """Sanitizes a filename part by replacing spaces with hyphens and removing special characters."""
    s = (s or "").strip()
    s = re.sub(r"\s+", "-", s)                 # spaces -> hyphens
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)      # remove complex chars
    return s.strip("._-")

# This is the function that uploads to the wiki
def wiki_upload(save_path: Path, wiki_filename: str):
    """Logs into the Miraheze wiki and uploads a file. Returns (result, warnings) from upload_file."""
    login_token, s = get_login_token()
    attempt_login(login_token, s)
    assert_logged_in(s)
    csrf_token = get_csrf_token(s)
    return upload_file(s, csrf_token, save_path, wiki_filename)


# This is the async discord function to upload an image. To see !uploadskin, see underneath.
@bot.command(help="You can upload an ONE image to the wiki with this command at a time. Feel free to use the additional fields to name it. Example: type_name_descriptor.png",brief="Upload image to wiki. Type '!help upload' for details.")
async def upload(ctx, type=None, name=None, descriptor=None):
    """
    Waits for the user to attach an image, saves it locally, and uploads it to the wiki.
    The filename is built from the optional type, name, and descriptor arguments.
    """
    if (ctx.channel.id == UPLOAD_CH_ID):
        await ctx.send(f"Beep boop... Waiting for file upload... Please send an image in your next message ({UPLOAD_TIMEOUT}).")
    else:
        await ctx.send(f"Please upload files from <#{UPLOAD_CH_ID}>!")
        return

    def check(m: discord.Message):
        return (
            m.author.id == ctx.author.id
            and m.channel.id == ctx.channel.id
            and len(m.attachments) > 0
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=UPLOAD_TIMEOUT)
    except asyncio.TimeoutError:
        await ctx.send("Too slow. Run `!upload` again when you’re ready.")
        return

    attachment = msg.attachments[0]

    # Only images
    if attachment.content_type and not attachment.content_type.startswith("image/"):
        await ctx.send("That’s not an image, stoopid. Give me the right thing.")
        return

    os.makedirs("uploads", exist_ok=True)

    ext = Path(attachment.filename).suffix  # ".png", ".jpg", etc.

    parts = [clean_part(type), clean_part(name), clean_part(descriptor)]
    parts = [p for p in parts if p]  # remove empty

    # Default name if no fields given
    if not parts:
        base = f"upload_{ctx.author.id}_{attachment.id}"
    else:
        base = "_".join(parts)

    wiki_filename = f"{base}{ext}"
    save_path = Path("uploads") / wiki_filename

    await attachment.save(save_path)
    await ctx.send(f"Beep boop... Saved your file as `{save_path}`. Uploading to wiki now...")

    # Wiki upload
    try:
        result, warnings = await asyncio.to_thread(wiki_upload, save_path, wiki_filename)
    except Exception as e:
        await ctx.send(f"Blehhhh. Something went wrong! <@{OWNER_ID}>, come fix this now!!!")
        raise Exception from e

    if result:
        await ctx.send(
            f"Success! `{wiki_filename}` uploaded.\n"
            f"Go check it out at https://cvscraft.miraheze.org/wiki/File:{wiki_filename}\n"
            f"If it didn't work, then <@{OWNER_ID}> deserves 3 spankings."
            )
    elif warnings is not None:
        await ctx.send(f"Upload failed! <@{OWNER_ID}>, come fix this!\n Warnings: {warnings}")
    else:
        await ctx.send(f"Upload failed because <@{OWNER_ID}> is bad at programming me!")

# Minecraft skin renderer
@bot.command(help="Works the exact some way as !upload, but this is specifically for uploading UNRENDERED minecraft skins (64x64 or 64x32)!")
async def uploadskin(ctx, type=None, name=None, descriptor=None):
    """
    Waits for the user to attach a raw Minecraft skin PNG (64x64 or 64x32), validates its dimensions,
    renders it using renderer.py, saves the rendered version to uploads/rendered_skins/, and uploads it to the wiki.
    """
    if (ctx.channel.id == UPLOAD_CH_ID):
        await ctx.send(f"Beep boop... Waiting for file upload... Please send an image in your next message ({UPLOAD_TIMEOUT}).")
    else:
        await ctx.send(f"Please upload files from <#{UPLOAD_CH_ID}>!")
        return

    def check(m: discord.Message):
    # Uploaded attachment is attachment from same user within same channel.
        return (
            m.author.id == ctx.author.id
            and m.channel.id == ctx.channel.id
            and len(m.attachments) > 0
        )

    # Timeout if upload time exceeds UPLOAD_TIMEOUT.
    try:
        msg = await bot.wait_for("message", check=check, timeout=UPLOAD_TIMEOUT)
    except asyncio.TimeoutError:
        await ctx.send("Too slow. Run `!upload` again when you’re ready.")
        return

    attachment = msg.attachments[0]

    # Images only
    if attachment.content_type and not attachment.content_type.startswith("image/"):
        await ctx.send("That’s not an image, stoopid. Give me the right thing.")
        return

    os.makedirs("uploads/raw_skins", exist_ok=True)

    ext = Path(attachment.filename).suffix  # ".png", ".jpg", etc.

    parts = [clean_part(type), clean_part(name), clean_part(descriptor)]
    parts = [p for p in parts if p]  # remove empty

    # Default name if no fields given
    if not parts:
        base = f"upload_{ctx.author.id}_{attachment.id}_raw"
    else:
        parts.append("raw")
        base = "_".join(parts)

    raw_filename = f"{base}{ext}"
    save_path = Path("uploads/raw_skins") / raw_filename

    await attachment.save(save_path)

    # Check image dimensions
    with Image.open(save_path) as img:
        if img.size not in [(64, 64), (64, 32)]:
            await ctx.send("The image size does not seem correct! It must be either 64x64 or 64x32 pixels!")
            return

    await ctx.send(f"Beep boop... Saved your file as `{save_path}`. Rendering skin now...")

    # Skin rendering and saving
    try:
        rendered_path = await render_skin(save_path, raw_filename)
    except Exception as e:
        await ctx.send(f"Skin rendering failed! <@{OWNER_ID}>, come fix this!")
        raise Exception from e

    
    rendered_file_name = rendered_path.name

    # Wiki upload
    try:
        result, warnings = await asyncio.to_thread(wiki_upload, rendered_path, rendered_file_name)
    except Exception as e:
        await ctx.send(f"Blehhhh. Something went wrong! <@{OWNER_ID}>, come fix this now!!!")
        raise Exception from e

    if result:
        await ctx.send(
            f"Success! `{rendered_file_name}` uploaded.\n"
            f"Go check it out at https://cvscraft.miraheze.org/wiki/File:{rendered_file_name}\n"
            f"If it didn't work, then <@{OWNER_ID}> deserves 3 spankings."
            )
    elif warnings is not None:
        await ctx.send(f"Upload failed! <@{OWNER_ID}>, come fix this!\n Warnings: {warnings}")
    else:
        await ctx.send(f"Upload failed because <@{OWNER_ID}> is bad at programming me!")

# ------------------ Fun Functions -------------------------

@bot.command(help="Kill the clanker.")
async def shutdown(ctx):
    if ctx.author.id != OWNER_ID:
        await ctx.send("Nope, beep boop. You are a wanker.")
        return

    await ctx.send("Shutting down... Later alligators.")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("Shutdown successful.")

    await bot.close()


@bot.command(help="Greet the clanker!") 
async def hello(ctx):           
    await ctx.send("Hello.")

@bot.command(help="Adds whole numbers.")
async def add(ctx, x="0", y="0"):
    result = int(x) + int(y)
    await ctx.send(f"{x} + {y} = {result}")

@bot.command(help="Tells you how the world sees you. Totally accurate.")
async def evaluateme(ctx):
    result = random.randint(0,3)
    if result == 1:
        await ctx.send("You are stupid.")
    elif result == 2:
        await ctx.send("Nobody likes you.")
    elif result == 3:
        await ctx.send("You are a clanker. Beep boop.")
    else:
        await ctx.send("You are the best!")

@bot.command(help="If you want to be impolite...")
async def evaluatemebitch(ctx):
    await ctx.send("No you are a bitch. Beep boop.")

@bot.command(help="When you are feeling lonely, ask for a smooch!")
async def smooch(ctx):
    await ctx.send("<:platonic_smooch:1322181401264783360>")

@bot.command(help="Tells you who you are if you exist.")
async def whoami(ctx):
    user = ctx.author.id
    match user:
        case 973176391929589780:
            await ctx.send("Hello, Sigma!")
        case 341323512096620555:
            await ctx.send("Hello, Incel.")
        case 550640453079531535:
            await ctx.send("Hello, Zee!")
        case _:
            await ctx.send(f"I don't know you yet... Blame <@{OWNER_ID}>!")





bot.run(BOT_TOKEN) # This allows the bot to run as a looping function.
