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


class ModelEvent:
    """
    ```
    #Model  24.75s var:39921/39999 constraints:79247/79403
    #Model   9.71s var:37230/39800 constraints:1/1 [skipped_logs=5]
    ```
    """
    def __init__(self, time: float, vars_remaining:int, vars:int, constr_remaining: int, constr: int, msg: typing.Optional[str]):
        self.time = time
        self.vars_remaining = vars_remaining
        self.vars = vars
        self.constr_remaining = constr_remaining
        self.constr = constr
        self.msg = msg

    @staticmethod
    def parse(line: str) -> typing.Optional["ModelEvent"]:
        # Model events start with #Model
        model_pattern = r"#Model\s+(?P<time>\d+\.\d+s)\s+var:(?P<vars_remaining>\d+)/(?P<vars>\d+)\s+constraints:(?P<constr_remaining>\d+)/(?P<constr>\d+)\s*(\[(?P<msg>.*)\])?"
        m = re.match(model_pattern, line)
        if m:
            return ModelEvent(
                time=parse_time(m.group("time")),
                vars_remaining=int(m.group("vars_remaining")),
                vars=int(m.group("vars")),
                constr_remaining=int(m.group("constr_remaining")),
                constr=int(m.group("constr")),
                msg=line,
            )
        else:
            return None

class SearchProgressBlock(LogBlock):
    def __init__(self, lines: typing.List[str]) -> None:
        lines = [l.strip() for l in lines if l.strip()]
        if not lines:
            raise ValueError("No lines to parse")
        if not self.matches(lines):
            raise ValueError("Lines do not match SearchProgressBlock")
        self.lines = lines

    @staticmethod
    def matches(lines: typing.List[str]) -> bool:
        if not lines:
            return False
        return lines[0].strip().lower().startswith("Starting search".lower())

    def _parse_events(self) -> typing.List[typing.Union[BoundEvent, ObjEvent, ModelEvent]]:
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
            model_event = ModelEvent.parse(line)
            if model_event:
                events.append(model_event)
                continue
        return events

    def get_presolve_time(self) -> float:
        # first line looks like this "Starting search at 16.74s with 24 workers."
        m = re.match(
            r"Starting [Ss]earch at (?P<time>\d+\.\d+s) with \d+ workers.",
            self.lines[0],
        )
        if m:
            return parse_time(m.group("time"))
        raise ValueError(f"Could not parse presolve time from '{self.lines[0]}'")

    def get_title(self) -> str:
        return "Search progress:"

    def get_help(self) -> typing.Optional[str]:
        return """
        The search progress log is one of the most important parts of the log and allows you to pinpoint performance issues.
        Here you can see, how the solver progresses over time and were it struggles
        the most. Are the upper or the lower bounds the problem? Does the solver quickly find a near optimal solution, but then struggles to close a small gap?

        You probably have to zoom into the plot to see the details as the first
        values can be very large. Check out which part converges the fastest.
        """
    
    def model_changes_as_plotly(self) -> go.Figure:
        """
        Plot the model changes in percent over time.
        """
        model_events = [e for e in self._parse_events() if isinstance(e, ModelEvent)]
        fig = go.Figure()
        if not model_events:
            return fig
        # add number of vars
        fig.add_trace(
            go.Scatter(
                x=[e.time for e in model_events],
                y=[100*(e.vars_remaining/e.vars) for e in model_events],
                mode="lines+markers",
                line=dict(color="red"),
                name="Variables",
                hovertext=[e.msg for e in model_events],
            )
        )
        # add number of constraints
        fig.add_trace(
            go.Scatter(
                x=[e.time for e in model_events],
                y=[100*(e.constr_remaining/e.constr) for e in model_events],
                mode="lines+markers",
                line=dict(color="blue"),
                name="Constraints",
                hovertext=[e.msg for e in model_events],
            )
        )
        # make the x-axis start at 0
        fig.update_xaxes(range=[0, 1.01 * model_events[-1].time])
        # make the y-axis range from 0 to 100
        fig.update_yaxes(range=[0, 101])
        fig.update_layout(
            title="Model changes",
            xaxis_title="Time (s)",
            yaxis_title="Remaining (%)",
            legend_title="Legend",
            font=dict(family="Courier New, monospace", size=18, color="RebeccaPurple"),
        )
        return fig

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
