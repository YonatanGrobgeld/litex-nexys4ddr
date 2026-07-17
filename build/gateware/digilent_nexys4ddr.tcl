# Vivado build script for digilent_nexys4ddr SoC (DOT8 + EXP_LUT + GEMV).
# Run from Vivado tcl shell:
#   cd <this folder>
#   vivado -mode batch -source digilent_nexys4ddr.tcl
# Or open Vivado GUI -> Tools -> Run Tcl Script -> select this file.

# Create Project
create_project -force -name digilent_nexys4ddr -part xc7a100tcsg324-1
set_msg_config -id {Common 17-55} -new_severity {Warning}

# Add Sources (relative paths - run vivado from this directory)
read_verilog ./VexRiscv_Dot8.v
read_verilog ./exp_lut.v
read_verilog ./gemv_core.v
read_verilog ./digilent_nexys4ddr.v

# Add constraints
read_xdc digilent_nexys4ddr.xdc
set_property PROCESSING_ORDER EARLY [get_files digilent_nexys4ddr.xdc]

# Synthesis
synth_design -directive default -top digilent_nexys4ddr -part xc7a100tcsg324-1

report_timing_summary -file digilent_nexys4ddr_timing_synth.rpt
report_utilization -hierarchical -file digilent_nexys4ddr_utilization_hierarchical_synth.rpt
report_utilization -file digilent_nexys4ddr_utilization_synth.rpt
write_checkpoint -force digilent_nexys4ddr_synth.dcp

# Optimize
opt_design -directive default

# Placement
place_design -directive default
report_utilization -hierarchical -file digilent_nexys4ddr_utilization_hierarchical_place.rpt
report_utilization -file digilent_nexys4ddr_utilization_place.rpt
report_io -file digilent_nexys4ddr_io.rpt
report_control_sets -verbose -file digilent_nexys4ddr_control_sets.rpt
report_clock_utilization -file digilent_nexys4ddr_clock_utilization.rpt
write_checkpoint -force digilent_nexys4ddr_place.dcp

# Routing
route_design -directive default
phys_opt_design -directive default
write_checkpoint -force digilent_nexys4ddr_route.dcp

report_timing_summary -no_header -no_detailed_paths
report_route_status -file digilent_nexys4ddr_route_status.rpt
report_drc -file digilent_nexys4ddr_drc.rpt
report_timing_summary -datasheet -max_paths 10 -file digilent_nexys4ddr_timing.rpt
report_power -file digilent_nexys4ddr_power.rpt

# Bitstream
write_bitstream -force digilent_nexys4ddr.bit

quit
