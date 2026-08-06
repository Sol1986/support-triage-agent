from dataclasses import asdict, dataclass

# This class represents the state of a support ticket, including its text, category, priority, summary, draft response, and whether it requires human review. It provides a method to convert the state to a dictionary format for easy serialization or further processing.
@dataclass
class TicketState:
    '''
    TicketState represents everything the workflow currently knows about a ticket.
    '''
    ticket_text: str
    category: str = ""
    priority: str = ""
    summary: str = ""
    draft_response: str = ""
    requires_human_review: bool = False

    def to_dict(self) -> dict:
        return asdict(self)