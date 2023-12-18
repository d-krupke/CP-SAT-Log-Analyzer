import re
import typing
import plotly.graph_objects as go
from .log_block import LogBlock


def parse_time(time: str):
    # seconds
    if re.match(r"\d+\.\d+s", time):
        return float(time[:-1])
    # minutes
    if re.match(r"\d+\.\d+m", time):
        return float(time[:-1]) * 60
    # ms
    if re.match(r"\d+\.\d+ms", time):
        return float(time[:-2]) / 1000
    raise ValueError(f"Unknown time format: {time}")


def _get_bound(match: re.Match):
    """
    Extract the bound from a match object.
    Needs to differ between upper and lower bound.
    """
    if "next_lb" not in match.groupdict():
        return match.group("obj")
    next_lb = match.group("next_lb")
    next_ub = match.group("next_ub")
    if next_lb is None or next_ub is None:
        return match.group("obj")
    bound_lb, bound_ub = int(next_lb), int(next_ub)
    obj = float(match.group("obj"))
    if obj < bound_lb:
        return bound_ub  # upper bound
    else:
        return bound_lb  # lower bound


class BoundEvent:
    def __init__(
        self, time: float, obj: typing.Optional[int], bound: int, msg: str
    ) -> None:
        self.bound = bound
        self.msg = msg
        self.time = time
        self.obj = obj

    def is_upper_bound(self):
        if self.obj is None:
            return None  # unknown
        return self.bound > self.obj

    def is_lower_bound(self):
        if self.obj is None:
            return None  # unknown
        return self.bound < self.obj

    @staticmethod
    def parse(line: str) -> typing.Optional["BoundEvent"]:
        # bound events start with #Bound
        # TODO: Allow more than just seconds
        bound_pattern = r"#Bound\s+(?P<time>\d+\.\d+s)\s+(best:(?P<obj>-?\d+|inf))\s+next:\[(?P<next_lb>-?\d+),(?P<next_ub>-?\d+)\]\s+(?P<msg>.*)"
        m = re.match(bound_pattern, line)
        if m:
            obj = int(m.group("obj")) if m.group("obj") != "inf" else None
            return BoundEvent(
                time=parse_time(m.group("time")),
                obj=obj,
                bound=_get_bound(m),
                msg=m.group("msg"),
            )
        else:
            return None


class ObjEvent:
    def __init__(self, time: float, obj: int, bound: int, msg: str) -> None:
        self.time = time
        self.obj = obj
        self.msg = msg
        self.bound = bound

    @staticmethod
    def parse(line: str) -> typing.Optional["ObjEvent"]:
        # obj events start with # and a number
        # TODO: Allow more than just seconds
        obj_pattern = r"#(-?\d+)\s+(?P<time>\d+\.\d+s)\s+(best:(?P<obj>-?\d+))\s+next:\[((?P<next_lb>-?\d+),(?P<next_ub>-?\d+))?\]\s+(?P<msg>.*)"
        m = re.match(obj_pattern, line)
        if m:
            return ObjEvent(
                time=parse_time(m.group("time")),
                obj=int(m.group("obj")),
                bound=_get_bound(m),
                msg=m.group("msg"),
            )
        else:
            return None


class SearchProgressBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        lines = [l.strip() for l in lines if l.strip()]
        if not lines:
            raise ValueError("No lines to parse")
        if not lines[0].startswith("Starting search"):
            raise ValueError(f"Not a valid progress log. First line: {lines[0]}")
        self.lines = lines

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().startswith("Starting search")

    def _parse_events(self) -> typing.List[typing.Union[BoundEvent, ObjEvent]]:
        """
        Parse the log file into a list of BoundEvent and ObjEvent.
        """
        events = []
        for line in self.lines:
            obj_event = ObjEvent.parse(line)
            if obj_event:
                events.append(obj_event)
                continue
            bound_event = BoundEvent.parse(line)
            if bound_event:
                events.append(bound_event)
                continue
        return events

    def get_presolve_time(self) -> float:
        # first line looks like this "Starting search at 16.74s with 24 workers."
        m = re.match(
            r"Starting search at (?P<time>\d+\.\d+s) with \d+ workers.", self.lines[0]
        )
        if m:
            return parse_time(m.group("time"))
        raise ValueError(f"Could not parse presolve time from '{self.lines[0]}'")

    def get_title(self) -> str:
        return "Search progress:"

    def get_help(self) -> str | None:
        return """
        The search progress log is probably the most important part of the log.
        Here you can see, how the solver progresses over time and were it struggles
        the most. Are the upper or the lower bounds the problem? Does the solver quickly find a near optimal solution, but then struggles to close a small gap?

        You probably have to zoom into the plot to see the details as the first
        values can be very large. Check out which part converges the fastest.
        """

    def as_plotly(self) -> go.Figure:
        """
        Plot the progress of the solver.
        """
        events = self._parse_events()
        obj_events = [e for e in events if isinstance(e, ObjEvent)]
        bound_events = [e for e in events if isinstance(e, BoundEvent)]
        fig = go.Figure()
        if not obj_events and not bound_events:
            return fig
        max_time = max([e.time for e in bound_events + obj_events])

        # make sure that both bounds and objs have a value at max_time
        if obj_events and obj_events[-1].time < max_time:
            if bound_events[-1].obj is None:
                # Should nearly never happen
                obj_events.append(
                    ObjEvent(
                        time=max_time,
                        obj=obj_events[-1].obj,
                        bound=bound_events[-1].bound,
                        msg="",
                    )
                )
            else:
                obj_events.append(
                    ObjEvent(
                        time=max_time,
                        obj=bound_events[-1].obj,
                        bound=bound_events[-1].bound,
                        msg="",
                    )
                )
        if bound_events and bound_events[-1].time < max_time:
            bound_events.append(
                BoundEvent(
                    time=max_time,
                    obj=obj_events[-1].obj,
                    bound=obj_events[-1].bound,
                    msg="",
                )
            )

        # plot the objective values over time. Add the comment as hover text
        fig.add_trace(
            go.Scatter(
                x=[o.time for o in obj_events],
                y=[o.obj for o in obj_events],
                mode="lines+markers",
                line=dict(color="green"),
                name="Objective",
                hovertext=[o.msg for o in obj_events],
            )
        )

        # plot the bounds over time. Add the comment as hover text
        fig.add_trace(
            go.Scatter(
                x=[b.time for b in bound_events],
                y=[b.bound for b in bound_events],
                mode="lines+markers",
                line=dict(color="red"),
                name="Bound",
                hovertext=[b.msg for b in bound_events],
            )
        )

        # make the x-axis start at 0
        fig.update_xaxes(range=[0, 1.01 * max_time])
        fig.update_layout(
            title="Search progress",
            xaxis_title="Time (s)",
            yaxis_title="Objective",
            legend_title="Legend",
            font=dict(family="Courier New, monospace", size=18, color="RebeccaPurple"),
        )
        return fig
