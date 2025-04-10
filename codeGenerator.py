import random
import asyncio
import time
from database import set_setting, get_setting, get_url_codes
from utils import int_to_base62

# Configuration Constants
BATCH_SIZE = 100_000
LOW_WATERMARK = 1_000
HIGH_WATERMARK = 10_000
GENERATION_COOLDOWN = 5  # Seconds to prevent rapid regeneration
CODE_CACHE_SIZE = 1_000  # Not directly used but kept for possible future enhancement

# Global State
available_codes = []
code_generation_lock = asyncio.Lock()
last_generation_time = 0

async def generate_codes_setup():
    global available_codes
    global code_generation_lock
    async with code_generation_lock:
        current_max = await get_setting('current_max')
        start = 1
        end = current_max + 1
        used_url_codes = await get_url_codes()
        used_codes = set(used_url_codes if used_url_codes else [])
        new_codes = {
            int_to_base62(code_int)
            for code_int in range(start, end)
            if int_to_base62(code_int) not in used_codes
        }
        available_codes.extend(new_codes)

async def generate_codes_if_needed():
    """Generate more short URL codes if available pool is low."""
    global available_codes, last_generation_time

    if len(available_codes) > LOW_WATERMARK:
        return

    async with code_generation_lock:
        if len(available_codes) > LOW_WATERMARK:
            return

        current_time = time.time()
        if current_time - last_generation_time < GENERATION_COOLDOWN:
            return

        last_generation_time = current_time
        print(f"Generating new codes. Current available: {len(available_codes)}")

        # Await the current maximum setting properly
        current_max = await get_setting('current_max')
        if not current_max:
            current_max = BATCH_SIZE

        # Define new range for generation
        start = current_max + 1
        end = start + BATCH_SIZE

        # Fetch used codes from database
        used_codes = set(await get_url_codes() or [])

        # Generate unique codes
        new_codes = {
            int_to_base62(code_int)
            for code_int in range(start, end)
            if int_to_base62(code_int) not in used_codes
        }

        available_codes.extend(new_codes)

        # Update the current max value in DB
        await set_setting('current_max', end - 1)
        print(f"Generated {len(new_codes)} new codes. Available now: {len(available_codes)}")


async def prefill_code_cache():
    """Prefill the available codes cache during app startup."""
    global available_codes

    current_max = await get_setting('current_max')
    if not current_max:
        current_max = BATCH_SIZE
        await set_setting('current_max', current_max)

    used_codes = set(await get_url_codes() or [])

    # Fill available codes from 1 to current_max
    available_codes.extend(
        int_to_base62(code_int)
        for code_int in range(1, current_max + 1)
        if int_to_base62(code_int) not in used_codes
    )

    print(f"Initial code cache filled with {len(available_codes)} codes")

    # If codes are too few, trigger generation
    if len(available_codes) < HIGH_WATERMARK:
        await generate_codes_if_needed()


async def get_code_for_new_url() -> str:
    """Fetch a fresh code for a new URL."""
    global available_codes

    # Refill if empty
    if not available_codes:
        await prefill_code_cache()

    if not available_codes:
        print("ERROR: No codes available even after attempting to fill!")
        return None

    # Pop a random code
    code = available_codes.pop(random.randrange(len(available_codes)))

    # Refill in background if low
    if len(available_codes) < LOW_WATERMARK:
        asyncio.create_task(generate_codes_if_needed())

    return code
