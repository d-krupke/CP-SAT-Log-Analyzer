"""
This file is the main entry point for the Streamlit app.
Further parts of the app are in the `_app` folder.
The logic for parsing the log is in the `cpsat_log_parser` folder.
"""

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
    TaskTimingBlock,
    PresolvedModelBlock,
)
from _app import print_header, input_log, show_overview

print_header()
data = input_log()

if data:
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
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    st.info(
                        "This plot shows you how the quality of the solution (objective), and the proved quality (bound) converge over time. It allows you to estimate if finding good solutions or proving optimality is the bottleneck."
                    )
                fig_3 = block.gap_as_plotly()
                if fig_3:
                    st.plotly_chart(fig_3, use_container_width=True)
                    st.info(
                        "This plot shows you how the gap between the objective and the bound changes over time. If it quickly reaches a small value but then does not improve for a long time, you could set the `relative_gap_limit` parameter to allow to stop the search as soon as a specific solution quality is reached."
                    )
                fig_2 = block.model_changes_as_plotly()
                if fig_2:
                    st.plotly_chart(fig_2, use_container_width=True)
                    st.info(
                        "This plot shows you how the size of the model changes over time."
                    )

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
        elif isinstance(block, TaskTimingBlock):
            with st.expander(block.get_title()):
                if block.get_help():
                    st.info(block.get_help())
                tab1, tab2 = st.tabs(["Table", "Raw"])
                df_1 = block.to_pandas(deterministic=False)
                tab1.dataframe(df_1, use_container_width=True)
                df_2 = block.to_pandas(deterministic=True)
                tab1.dataframe(df_2, use_container_width=True)
                tab2.text(str(block))
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
