import os

sch_dir = 'C:/Users/white/terrascout-grounded/hardware/schematics'

# Read template sym-lib-table from KiCad installation
template_sym_path = 'C:/Program Files/KiCad/10.0/share/kicad/template/sym-lib-table'
with open(template_sym_path, 'r', encoding='utf-8') as f:
    sym_lines = f.readlines()

# Insert terrascout_custom as the first library
custom_entry = '\t(lib (name "terrascout_custom") (type "KiCad") (uri "${KIPRJMOD}/terrascout_custom.kicad_sym") (options "") (descr "TerraScout Rover Custom Component Library"))\n'
new_sym_lines = [sym_lines[0], sym_lines[1], custom_entry] + sym_lines[2:]

with open(os.path.join(sch_dir, 'sym-lib-table'), 'w', encoding='utf-8') as f:
    f.writelines(new_sym_lines)

# Read template fp-lib-table from KiCad installation
template_fp_path = 'C:/Program Files/KiCad/10.0/share/kicad/template/fp-lib-table'
if os.path.exists(template_fp_path):
    with open(template_fp_path, 'r', encoding='utf-8') as f:
        fp_content = f.read()
    with open(os.path.join(sch_dir, 'fp-lib-table'), 'w', encoding='utf-8') as f:
        f.write(fp_content)

print("Created sym-lib-table and fp-lib-table in schematics dir")
