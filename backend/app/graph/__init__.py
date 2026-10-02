"""Graph package for LangGraph state and workflow definition."""

from backend.app.graph.state import WeatherState


def create_weather_graph(*args, **kwargs):
    from backend.app.graph.workflow import create_weather_graph as _create_weather_graph
    return _create_weather_graph(*args, **kwargs)


__all__ = ["WeatherState", "create_weather_graph"]
