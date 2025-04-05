from dataclasses import dataclass
from typing import Callable

from autogen_core import (DefaultTopicId, MessageContext, RoutedAgent,
                          default_subscription, message_handler)


@dataclass
class Data:
    letters: int


@default_subscription
class Alice(RoutedAgent):
    def __init__(self, modify_val: Callable[[int], int]) -> None:
        super().__init__("Alice")
        self._mv = modify_val

    @message_handler
    async def handle_message(self, message: Data, data_ctx: MessageContext) -> None:
        val = self._mv(message.letters)
        print("-" * 80)
        print("Alice : ")
        print(message.letters)
        print(val)
        await self.publish_message(Data(letters=val), DefaultTopicId())  # type: ignore


@default_subscription
class Bob(RoutedAgent):

    def __init__(self, modify_val: Callable[[int], int]):
        super().__init__("Bob")
        self._mv = modify_val

    @message_handler
    async def handle_message(self, message: Data, _: MessageContext) -> None:

        val = self._mv(message.letters)
        print("-" * 80)
        print("Bob : ")
        print(message.letters)
        print(val)

        if message.letters > 0:
            await self.publish_message(Data(letters=val), DefaultTopicId())  # type: ignore


async def main():
    from autogen_core import AgentId, SingleThreadedAgentRuntime

    runtime = SingleThreadedAgentRuntime()

    alice_at = await Alice.register(runtime, "Alice", lambda: Alice(lambda x: x + 1))
    bob_at = await Bob.register(runtime, "Bob", lambda: Bob(lambda x: x - 10))

    # Start the runtime and send a direct message to the checker.
    runtime.start()
    await runtime.send_message(Data(10), AgentId(bob_at.type, "default"))
    await runtime.send_message(Data(10), AgentId(alice_at.type, "default"))
    await runtime.stop_when_idle()
