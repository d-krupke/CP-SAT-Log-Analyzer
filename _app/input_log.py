import datetime
import streamlit as st
import os


def get_data_from_url(url):
    import urllib.request
    import urllib.parse

    url_ = "https://cpsat-log-analyzer.streamlit.app/?" + urllib.parse.urlencode(
        {"from_url": url}
    )
    try:
        data = urllib.request.urlopen(url).read(20_000).decode("utf-8")
    except Exception as e:
        st.error(f"Could not load log from `{url}`. Error: {e}")
        return None
    st.info(
        f"Loading log from `{url}`. You can share it with others using [{url_}]({url_})."
    )
    return data


def input_log():
    # accept log via file upload or text input
    data = None
    save_to_history = True
    log_file = st.file_uploader("Upload a log file", type="txt")
    if log_file is not None:
        data = log_file.read().decode("utf-8")
    else:
        log_text = st.text_area("Or paste a log here")
        if log_text:
            data = log_text
        url = st.text_input("Or load a log from a URL:", value="")
        if url:
            data = get_data_from_url(url)
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
                        save_to_history = False

    if not data and "from_url" in st.query_params:
        url = st.query_params.get_all("from_url")[0]
        data = get_data_from_url(url)
    if not data and "example" in st.query_params:
        example = st.query_params.get_all("example")[0]
        import urllib.request
        import urllib.parse

        url = "https://cpsat-log-analyzer.streamlit.app/?" + urllib.parse.urlencode(
            {"example": example}
        )
        st.info(
            f"Loading example log `{example}`. You can share it with others using [{url}]({url})."
        )
        if "/" in example:
            st.error(f"Invalid example log `{example}`.")
            return None
        example_path = f"example_logs/{example}.txt"
        if not os.path.dirname(example_path).endswith("example_logs"):
            st.error(f"Invalid example log `{example}`.")
            return None
        if not os.path.exists(example_path):
            st.error(f"Example log `{example}` does not exist.")
            return None
        with open(f"example_logs/{example}.txt") as f:
            data = f.read()
    # show a history of the previous logs in the sidebar and allow to select them again
    if "cpsat_log_history" not in st.session_state:
        st.session_state["cpsat_log_history"] = {}
    history = st.session_state["cpsat_log_history"]
    if save_to_history and data:
        # use current time/date as key
        key = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "cpsat_log_history" not in st.session_state:
            st.session_state["cpsat_log_history"] = {}
        if "cpsat_log_history_hashes" not in st.session_state:
            st.session_state["cpsat_log_history_hashes"] = []
        history_hash = hash(data)
        if history_hash not in st.session_state["cpsat_log_history_hashes"]:
            st.session_state["cpsat_log_history_hashes"].append(history_hash)
            history[key] = data
            st.session_state["cpsat_log_history"] = history
    if history:
        with st.sidebar:
            st.markdown("### Previous Logs")
            reversed_keys = list(history.keys())[::-1]
            for key in reversed_keys:
                if st.button(f"{key}"):
                    data = history.get(key, None)
                    save_to_history = False

    # delete log button
    if st.button("Clear", use_container_width=True, help="Delete the current log."):
        data = None
    return data
