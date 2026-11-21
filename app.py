import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from pydantic import BaseModel

import db
from extract import PROVIDERS, extract
from schema import Extraction
from viewer import viewer_html

LONG_TEXT = {
    "remarks", "notes", "text", "drilling_instructions", "other_comments", "sketch_notes",
    "extra_handwritten_notes", "land_owner_name_address", "caretaker_name_address",
}

# Field arrangement that follows the printed forms: a string is a section heading, a list is one row.
LAYOUTS = {
    "location_sheet": [
        "Location",
        ["project_office", "well_no"],
        ["district", "ps_division"],
        ["electorate", "gs_division"],
        ["village", "location"],
        ["investigation_order_no"],
        ["land_owner_name_address", "permission_obtained", "within_road_reservation"],
        "Request",
        ["request_made_by", "request_date"],
        ["funding_criteria", "contract_order_no"],
        ["well_category"],
        ["project_name", "funded_by"],
        "General",
        ["distance_to_nearest_public_perennial_well", "caretaker_name_address"],
        ["houses_within_500m", "consent_of_ps_for_maintenance", "consumer_society_formed"],
        "Geology",
        ["geomorphology"],
        ["soil_types"],
        ["rock_types"],
        ["structure", "geophysical_survey"],
        "Drilling",
        ["expected_overburden_m", "proposed_depth_m", "expected_discharge"],
        ["type_of_drilling"],
        ["drilling_instructions"],
        "Sketch & reference (page 2)",
        ["topo_sheet", "topo_scale"],
        ["geology_map", "geology_scale"],
        ["air_photo_no"],
        ["coordinates_x", "coordinates_y"],
        ["sketch_notes"],
        "Approval",
        ["site_selected_to_satisfy"],
        ["other_comments"],
        ["site_located_by", "site_approved_by"],
        ["located_date", "approved_date"],
        ["extra_handwritten_notes"],
    ],
    "drill_log": [
        ["project_office", "well_no"],
        ["district", "ds_division"],
        ["village", "location"],
        ["date_start", "casing_dia", "drilling_type_overburden", "drilling_type_rock"],
        ["date_finish", "casing_length_m", "screen_from_m", "screen_to_m"],
        ["final_depth_m", "yield_lpm", "swl_m", "swl_datetime", "final_ec_us_cm"],
        ["rows"],
        ["soil_sample_collected", "water_sample_collected"],
        ["driller_name", "olc_name"],
    ],
}

st.set_page_config(page_title="Drill data extractor", layout="wide")
con = db.connect()
ver = st.session_state.setdefault("ver", 0)  # bumped on save so widgets reload from the database


@st.cache_data
def file_hash(path, mtime):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@st.cache_data
def pdf_viewer(path, mtime):
    return viewer_html(path)


def process(path, h):
    """Extracts one file and stores it. Returns False (after showing the error) on failure."""
    try:
        result, tokens_in, tokens_out = extract(path.read_bytes(), provider)
    except Exception as e:  # any provider's API or credential error: show it and carry on
        st.error(f"{path.name}: {e}")
        return False
    db.add_extraction(con, h, str(path), result.model_dump(), tokens_in, tokens_out)
    return True


def label(name):
    return name.replace("_", " ").capitalize()


def edit_field(name, field, value, key):
    ann = field.annotation
    if name == "source_pages":  # reference only, not editable
        st.caption(f"Source pages in the PDF: {value}")
        return value or ""
    if ann is str:
        widget = st.text_area if name in LONG_TEXT else st.text_input
        return widget(label(name), value or "", key=key, help=field.description)
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        st.markdown(f"**{label(name)}**")
        return edit_model(ann, value or {}, key, LAYOUTS.get(name))
    item = ann.__args__[0]  # list[item]
    st.markdown(f"**{label(name)}**")
    if all(f.annotation is str for f in item.model_fields.values()):
        df = pd.DataFrame(value or [], columns=list(item.model_fields), dtype=str)
        return st.data_editor(df, num_rows="dynamic", key=key).fillna("").to_dict("records")
    out = []
    for i, v in enumerate(value or []):
        with st.expander(f"{label(name)} {i + 1}", expanded=True):
            out.append(edit_model(item, v, f"{key}.{i}"))
    return out


def edit_model(model, value, key, layout=None):
    fields = model.model_fields
    layout = layout or []
    placed = {n for row in layout if isinstance(row, list) for n in row}
    out = {}
    for row in [[n] for n in fields if n not in placed] + layout:
        if isinstance(row, str):
            st.markdown(f"**{row}**")
            continue
        cols = st.columns(len(row)) if len(row) > 1 else [st.container()]
        for col, name in zip(cols, row):
            with col:
                out[name] = edit_field(name, fields[name], value.get(name), f"{key}.{name}")
    return out


with st.sidebar:
    st.title("Drill data extractor")
    engines = list(PROVIDERS)
    provider = st.selectbox("Extraction engine", engines, index=engines.index(os.environ.get("EXTRACTOR", "claude")))
    folder = Path(st.text_input("Folder with PDF files", "samples")).expanduser()
    pdfs = sorted(folder.glob("*.pdf"))
    hashes = {p: file_hash(str(p), p.stat().st_mtime) for p in pdfs}
    wells = {p: db.well_for_hash(con, h) for p, h in hashes.items()}
    pending = [p for p in pdfs if wells[p] is None]

    if st.button(f"Extract {len(pending)} pending file(s)", disabled=not pending):
        bar = st.progress(0.0)
        for i, p in enumerate(pending):
            bar.progress(i / len(pending), p.name)
            process(p, hashes[p])
        st.rerun()

    def status(p):
        w = wells[p]
        return f"{'pending' if w is None else 'reviewed' if w['reviewed'] else 'extracted'} · {p.name}"

    selected = st.radio("Files", pdfs, format_func=status) if pdfs else None

if selected is None:
    st.info("No PDF files found in this folder.")
    st.stop()

left, right = st.columns(2)

with left:
    st.iframe(pdf_viewer(str(selected), selected.stat().st_mtime), height=900)

with right.container(height=900):
    well = wells[selected]
    if well is None:
        st.write("This file has not been extracted yet.")
        if st.button("Extract this file", type="primary"):
            with st.spinner("Extracting, this takes a minute or two..."):
                ok = process(selected, hashes[selected])
            if ok:
                st.rerun()
        st.stop()

    data = json.loads(well["data"])
    key = f"{well['well_no']}.{ver}"
    st.subheader(f"Well {well['well_no']}")
    st.caption(
        f"Last saved {well['updated_at']} UTC · extraction used "
        f"{well['input_tokens']:,} input / {well['output_tokens']:,} output tokens"
    )
    with st.form("edit"):
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("Save", type="primary")
        reviewed = c2.checkbox("Reviewed", bool(well["reviewed"]), key=f"{key}.reviewed")
        fields = Extraction.model_fields
        edited = {}
        for tab, (name, field) in zip(st.tabs([label(n) for n in fields]), fields.items()):
            with tab:
                edited[name] = edit_field(name, field, data.get(name), f"{key}.{name}")
        if submitted:
            db.save(con, well["well_no"], edited, reviewed)
            st.session_state["ver"] += 1
            st.rerun()
