import asyncio


async def async_map(func, iterable):
    tasks = [asyncio.create_task(func(item)) for item in iterable]
    return await asyncio.gather(*tasks)
