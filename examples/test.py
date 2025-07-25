from lunar_engine.prompt import Prompt
from lunar_engine.exceptions import InterruptException
from prompt_toolkit.completion import FuzzyWordCompleter

prompt = Prompt(
    "> ",
    rprompt="Hi, test!",
    completer=FuzzyWordCompleter(
        ["hello", "world", "exit"],
        meta_dict={
            "hello": "hello world",
            "world": "world bye",
        },
    ),
)

with prompt:
    try:
        for input in prompt:
            if input == "exit":
                break  # should not raise
            print(input)
    except InterruptException:
        print("Goodbye!")
    else:
        print("passed")

assert not prompt

prompt._running = True  # pyright: ignore[reportPrivateUsage]

try:
    for input in prompt:
        print(input)
except InterruptException:
    print("Goodbye!")
except RuntimeError:
    print("passed")

assert not prompt
