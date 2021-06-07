# RT - Worker

from importlib import import_module
from traceback import format_exc
from websockets import connect
from ujson import loads, dumps
from random import randint
from time import time
import logging
import asyncio

from .converter import add_converter
from .errors import NotConnected, NotFound


def if_connected(function):
    async def _function(self, *args, **kwargs):
        if self.ws:
            await function(self, *args, **kwargs)
        else:
            raise NotConnected("まだWebSocketに接続できていないので処理を実行できません。")
    return _function


class Worker:
    def __init__(self, prefixes, loop=None, logging_level=logging.DEBUG,
                 print_extension_name=False, ignore_me=True):
        self.print_extension_name = print_extension_name
        self.ignore_me = ignore_me
        self.queue = asyncio.Queue()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.events = {}
        self.commands = {}
        self.extensions = {}
        self.cogs = {}
        self.ws = None
        self._request = asyncio.Event()
        self._event = asyncio.Event()
        self._ready = asyncio.Event()

        # プリフィックスを設定する。
        if isinstance(prefixes, list):
            self.prefixes = tuple(prefixes)
        elif isinstance(prefixes, tuple):
            self.prefixes = prefixes
        elif isinstance(prefixes, str):
            self.prefixes = (prefixes,)
        else:
            raise TypeError("プリフィックスはタプルかリストか文字列にする必要があります。")

        # ログ出力の設定をする。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Worker")

        # コマンドフレームワークのコマンドを走らせるためにon_messageイベントを登録しておく。
        self.add_event(self.on_message, "message_create")

        super().__init__()

    def run(self):
        self.loop.run_until_complete(self.worker())

    async def close(self):
        await self.ws.close()

    def make_session_id(self) -> str:
        base = str(time())
        for _ in range(5):
            base += str(range(0, 9))
        return base

    async def worker(self):
        self.logger.info("Connecting to websocket...")
        # 親のDiscordからのイベントを受け取るmain.pyと通信をする。
        # イベントを受け取ったらそのイベントでの通信を開始する。
        ws = await connect("ws://localhost:3000")
        self.ws = ws
        self._ready.set()
        self.logger.info("Start worker.")
        while True:
            # リクエストが終わるまで待つ。
            await self._request.wait()
            # リクエストができないようにする。
            self._event.clear()
            try:
                data = loads(await asyncio.wait_for(ws.recv(), timeout=0.01))
            except asyncio.TimeoutError:
                pass
            else:
                # イベント呼び出しならそれ専用のことをする。
                callback_data = {
                    "type": "ok",
                    "data": {}
                }
                try:
                    if (data["data"]["type"] in self.events
                            and data["type"] == "start"):
                        # 登録されているイベントを呼び出すものならそのイベントを呼び出す。
                        new_data = data["data"]
                        new_data["callback_template"] = callback_data
                        # guildなどの取得できるのなら取得しておく。
                        guild_id = new_data.get("guild_id")
                        if guild_id:
                            new_data["guild"] = await self.discord(
                                "get_guild", guild_id, wait=True)
                        channel_id = new_data.get("channel_id")
                        if channel_id:
                            new_data["channel"] = await self.discord(
                                "get_channel", channel_id, wait=True)
                        # イベントの実行をする。
                        for coro in self.events[data["type"]]:
                            asyncio.create_task(coro(ws, new_data))
                except Exception:
                    error = format_exc()
                    callback_data["type"] = "error"
                    callback_data["data"] = error
                    print("\nException in worker:" + error)
                # コールバックを返却する。
                await ws.send(dumps(callback_data))
            # リクエストができるようにする。
            self._event.set()

    def event(self, event_name=None):
        # イベント登録用のデコレ―タ。
        def _event(coro):
            self.add_event(coro, event_name)
        return _event

    def add_event(self, coro, event_name=None):
        # イベント登録用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(coro)
        self.logger.info(f"Added event {event_name}.")

    def remove_event(self, coro, event_name=None):
        # イベント削除用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name in self.events:
            i = -1
            for check_coro in self.events[event_name]:
                i += 1
                if check_coro == coro:
                    del self.events[event_name][i]
                    self.logger.info(f"Removed event {event_name}.")
                    return
        raise ValueError("そのコルーチンはイベントとして登録されていません。")

    @if_connected
    async def discord(self, event_type: str, *args, **kwargs):
        # Discordに何かリクエストしてもらう。
        await self._event.wait()
        self._request.clear()
        data = {
            "type": "discord",
            "data": {
                "args": args,
                "kwargs": kwargs
            }
        }
        if "wait" in kwargs:
            wait = kwargs["wait"]
            data["data"]["wait"] = wait
            del kwargs["wait"]
        await self.ws.send(dumps(data))
        data = loads(await self.ws.recv())
        self._request.set()
        if data["type"] == "error":
            raise Exception("\n", data["data"])
        return data

    async def wait_until_ready(self):
        await self._ready.wait()

    def command(self, command_name=None):
        # コマンド登録用のデコレ―タ。
        def _command(coro):
            # converter.pyにあるやつでコンバーターをコマンドのコルーチンに追加する。
            self.add_command(coro, command_name)
        return _command

    def add_command(self, coro, command_name=None):
        # コマンド登録用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するコマンドはコルーチンである必要があります。")
        command_name = command_name if command_name else coro.__name__
        self.commands[command_name] = coro
        self.logger.info(f"Added command {command_name}")

    def remove_command(self, command_name):
        # コマンド削除用の関数。
        if asyncio.iscoroutine(command_name):
            command_name = command_name.__name__
        del self.commands[command_name]
        self.logger.info(f"Removed command {command_name}")

    async def process_commands(self, ws, data):
        # コマンドを走らせる。
        if data["content"].startswith(self.prefixes):
            for command_name in self.commands:
                for prefix in self.prefixes:
                    start = prefix + command_name
                    if data["content"].startswith(start):
                        # コマンドの準備をする。
                        # 引数を取り出してからコンバーターをコマンドのプログラムにつけて実行する。
                        args = self.parse_args(
                            data["content"].replace(start, ""))
                        cmd = add_converter(
                            self.commands[command_name], ws, data, None, *args)
                        asyncio.create_task(cmd)
                        return command_name

    async def on_message(self, ws, data):
        await self.process_commands(ws, data)

    def parse_args(self, content: str) -> list:
        # 引数を取り出す。
        args, raw_arg = [], ""
        now_split_char = False
        for c in content:
            if c in (" ", "　", "\t", "\n") and not now_split_char:
                if raw_arg:
                    args.append(raw_arg)
                    raw_arg = ""
            elif c in ("'", '"'):
                now_split_char = False if now_split_char else True
            else:
                raw_arg += c
        if raw_arg:
            args.append(raw_arg)
        return args

    def add_cog(self, cog_class):
        # コグを追加する。
        name = cog_class.__class__.__name__
        self.cogs[name] = cog_class
        self.logger.info("Added cog " + name)

    def remove_cog(self, name):
        # コグを削除する。
        # この時コグで登録されたコマンドを削除しておく。
        if name in self.cogs:
            for command_name in self.commands:
                cog_name = getattr(
                    "__cog_name", "ThisIsNotCogYeahAndImTasuren")
                if cog_name == name:
                    self.remove_command(command_name)
            cog_unload = getattr(self.cogs[name], "cog_unload", None)
            if cog_unload:
                cog_unload()
            del self.cogs[name]
            self.logger.info("Removed cog " + name)
        else:
            raise NotFound(f"{name}というコグが見つからないためコグの削除ができません。")

    def load_extension(self, path):
        # エクステンションのロードをする。
        path = path.replace("/", ".").replace(".py", "")
        self.extensions[path] = import_module(path)
        return_data = self.extensions[path].setup(self)
        text = "Loaded extension " + path
        if self.print_extension_name:
            if isinstance(self.print_extension_name, str):
                text = self.print_extension_name + path
            print(text)
        self.logger.info(text)
        return return_data

    def unload_extension(self, path):
        # エクステンションのアンロードをする。
        # アンロードする前にコグを外しておく。
        if path in self.extensions:
            for key in self.cogs:
                if self.cogs[key].get_filename() == path:
                    self.remove_cog(key)
            del self.extensions[path]
            self.logger.info("Unloaded extension " + path)
        else:
            raise NotFound(f"{path}のエクステンションが見つからないためアンロードすることができません。")

    def reload_extension(self, path):
        # エクステンションをリロードする。
        self.unload_extension(path)
        self.load_extension(path)
        self.logger.info("Reloaded extension " + path)

    def reload_all_extensions(self):
        # 全てのエクステンションをリロードする。
        for path in [path for path in self.extensions]:
            # 内包表記でわざわざリストにしているのは反復中にself.extensionsに変更が入るから。
            self.unload_extension(path)
            self.load_extension(path)
        self.logger.info("Reloaded all extensions")


if __name__ == "__main__":
    worker = Worker()
    worker.run()
