"""Jarvis CLI - Main entry point for the Jarvis AI assistant."""

from agent.core import Jarvis


def main():
    """Start the Jarvis CLI."""
    jarvis = Jarvis()

    print("=" * 50)
    print("JARVIS ONLINE")
    print("Type 'exit' to shut down.")
    print("=" * 50)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "exit":
            print("Jarvis shutting down.")
            break

        if not user_input:
            continue

        try:
            response = jarvis.chat(user_input)
            print(f"\nJarvis: {response}")

        except Exception as error:
            print(f"\nError: {error}")


if __name__ == "__main__":
    main()
