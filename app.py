import streamlit as st
from cpsat_log_parser import parse_blocks

from cpsat_log_parser.blocks import (
    SearchProgressBlock,
    SearchStatsBlock,
    SolutionsBlock,
    TableBlock,
    SolverBlock,
    ResponseBlock,
    PresolveLogBlock,
    InitialModelBlock,
    PresolvedModelBlock,
)

st.title("CP-SAT Log Analyzer")
st.markdown(
    "Dive into the world of constraint programming with ease using our CP-SAT Log Analyzer. This tool transforms the dense and detailed logs of CP-SAT into clear, readable formats, complemented by intuitive visualizations of key metrics. Whether you're tuning your model or exploring data, our analyzer simplifies and enlightens your journey with CP-SAT. Let us make complex logs simple and actionable!"
)

st.markdown(
    "[![d-krupke - CP-SAT Log Analyzer](https://img.shields.io/badge/d--krupke-CP--SAT%20Log%20Analyzer-blue?style=for-the-badge&logo=github)](https://github.com/d-krupke/CP-SAT-Log-Analyzer) Feel free to open issues or contribute."
)
st.markdown(
    "[![d-krupke - CP-SAT Primer](https://img.shields.io/badge/d--krupke-CP--SAT%20Primer-blue?style=for-the-badge&logo=github)](https://github.com/d-krupke/cpsat-primer) This project is a sibling of the CP-SAT Primer."
)


st.header("Log File")
st.markdown(
    """
To begin analyzing with CP-SAT Log Analyzer, please upload your log file. If you haven't already, you can generate a log file by enabling the log output. Simply set the `log_search_progress` parameter to `True` in your CP-SAT solver configuration. Once this is done, you'll have a detailed log ready for upload and analysis.

The log usually starts as follows:
```
Starting CP-SAT solver v9.7.2996
Parameters: log_search_progress: true
Setting number of workers to 24

...
```

Only complete and properly formatted logs are supported for now.
"""
)
# accept log via file upload or text input
data = None
log_file = st.file_uploader("Upload a log file", type="txt")
if log_file is not None:
    data = log_file.read().decode("utf-8")
else:
    log_text = st.text_area("Or paste a log here")
    if log_text:
        data = log_text
    # example logs per button
    st.markdown("Or use one of the following example logs:")
    examples = [
        "example_logs/98_02.txt",
        "example_logs/98_03.txt",
        "example_logs/98_04.txt",
        "example_logs/97_01.txt",
    ]
    cols = st.columns(len(examples))
    for i, example in enumerate(examples):
        if cols[i].button(f"Example {i+1}"):
            with open(example) as f:
                data = f.read()


def get_named_blocks(blocks) -> dict:
    named_blocks = {}
    for block in blocks:
        named_blocks[type(block)] = block
    return named_blocks


def show_overview(blocks):
    block_dict = get_named_blocks(blocks)
    st.subheader("Overview", divider=True)
    solver_block = block_dict[SolverBlock]
    initial_model_block = block_dict[InitialModelBlock]
    search_progress_block = block_dict[SearchProgressBlock]
    response_block = block_dict[ResponseBlock]
    col1, col2 = st.columns(2)
    major, minor, patch = solver_block.get_parsed_version()
    if major < 9 or (major == 9 and minor < 8):
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

    col1, col2 = st.columns(2)
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
    # col3.metric("Model Fingerprint", value=initial_model_block.get_model_fingerprint())

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Objective",
        value=response["objective"],
        help="Value of the best solution found.",
    )
    col2.metric(
        label="Best bound",
        value=response["best_bound"],
        help="Bound on how good the best solution can be. If it matches the objective, the solution is optimal.",
    )
    gap = response_block.get_gap()
    gap_help = "The gap is the difference between the objective and the best bound. The smaller the better. A gap of 0% means that the solution is optimal."
    if gap is None:
        col3.metric(label="Gap", value="N/A", help=gap_help)
    else:
        col3.metric(label="Gap", value=f"{gap:.2f}%", help=gap_help)
        if response["status"] == "OPTIMAL" and gap > 0:
            st.error(
                "CP-SAT returned the status `OPTIMAL`, but does not have a matching bound. This indicates a bug."
            )

    if response["status"] in ("OPTIMAL", "FEASIBLE"):
        st.plotly_chart(search_progress_block.as_plotly(), use_container_width=True)


if not data:
    st.stop()
else:
    st.header("Log Analysis")
    st.warning(
        "This is just a prototype and may crash or show wrong results. Please report any issues [here](https://github.com/d-krupke/CP-SAT-Log-Analyzer). I welcome any feedback and complex logs to test this on."
    )
    blocks = parse_blocks(data)
    show_overview(blocks)

    st.markdown("*You can expand the following block to see the raw log.*")
    with st.expander("Raw Log"):
        st.text(data)
    st.markdown(
        "*The following part contains a parsed version of the log, easier for analysis. Depending on the CP-SAT version, not all parts may be parsed properly.*"
    )

    for block in blocks:
        if isinstance(block, SearchProgressBlock):
            st.subheader("Search", divider=True)
            with st.expander(block.get_title(), expanded=True):
                if block.get_help():
                    st.info(block.get_help())
                st.text(str(block))
                fig = block.as_plotly()
                st.plotly_chart(fig, use_container_width=True)
            st.subheader("Statistics", divider=True)
            st.info(
                "This part contains detailed statistics about the search. Only a few elements are useful for the common user."
            )
        elif isinstance(block, SolverBlock):
            st.subheader("Initialization", divider=True)
            st.info(
                "This block contains some basic information about the solver and the model. For example, you can check how large the model is which parameters were changed."
            )
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                st.text(str(block))
        elif isinstance(block, SearchStatsBlock):
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                df = block.to_pandas()
                st.dataframe(
                    df,
                    column_config={
                        "Restarts": st.column_config.NumberColumn(
                            help="Restarting the search once we learned about the importance of variables can significantly reduce the size of the search tree."
                        ),
                    },
                )

        elif isinstance(block, SolutionsBlock):
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                st.markdown(f"Number of solutions: {block.get_num_solutions()}")
                df = block.to_pandas()
                st.dataframe(df, use_container_width=True)
        elif isinstance(block, PresolvedModelBlock):
            with st.expander(block.get_title(), expanded=True):
                if block.get_help():
                    st.info(block.get_help())
                st.text(str(block))
        elif isinstance(block, ResponseBlock):
            st.subheader("Summary", divider=True)
            with st.expander(block.get_title(), expanded=True):
                if block.get_help():
                    st.info(block.get_help())
                df = block.to_pandas()
                st.dataframe(df.transpose(), use_container_width=True)
        elif isinstance(block, PresolveLogBlock):
            st.subheader("Presolve", divider=True)
            st.info(
                "This block contains information about the presolve phase, which is the first step of the solver. It tries to simplify the model before the actual search starts. This can significantly reduce the size of the search tree."
            )
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                st.text(str(block))
        elif isinstance(block, TableBlock):
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                tab1, tab2 = st.tabs(["Table", "Raw"])
                df = block.to_pandas()
                tab1.dataframe(df, use_container_width=True)
                tab2.text(str(block))
        else:
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                st.text(str(block))
