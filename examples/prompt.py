# EXAMPLE: Prompt
#
# Handling Prompt directly allows for very low-level control over the user input process.


from lunar_engine.exceptions import InterruptException
from lunar_engine.prompt import Prompt


with Prompt(">> ") as p:  # Prompt should be used within a "with" context
    try:
        for line in p:  # It can then be iterated through for lines of user input
            print(f"You inputted: {line}")

    # When Ctrl+C or similar is pressed to interrupt the program, this exception is raised.
    except InterruptException:
        print("Bye!")
