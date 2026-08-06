import json

from support_triage_agent.pipeline import process_ticket


def main() -> None:
    print("LangGraph Support Ticket Triage")
    print("Type 'exit' to stop.\n")

    while True:
        ticket_text = input("Enter support ticket: ")

        if ticket_text.lower().strip() == "exit":
            print("Application stopped.")
            break

        try:
            result = process_ticket(ticket_text)

            print("\nFinal graph state:")
            print(json.dumps(result, indent=2))
            print()

        except ValueError as error:
            print(f"\nValidation error: {error}\n")


if __name__ == "__main__":
    main()