"""Shared, bounded resources and safe contexts for independently running commands."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial
from weakref import WeakKeyDictionary

import aiohttp
from discord.ext import commands


_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pippo-media")
_gates = WeakKeyDictionary()


def _discard_media(result):
    """Close attachments whose waiting command was cancelled before delivery."""
    import discord
    from PIL import Image
    if isinstance(result, (discord.File, Image.Image)):
        result.close()
    elif isinstance(result, (tuple, list)):
        for value in result:
            _discard_media(value)


async def run_blocking(function, /, *args, **kwargs):
    """Bound active and queued work even when waiting commands are cancelled."""
    loop = asyncio.get_running_loop()
    gate = _gates.setdefault(loop, asyncio.Semaphore(4))
    await gate.acquire()
    try:
        future = loop.run_in_executor(_workers, partial(function, *args, **kwargs))
    except BaseException:
        gate.release()
        raise
    cancelled = discarded = False

    def discard_if_cancelled(done):
        nonlocal discarded
        if cancelled and not discarded:
            discarded = True
            try:
                result = done.result()
            except BaseException:
                return
            _discard_media(result)

    def completed(done):
        gate.release()
        discard_if_cancelled(done)

    future.add_done_callback(completed)
    try:
        # A Python thread cannot be stopped by cancelling its waiting coroutine.
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        cancelled = True
        if future.done():
            discard_if_cancelled(future)
        raise


@asynccontextmanager
async def http_session(bot, *, timeout=None):
    """Borrow the bot's pooled HTTP client; standalone cogs retain a safe fallback."""
    session = getattr(bot, "http_session", None)
    if session is not None and not session.closed:
        yield session
    else:
        async with aiohttp.ClientSession(timeout=timeout or aiohttp.ClientTimeout(total=10)) as session:
            yield session


class PippoContext(commands.Context):
    async def send(self, content=None, **kwargs):
        registry = getattr(self.bot, "view_sessions", None)
        view = kwargs.get("view")
        if registry is not None and view is not None:
            try:
                registry.reserve(self.author.id, view)
            except SessionBusy:
                for file in [kwargs.get("file"), *(kwargs.get("files") or [])]:
                    if file is not None:
                        file.close()
                raise
        try:
            return await super().send(content, **kwargs)
        except BaseException:
            if registry is not None and view is not None:
                registry.release(view)
                view.stop()
            raise

    async def reply(self, content=None, **kwargs):
        if self.interaction is not None:
            return await super().reply(content, **kwargs)
        # Deleting a user's prefix message must not make the command fail.
        kwargs.setdefault("reference", self.message.to_reference(fail_if_not_exists=False))
        return await self.send(content, **kwargs)


class SessionBusy(commands.CheckFailure):
    pass


class TextSessions:
    """Only chat-guessing games share a channel resource; button boards are independent."""
    COMMANDS = {"bollywood", "hollywood", "plotster", "poster", "onewordstory"}

    def __init__(self, capacity=100, user_limit=2):
        self.capacity = capacity
        self.user_limit = user_limit
        self.channels = {}

    def acquire(self, ctx):
        if ctx.command.name not in self.COMMANDS:
            return
        channel = ctx.channel.id
        if channel in self.channels:
            raise SessionBusy("A chat-guessing game is already running here. Finish it or use another channel or thread.")
        if len(self.channels) >= self.capacity:
            raise SessionBusy("Pippo's game rooms are busy. Please try again shortly.")
        if sum(owner == ctx.author.id for _, owner in self.channels.values()) >= self.user_limit:
            raise SessionBusy("You already have two chat games running. Finish one before starting another.")
        self.channels[channel] = (ctx, ctx.author.id)

    def release(self, ctx):
        entry = self.channels.get(ctx.channel.id)
        if entry is not None and entry[0] is ctx:
            del self.channels[ctx.channel.id]


async def read_limited(response, limit):
    """Read through EOF, rejecting oversized declared or streamed bodies."""
    if response.content_length is not None and response.content_length > limit:
        raise ValueError("Response exceeds the download limit")
    body = bytearray()
    async for chunk in response.content.iter_chunked(64 * 1024):
        if len(body) + len(chunk) > limit:
            raise ValueError("Response exceeds the download limit")
        body.extend(chunk)
    return bytes(body)


class PrefixCache:
    """Bounded TTL cache that coalesces simultaneous reads for the same guild."""
    def __init__(self, ttl=60, capacity=4096):
        from collections import OrderedDict
        self.values = OrderedDict()
        self.pending = {}
        self.ttl = ttl
        self.capacity = capacity

    async def get(self, key, loader):
        loop = asyncio.get_running_loop()
        value = self.values.get(key)
        if value is not None and value[0] > loop.time():
            self.values.move_to_end(key)
            return value[1]
        if key not in self.pending:
            async def load():
                try:
                    result = await loader()
                    # Invalidation drops the pending entry; don't restore stale data.
                    if self.pending.get(key) is asyncio.current_task():
                        self.values[key] = (loop.time() + self.ttl, result)
                        self.values.move_to_end(key)
                        while len(self.values) > self.capacity:
                            self.values.popitem(last=False)
                    return result
                finally:
                    if self.pending.get(key) is asyncio.current_task():
                        self.pending.pop(key, None)
            self.pending[key] = asyncio.create_task(load())
            self.pending[key].add_done_callback(lambda task: None if task.cancelled() else task.exception())
        return await asyncio.shield(self.pending[key])

    def invalidate(self, key):
        self.values.pop(key, None)
        self.pending.pop(key, None)


class ViewSessions:
    """Cap live component menus without sharing boards between players."""
    def __init__(self, capacity=500, user_limit=8):
        self.capacity = capacity
        self.user_limit = user_limit
        self.entries = {}

    def reserve(self, owner, view):
        self.entries = {key: value for key, value in self.entries.items() if not value[1].is_finished()}
        key = id(view)
        if key in self.entries:
            return
        if len(self.entries) >= self.capacity:
            raise SessionBusy("Pippo has too many active menus. Please try again shortly.")
        if sum(uid == owner for uid, _ in self.entries.values()) >= self.user_limit:
            raise SessionBusy("You have eight active menus. Finish one or let it expire before opening another.")
        self.entries[key] = (owner, view)

    def release(self, view):
        self.entries.pop(id(view), None)


async def react(message, emoji):
    """A deleted guess or missing reaction permission must not abort a game."""
    import discord
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        pass
