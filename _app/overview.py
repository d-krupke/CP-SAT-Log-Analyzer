import streamlit as st

from cpsat_log_parser.blocks import (
    SearchProgressBlock,
    SolverBlock,
    ResponseBlock,
    InitialModelBlock,
)


def show_overview(parser):
    st.subheader("Overview", divider=True)
    if parser.comments:
        with st.chat_message("user"):
            # escape markdown to prevent XSS
            comment = "\n".join(parser.comments)
            comment = comment.replace("\\", "")
            comment = comment.replace("[", "\\[*")
            comment = comment.replace("]", "*\\]")
            st.write(comment)
    try:
        solver_block = parser.get_block_of_type(SolverBlock)
        initial_model_block = parser.get_block_of_type(InitialModelBlock)
        search_progress_block = parser.get_block_of_type(SearchProgressBlock)
        response_block = parser.get_block_of_type(ResponseBlock)
        col1, col2 = st.columns(2)
        major, minor, patch = solver_block.get_parsed_version()
        if major < 9 or (major == 9 and minor < 9):
            col1.metric(
                label="CP-SAT Version",
                value=solver_block.get_version(),
                help="CP-SAT has seen significant performance improvements over the last years. Make sure to use the latest version.",
                delta="outdated",
                delta_color="inverse",
            )
        else:
            col1.metric(
                label="CP-SAT Version",
                value=solver_block.get_version(),
                help="CP-SAT has seen significant performance improvements over the last years. Make sure to use the latest version.",
            )
        col2.metric(
            label="Number of workers",
            value=solver_block.get_number_of_workers(),
            help="CP-SAT has different parallelization tiers, triggered by the number of workers. More workers can improve performance. Fine more information [here](https://github.com/google/or-tools/blob/main/ortools/sat/docs/troubleshooting.md#improving-performance-with-multiple-workers)",
        )
        # https://github.com/google/or-tools/blob/main/ortools/sat/docs/troubleshooting.md#improving-performance-with-multiple-workers

        # print all parameters (key: value)
        if solver_block.get_parameters():
            md = "*CP-SAT was setup with the following parameters:*\n"
            st.markdown(md)
            st.json(solver_block.get_parameters())
            st.markdown(
                "*You can find more information about the parameters [here](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto).*"
            )

        col1, col2, col3 = st.columns(3)
        response = response_block.to_dict()

        col1.metric(
            label="Status",
            value=response["status"],
            help="""
    CP-SAT can have 5 different statuses:
    - `UNKNOWN`: The solver timed out before finding a solution or proving infeasibility.
    - `OPTIMAL`: The solver found an optimal solution. This is the best possible status.
    - `FEASIBLE`: The solver found a feasible solution, but it is not guaranteed to be optimal.
    - `INFEASIBLE`: The solver proved that the problem is infeasible. This often indicates a bug in the model.
    - `MODEL_INVALID`: Definitely a bug. Should rarely happen.
    """,
        )
        col2.metric(
            label="Time",
            value=f"{float(response['walltime']):.3f}s",
            help="The total time spent by the solver. This includes the time spent in presolve and the time spent in the search.",
        )
        col3.metric(
            label="Presolve",
            value=f"{search_progress_block.get_presolve_time():.3f}s",
            help="The time spent in presolve. This is usually a small fraction of the total time.",
        )

        col1, col2, col3 = st.columns(3)
        col1.metric(
            label="Variables",
            value=initial_model_block.get_num_variables(),
            help="CP-SAT can handle (hundreds of) thousands of variables. This just gives a rough estimate of the size of the problem. Check *Initial Optimization Model* for more information. Many variables may also be removed during presolve, check *Presolve Summary*.",
        )
        col2.metric(
            label="Constraints",
            value=initial_model_block.get_num_constraints(),
            help="CP-SAT can handle (hundreds of) thousands of constraints. More important than the number is the type of constraints. Some constraints are more expensive than others. Check *Initial Optimization Model* for more information.",
        )
        col3.metric(
            label="Type",
            value="Optimization"
            if initial_model_block.is_optimization()
            else "Satisfaction",
            help="Is the model an optimization or satisfaction model?",
        )
        # col3.metric("Model Fingerprint", value=initial_model_block.get_model_fingerprint())

        col1, col2, col3 = st.columns(3)
        try:
            obj = float(response["objective"])
        except ValueError:
            obj = None
        col1.metric(
            label="Objective",
            value=obj,
            help="Value of the best solution found.",
        )
        try:
            bound = float(response["best_bound"])
        except ValueError:
            bound = None
        col2.metric(
            label="Best bound",
            value=bound,
            help="Bound on how good the best solution can be. If it matches the objective, the solution is optimal.",
        )
        gap = response_block.get_gap()
        gap_help = "The gap is the difference between the objective and the best bound. The smaller the better. A gap of 0% means that the solution is optimal."
        if gap is None:
            col3.metric(label="Gap", value=None, help=gap_help)
        else:
            col3.metric(label="Gap", value=f"{gap:.2f}%", help=gap_help)
            if response["status"] == "OPTIMAL" and gap > 0:
                st.error(
                    "CP-SAT returned the status `OPTIMAL`, but does not have a matching bound. This indicates a bug."
                )

        if (
            response["status"] in ("OPTIMAL", "FEASIBLE")
            and initial_model_block.is_optimization()
        ):
            fig = search_progress_block.as_plotly()
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    except KeyError as ke:
        st.error(
            f"Error parsing information. Log seems to be incomplete: {ke}. Make sure you enter the full log without any modifications. The parser is sensitive to new lines."
        )
