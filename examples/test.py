from lunar_engine.prompt import Prompt
from lunar_engine.exceptions import LunarEngineInterrupt
from prompt_toolkit.completion import FuzzyWordCompleter

prompt = Prompt(
    "> ",
    rprompt="Hi, test!",
    completer=FuzzyWordCompleter(["hello", "world"]),
)

with prompt:
    try:
        for input in prompt:
            if input == "exit":
                # should not raise
                break
            print(input)
    except LunarEngineInterrupt:
        print("Goodbye!")

assert not prompt

prompt._running = True  # pyright: ignore[reportPrivateUsage]

try:
    for input in prompt:
        print(input)
except LunarEngineInterrupt:
    print("Goodbye!")
except RuntimeError:
    print("passed")

assert not prompt
