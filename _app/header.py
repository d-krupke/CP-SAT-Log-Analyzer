import streamlit as st

def print_header():
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
    
