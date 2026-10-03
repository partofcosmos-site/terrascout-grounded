import os
import uuid

KICAD_SYM_DIR = "C:/Program Files/KiCad/10.0/share/kicad/symbols"

def get_official_sym_text(lib_name, sym_name):
    """Extracts official symbol text from KiCad system libraries and wraps it as lib_name:sym_name"""
    path = os.path.join(KICAD_SYM_DIR, f"{lib_name}.kicad_sym")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1:
        return None
    depth = 0
    start = idx
    end = -1
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    s = text[start:end]
    return s.replace(f'(symbol "{sym_name}"', f'(symbol "{lib_name}:{sym_name}"', 1)

def get_custom_sym_text(sym_name):
    """Extracts custom symbol text from terrascout_custom.kicad_sym"""
    path = os.path.join("C:/Users/white/terrascout-grounded/hardware/schematics/terrascout_custom.kicad_sym")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    target = f'(symbol "{sym_name}"'
    idx = text.find(target)
    if idx == -1:
        return None
    depth = 0
    start = idx
    end = -1
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    s = text[start:end]
    return s.replace(f'(symbol "{sym_name}"', f'(symbol "terrascout_custom:{sym_name}"', 1)

class KiCadSymbolInstance:
    def __init__(self, lib_id, ref, val, footprint, x, y, angle=0, mirror=False, datasheet="~", desc=""):
        self.lib_id = lib_id
        self.ref = ref
        self.val = val
        self.footprint = footprint
        self.x = round(x, 2)
        self.y = round(y, 2)
        self.angle = angle
        self.mirror = mirror
        self.datasheet = datasheet
        self.desc = desc
        self.uuid = str(uuid.uuid4())
        self.pins = []

    def add_pin(self, num):
        p_uuid = str(uuid.uuid4())
        self.pins.append((num, p_uuid))
        return p_uuid

class SchematicSheet:
    def __init__(self, title, sheet_uuid, root_uuid, project_name="terrascout", paper="A4"):
        self.title = title
        self.sheet_uuid = sheet_uuid
        self.root_uuid = root_uuid
        self.project_name = project_name
        self.paper = paper
        self.symbols = []
        self.wires = []
        self.junctions = set()
        self.global_labels = []
        self.no_connects = []
        self.texts = []
        self.sheets = [] # Subsheets if root
        self.needed_lib_symbols = set()

    def add_symbol(self, lib_id, ref, val, footprint, x, y, angle=0, mirror=False, datasheet="~", desc=""):
        sym = KiCadSymbolInstance(lib_id, ref, val, footprint, x, y, angle, mirror, datasheet, desc)
        self.symbols.append(sym)
        self.needed_lib_symbols.add(lib_id)
        return sym

    def add_wire(self, x1, y1, x2, y2):
        self.wires.append((round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2), str(uuid.uuid4())))

    def add_junction(self, x, y):
        self.junctions.add((round(x, 2), round(y, 2)))

    def add_global_label(self, name, x, y, angle=0, shape="bidirectional"):
        self.global_labels.append((name, round(x, 2), round(y, 2), angle, shape, str(uuid.uuid4())))

    def add_no_connect(self, x, y):
        self.no_connects.append((round(x, 2), round(y, 2), str(uuid.uuid4())))

    def add_text(self, text, x, y, size=1.5, bold=True):
        self.texts.append((text, round(x, 2), round(y, 2), size, bold, str(uuid.uuid4())))

    def add_subsheet(self, sheetname, sheetfile, x, y, w, h, subsheet_uuid):
        self.sheets.append({
            'name': sheetname,
            'file': sheetfile,
            'x': round(x, 2),
            'y': round(y, 2),
            'w': round(w, 2),
            'h': round(h, 2),
            'uuid': subsheet_uuid
        })

    def render(self):
        # Build lib_symbols
        lib_syms_rendered = []
        for lid in sorted(list(self.needed_lib_symbols)):
            parts = lid.split(':')
            if len(parts) == 2:
                lib, name = parts
                if lib == "terrascout_custom":
                    stext = get_custom_sym_text(name)
                else:
                    stext = get_official_sym_text(lib, name)
                if stext:
                    lib_syms_rendered.append(stext)
                else:
                    print(f"Warning: could not find symbol text for {lid}")

        lines = [
            "(kicad_sch",
            "\t(version 20250114)",
            "\t(generator \"eeschema\")",
            "\t(generator_version \"10.0\")",
            f"\t(uuid \"{self.sheet_uuid}\")",
            f"\t(paper \"{self.paper}\")",
            "\t(title_block",
            f"\t\t(title \"{self.title}\")",
            "\t\t(date \"2026-10-03\")",
            "\t\t(rev \"v1.0\")",
            "\t\t(company \"TerraScout Autonomous Robotics Division\")",
            "\t\t(comment 1 \"Hack Club Grounded $150 Hardware Grant\")",
            "\t)",
            "\t(lib_symbols"
        ]
        for ls in lib_syms_rendered:
            for l in ls.splitlines():
                lines.append(f"\t\t{l}")
        lines.append("\t)")

        # Subsheets
        for s in self.sheets:
            lines.extend([
                "\t(sheet",
                f"\t\t(at {s['x']} {s['y']})",
                f"\t\t(size {s['w']} {s['h']})",
                "\t\t(exclude_from_sim no)",
                "\t\t(in_bom yes)",
                "\t\t(on_board yes)",
                "\t\t(dnp no)",
                "\t\t(stroke (width 0) (type solid))",
                "\t\t(fill (color 0 0 0 0.0000))",
                f"\t\t(uuid \"{s['uuid']}\")",
                f"\t\t(property \"Sheetname\" \"{s['name']}\" (at {s['x']} {round(s['y'] - 1.5, 2)} 0) (effects (font (size 1.524 1.524)) (justify left bottom)))",
                f"\t\t(property \"Sheetfile\" \"{s['file']}\" (at {s['x']} {round(s['y'] + s['h'] + 2.0, 2)} 0) (effects (font (size 1.524 1.524)) (justify left top)))",
                "\t\t(instances",
                f"\t\t\t(project \"{self.project_name}\"",
                f"\t\t\t\t(path \"/{self.root_uuid}\" (page \"{len(lines)}\"))",
                "\t\t\t)",
                "\t\t)",
                "\t)"
            ])

        # Symbol instances
        is_root = (self.sheet_uuid == self.root_uuid)
        inst_path = f"/{self.root_uuid}" if is_root else f"/{self.root_uuid}/{self.sheet_uuid}"

        for sym in self.symbols:
            lines.extend([
                "\t(symbol",
                f"\t\t(lib_id \"{sym.lib_id}\")",
                f"\t\t(at {sym.x} {sym.y} {sym.angle})",
                "\t\t(unit 1)",
                "\t\t(exclude_from_sim no)",
                "\t\t(in_bom yes)",
                "\t\t(on_board yes)",
                "\t\t(dnp no)",
                f"\t\t(uuid \"{sym.uuid}\")",
                f"\t\t(property \"Reference\" \"{sym.ref}\" (at {round(sym.x + 1.27, 2)} {round(sym.y - 1.27, 2)} 0) (effects (font (size 1.27 1.27)) (justify left)))",
                f"\t\t(property \"Value\" \"{sym.val}\" (at {round(sym.x + 1.27, 2)} {round(sym.y + 1.27, 2)} 0) (effects (font (size 1.27 1.27)) (justify left)))",
                f"\t\t(property \"Footprint\" \"{sym.footprint}\" (at {sym.x} {sym.y} 0) (effects (font (size 1.27 1.27)) (hide yes)))",
                f"\t\t(property \"Datasheet\" \"{sym.datasheet}\" (at {sym.x} {sym.y} 0) (effects (font (size 1.27 1.27)) (hide yes)))",
                f"\t\t(property \"Description\" \"{sym.desc}\" (at {sym.x} {sym.y} 0) (effects (font (size 1.27 1.27)) (hide yes)))"
            ])
            for pnum, puuid in sym.pins:
                lines.append(f"\t\t(pin \"{pnum}\" (uuid \"{puuid}\"))")
            lines.extend([
                "\t\t(instances",
                f"\t\t\t(project \"{self.project_name}\"",
                f"\t\t\t\t(path \"{inst_path}\" (reference \"{sym.ref}\") (unit 1))",
                "\t\t\t)",
                "\t\t)",
                "\t)"
            ])

        # Wires
        for x1, y1, x2, y2, w_uuid in self.wires:
            lines.append(f"\t(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid \"{w_uuid}\"))")

        # Junctions
        for jx, jy in self.junctions:
            lines.append(f"\t(junction (at {jx} {jy}) (diameter 1.0) (color 0 0 0 0) (uuid \"{str(uuid.uuid4())}\"))")

        # Global Labels
        for name, lx, ly, lang, shape, luuid in self.global_labels:
            lines.extend([
                f"\t(global_label \"{name}\"",
                f"\t\t(shape {shape})",
                f"\t\t(at {lx} {ly} {lang})",
                "\t\t(fields_autoplaced yes)",
                "\t\t(effects (font (size 1.27 1.27)) (justify left))",
                f"\t\t(uuid \"{luuid}\")",
                f"\t\t(property \"Intersheetrefs\" \"${{INTERSHEET_REFS}}\" (at {round(lx + 5.0, 2)} {ly} 0) (effects (font (size 1.27 1.27)) (hide yes)))",
                "\t)"
            ])

        # No Connects
        for ncx, ncy, ncuuid in self.no_connects:
            lines.append(f"\t(no_connect (at {ncx} {ncy}) (uuid \"{ncuuid}\"))")

        # Texts
        for txt, tx, ty, tsz, tbld, tuuid in self.texts:
            bld_str = " bold" if tbld else ""
            lines.extend([
                f"\t(text \"{txt}\"",
                f"\t\t(at {tx} {ty} 0)",
                f"\t\t(effects (font (size {tsz} {tsz}){bld_str}) (justify left))",
                f"\t\t(uuid \"{tuuid}\")",
                "\t)"
            ])

        lines.append(")")
        return "\n".join(lines)
