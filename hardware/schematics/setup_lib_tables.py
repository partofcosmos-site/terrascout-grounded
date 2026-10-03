import os

sch_dir = 'C:/Users/white/terrascout-grounded/hardware/schematics'
template_sym_path = 'C:/Program Files/KiCad/10.0/share/kicad/template/sym-lib-table'

with open(template_sym_path, 'r', encoding='utf-8') as f:
    sym_lines = f.readlines()

custom_entry = '\t(lib (name "terrascout_custom") (type "KiCad") (uri "C:/Users/white/terrascout-grounded/hardware/schematics/terrascout_custom.kicad_sym") (options "") (descr "TerraScout Rover Custom Component Library"))\n'
new_sym_lines = [sym_lines[0], sym_lines[1], custom_entry] + sym_lines[2:]

with open(os.path.join(sch_dir, 'sym-lib-table'), 'w', encoding='utf-8') as f:
    f.writelines(new_sym_lines)

# Also copy to user AppData so kicad-cli always has it globally!
user_kicad_dir = os.path.expanduser('~/AppData/Roaming/kicad/10.0')
with open(os.path.join(user_kicad_dir, 'sym-lib-table'), 'w', encoding='utf-8') as f:
    f.writelines(new_sym_lines)

print("Updated sym-lib-table with absolute path in both project and AppData")
