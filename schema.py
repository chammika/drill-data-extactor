"""Extraction schema. Every scalar is a string ("" when blank on the form)."""
from pydantic import BaseModel, Field


class Summary(BaseModel):
    well_no: str = Field(description="As written on the Site Location Sheet, e.g. 36/146")
    location: str
    divisional_secretariat: str = Field(description="DS / P.S. division")
    gn_division: str = Field(description="G.S. / GN division from the Site Location Sheet")
    drilling_start_date: str = Field(description="YYYY-MM-DD, from the drill log")
    drilling_end_date: str = Field(description="YYYY-MM-DD, from the drill log")
    yield_rate: str = Field(description="Drill log header yield, with unit, e.g. '800 l/min'")
    total_depth_m: str = Field(description="Drill log final depth")
    overburden_depth_m: str = Field(description="Depth at which the drill log description changes to rock; if not stated, the casing length")
    pvc_casing_length_m: str = Field(description="Drill log casing length")
    fracture_depths_m: str = Field(description="All fracture depths from the drill log rows, comma separated")
    static_water_level_m: str = Field(description="From the latest pumping test; if none, the drill log SWL")
    dynamic_water_level_m: str = Field(description="Latest pumping test: static water level + drawdown at end of test. Blank if no drawdown is given")
    pump_test_duration: str = Field(description="Latest pumping test duration of pumping, with unit, e.g. '1440 min'")
    remarks: str = Field(description="Short notable remarks about this well")


class LocationSheet(BaseModel):
    source_pages: str = Field(description="PDF page numbers of this form, e.g. '1-2'")
    well_no: str
    project_office: str
    district: str
    electorate: str
    village: str
    ps_division: str
    gs_division: str
    location: str
    investigation_order_no: str
    land_owner_name_address: str
    permission_obtained: str = Field(description="yes / no / blank")
    within_road_reservation: str = Field(description="yes / no / blank")
    request_made_by: str
    request_date: str
    funding_criteria: str = Field(description="on payment / board funds / capital budget")
    well_category: str = Field(description="HPTW / productive well / test well")
    project_name: str
    contract_order_no: str
    funded_by: str
    distance_to_nearest_public_perennial_well: str
    houses_within_500m: str
    consent_of_ps_for_maintenance: str = Field(description="yes / no / blank")
    consumer_society_formed: str = Field(description="yes / no / blank")
    caretaker_name_address: str
    geomorphology: str
    soil_types: str
    rock_types: str
    structure: str
    geophysical_survey: str = Field(description="yes / no / blank")
    expected_overburden_m: str
    proposed_depth_m: str
    expected_discharge: str
    type_of_drilling: str = Field(description="DTH / rotary / rotary mud / ODEX / other")
    drilling_instructions: str
    topo_sheet: str
    topo_scale: str
    geology_map: str
    geology_scale: str
    air_photo_no: str
    coordinates_x: str
    coordinates_y: str
    sketch_notes: str = Field(description="Text labels and distances written on the sketch")
    site_selected_to_satisfy: str = Field(description="hydrogeological conditions / community request / both")
    other_comments: str
    site_located_by: str
    located_date: str
    site_approved_by: str
    approved_date: str
    extra_handwritten_notes: str = Field(description="Notes written outside the form boxes")


class DrillLogRow(BaseModel):
    date: str = Field(description="YYYY-MM-DD; carry the date down from the row where it was last written")
    rod_no: str
    time_start: str
    time_finish: str
    duration_min: str
    drill_bit_no_dia: str
    depth_m: str
    yield_lpm: str
    ec_us_cm: str
    fracture_depth_m: str
    description: str


class DrillLog(BaseModel):
    source_pages: str
    well_no: str
    project_office: str
    district: str
    village: str
    ds_division: str
    location: str
    date_start: str
    date_finish: str
    casing_dia: str
    casing_length_m: str
    drilling_type_overburden: str = Field(description="DTH / mud / other")
    drilling_type_rock: str = Field(description="DTH / other")
    screen_from_m: str
    screen_to_m: str
    final_depth_m: str
    yield_lpm: str
    swl_m: str
    swl_datetime: str
    final_ec_us_cm: str
    soil_sample_collected: str = Field(description="yes / no / blank")
    water_sample_collected: str = Field(description="yes / no / blank")
    driller_name: str
    olc_name: str
    rows: list[DrillLogRow] = Field(description="Every filled table row, in the order written, across all drill log pages")


class StepTestRow(BaseModel):
    step: str
    discharge_lpm: str
    remarks: str


class ConstantDischarge(BaseModel):
    discharge_rate_lpm: str
    pumping_duration_min: str
    recovery_duration_min: str
    drawdown_end_m: str
    recovered_water_level_mbgl: str
    ec_us_cm: str


class Recommendation(BaseModel):
    pumping_rate_lpm: str
    pumping_hours_per_day: str
    pumping_water_level_mbgl: str
    pump_installation_depth_mbgl: str
    notes: str


class PumpTest(BaseModel):
    source_pages: str
    report_date: str
    test_started_date: str
    total_depth_m: str
    min_diameter_mm: str
    main_fracture_from_m: str
    main_fracture_to_m: str
    static_water_level_mbgl: str
    pump_type: str
    pump_outer_diameter_mm: str
    measuring_height_m: str
    step_test: list[StepTestRow]
    constant_discharge: ConstantDischarge
    recommendation: Recommendation


class OtherSection(BaseModel):
    page: str
    title: str
    text: str


class Extraction(BaseModel):
    summary: Summary
    location_sheet: LocationSheet
    drill_log: DrillLog
    pump_tests: list[PumpTest] = Field(description="One entry per pumping test report, for this file's well only, oldest first")
    other_sections: list[OtherSection] = Field(description="Letters, job cards, annexes, discussion and other content not covered by the forms")
