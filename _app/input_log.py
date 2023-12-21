import streamlit as st


def input_log():
    # accept log via file upload or text input
    data = None
    log_file = st.file_uploader("Upload a log file", type="txt")
    if log_file is not None:
        data = log_file.read().decode("utf-8")
    else:
        log_text = st.text_area("Or paste a log here")
        if log_text:
            data = log_text
        url = st.text_input("Or load a log from a URL:")
        if url:
            import urllib.request
            import urllib.parse

            url_ = (
                "https://cpsat-log-analyzer.streamlit.app/?"
                + urllib.parse.urlencode({"from_url": url})
            )
            st.info(
                f"Loading log from `{url}`. You can share it with others using [{url_}]({url_})."
            )
            data = urllib.request.urlopen(url).read(20_000).decode("utf-8")
        # example logs per button
        st.markdown("Or use one of the following example logs:")
        examples = [
            {
                "file": "example_logs/98_02.txt",
                "origin": "This log originates from a TSP with MTZ constraints. It is not solved to optimality.",
            },
            {
                "file": "example_logs/98_03.txt",
                "origin": "This log originates from a TSP with AddCircuit constraint. It only has a single, but expensive, constraint.",
            },
            {
                "file": "example_logs/98_04.txt",
                "origin": "This log originates from a Multi-Knapsack problem.",
            },
            {
                "file": "example_logs/98_05.txt",
                "origin": "This log originates from a Packing problem.",
            },
            {
                "file": "example_logs/98_06.txt",
                "origin": "This log originates from a Packing problem.",
            },
            {
                "file": "example_logs/98_07.txt",
                "origin": "This log originates from a Knapsack problem run on an old Macbook. It spends most of the time in presolve.",
            },
            {
                "file": "example_logs/98_08.txt",
                "origin": "An example from an iteration of SampLNS",
            },
            {
                "file": "example_logs/97_01.txt",
                "origin": "This was an example log flying around on my computer for teaching purposes.",
            },
        ]
        # at most 5 examples per row
        row_length = 4
        for i in range(0, len(examples), row_length):
            cols = st.columns(min(len(examples) - i, row_length))
            for j, example in enumerate(examples[i : i + row_length]):
                if cols[j].button(f"Example {i+j+1}", help=example.get("origin", None)):
                    with open(example["file"]) as f:
                        data = f.read()

    query_params = st.experimental_get_query_params()
    if not data and "from_url" in query_params:
        url = query_params["from_url"][0]
        import urllib.request
        import urllib.parse

        url_ = "https://cpsat-log-analyzer.streamlit.app/?" + urllib.parse.urlencode(
            {"from_url": url}
        )
        st.info(
            f"Loading log from `{url}`. You can share it with others using [{url_}]({url_})."
        )
        data = urllib.request.urlopen(url).read(20_000).decode("utf-8")
    if not data and "example" in query_params:
        example = query_params["example"][0]
        import urllib.request
        import urllib.parse

        url = "https://cpsat-log-analyzer.streamlit.app/?" + urllib.parse.urlencode(
            {"example": example}
        )
        st.info(
            f"Loading example log `{example}`. You can share it with others using [{url}]({url})."
        )
        with open(f"example_logs/{example}.txt") as f:
            data = f.read()
    return data
