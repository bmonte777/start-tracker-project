"""Quick 2D previews of a board: front and back copper + fabrication outlines as PNG.  usage: preview.py <board-folder> [zoom]"""
import os
import subprocess
import sys

folder = os.path.abspath(sys.argv[1])
zoom = sys.argv[2] if len(sys.argv) > 2 else "9"
name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
out = os.path.join(folder, "out")
for side, layers, mirror in (("front", "F.Cu,F.Fab,F.SilkS,Edge.Cuts", False), ("back", "B.Cu,B.Fab,B.SilkS,Edge.Cuts", True)):
    svg = os.path.join(out, f"{name}-{side}.svg")
    cmd = ["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--mode-single", "--exclude-drawing-sheet", "--page-size-mode", "2", "-o", svg,
           os.path.join(folder, name + ".kicad_pcb")]
    if mirror:
        cmd.insert(4, "--mirror")
    subprocess.run(cmd, capture_output=True)
    subprocess.run(["rsvg-convert", "-z", zoom, "-b", "white", svg, "-o", svg[:-4] + ".png"], capture_output=True)
    print(svg[:-4] + ".png")
