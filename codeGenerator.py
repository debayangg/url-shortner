import random
import asyncio
from database import set_setting, get_setting, cursor, get_url_codes
from utils import int_to_base62

BATCH_SIZE = 100000
LOW_WATERMARK = 1000
codes = []

code_generation_lock = asyncio.Lock()

async def generate_codes_if_needed():
    global codes
    async with code_generation_lock:
        current_max = get_setting('current_max')
        if current_max == 0:
            current_max += BATCH_SIZE
        start = 1
        end = current_max + 1

        codes = [int_to_base62(code) for code in range(start, end)]

        used_codes = get_url_codes()

        if used_codes is not None:
            for used_code in used_codes:
                codes.remove(used_code)

        if len(codes) < LOW_WATERMARK:
            current_max += BATCH_SIZE
            start = end
            end = current_max + 1
            codes.extend([int_to_base62(code) for code in range(start, end)])

        await set_setting('current_max', current_max)
        print(f"[generate_codes_if_needed] Finished generating codes. Updated current_max to {end - 1}")


async def get_code_for_new_url() -> str:
    """Return a random available code, removing it from the pool."""
    global codes
    async with code_generation_lock:
        print("[get_code_for_new_url] Getting code for new URL...")
        # Optionally, check if codes need to be generated:
        if len(codes)<LOW_WATERMARK:
            await generate_codes_if_needed()
    
        print("[get_code_for_new_url] Fetching a random code from codes...")
        code = codes[random.randint(0, len(codes) - 1)]
        codes.remove(code)
    
        if code:
            print(f"[get_code_for_new_url] Code {code} deleted from available codes.")
        else:
            print("[get_code_for_new_url] No code available! This should not happen if generation works properly.")
        return code
