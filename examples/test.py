from lunar_engine.prompt import Prompt
from lunar_engine.exceptions import LunarEngineInterrupt
from prompt_toolkit.completion import FuzzyWordCompleter

prompt = Prompt(
    "> ",
    rprompt="Hi, test!",
    completer=FuzzyWordCompleter(["hello", "world"]),
)

try:
    prompt.run_loop(callback=lambda x: print(x) if x != "" else None)
except LunarEngineInterrupt:
    print("Goodbye!")
