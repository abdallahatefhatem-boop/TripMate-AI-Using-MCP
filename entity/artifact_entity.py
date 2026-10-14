from dataclasses import dataclass


@dataclass
class FlightArtifact:
    """
    Artifact representing retrieved flight data.
    """

    flight_data: str
    status: str = "success"


@dataclass
class HotelArtifact:
    """
    Artifact representing retrieved hotel options.
    """

    hotel_data: str
    status: str = "success"


@dataclass
class ItineraryArtifact:
    """
    Artifact representing the generated itinerary.
    """

    itinerary_text: str
    status: str = "success"


@dataclass
class TravelAgentOutput:
    """
    Final output artifact produced by the travel multi-agent graph.
    """

    thread_id: str
    answer: str
    flight_results: str = ""
    hotel_results: str = ""
    itinerary: str = ""
    llm_calls: int = 0
