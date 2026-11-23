#!/usr/bin/env python3
"""Draw the Phase 6 app diagrams (Graphviz) into docs/img/06-*.svg and .png. Same style as firmware/tools/diagrams.py."""
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parents[2] / "docs/img"
FONT = 'fontname="Helvetica"'
BASE = (f'graph [{FONT} fontsize=11 bgcolor=white pad=0.2]; '
        f'node [{FONT} fontsize=10 shape=box style="rounded,filled" fillcolor="#f4f6fa" color="#4a5a75"]; '
        f'edge [{FONT} fontsize=9 color="#4a5a75"];')

DIAGRAMS = {
"06-app-layers": f"""
digraph G {{ {BASE} rankdir=TB; compound=true; newrank=true; nodesep=0.25; ranksep=0.35;
 subgraph cluster_ui {{ label="app/ui — shared web UI (HTML · CSS · JS modules, no build step) — Blue Hour, Day / Night / Red"; style=rounded; color="#2f6db5";
   scr [label="Screens (one page, hash routes)\\nConnect · Dashboard · Sky · Align · Rig · Roll · Camera & jobs\\nNight planner · Gallery · PEC · Health · Update · Settings" fillcolor="#e3ecf9"];
   store [label="Store\\nlatest head state · settings · limits\\nconnection · job · camera · toasts"];
   scr -> store [dir=both];
 }}
 subgraph cluster_shared {{ label="app/shared — device client and app logic (JS, unit-tested against the simulator)"; style=rounded; color="#2f6db5";
   cli [label="StClient\\nWebSocket API v1: id → reply, state stream (seq),\\nreconnect + hello resume, typed models"];
   disc [label="Discovery\\nlast head · mDNS · Alpaca UDP 32227 · 192.168.4.1\\n→ /startracker/v1/info"];
   upd [label="Update\\n.stfw check + upload with progress"];
   jobs [label="Job planner\\npanorama grid, path-lapse keys,\\nastro dither, Holy Grail ramp"];
   cat [label="Catalogue + ephemeris\\nstars8 · Messier/NGC · planets · Sun · Moon"];
 }}
 subgraph cluster_native {{ label="Native shell (the thin part)"; style=rounded; color="#b5602f";
   and [label="Android: Java app + WebView\\nUSB host (Sony PTP), BLE, UDP/mDNS,\\nforeground service + wake/Wi-Fi locks, files" fillcolor="#fbeee4"];
   win [label="Windows: Tauri 2 window + Python 3.13 backend\\nWPD (Sony PTP), BLE (bleak), UDP/mDNS,\\nASTAP, files" fillcolor="#fbeee4"];
   reuse [label="Reused from Benro-Polaris-Controller (D12)\\nSony camera + live view · Holy Grail · astro · trails · HDR\\nfocus stack · panorama · plate solver · gallery · shot log"];
 }}
 head [label="Star Tracker head (or the simulator)\\nws://head/ws/v1 · POST /startracker/v1/op\\nPOST /api/update · Alpaca :32323 · BLE GATT" shape=box3d fillcolor="#fff8dc"];
 cam [label="Sony camera\\nUSB-C (PTP / PC Remote)\\nor the head's shutter port" shape=box3d fillcolor="#fff8dc"];
 store -> cli [dir=both]; store -> disc; store -> upd; store -> jobs; scr -> cat;
 cli -> head [label="WebSocket JSON" color="#2f6db5" penwidth=1.6];
 upd -> head [label="HTTP POST"];
 disc -> and [label="bridge" style=dashed]; disc -> win [label="bridge" style=dashed];
 jobs -> reuse [label="camera jobs" style=dashed];
 and -> reuse [dir=none style=dotted]; win -> reuse [dir=none style=dotted];
 reuse -> cam [label="USB"]; reuse -> head [label="job.ack (HTTP op)" style=dashed];
 and -> head [label="BLE set-up" style=dashed];
}}""",

"06-connection-states": f"""
digraph G {{ {BASE} rankdir=LR; nodesep=0.35;
 off [label="Offline\\n(no head chosen)"]; find [label="Finding\\nlast · mDNS · UDP · AP"];
 conn [label="Connecting\\nWebSocket open"]; hello [label="Hello\\nversions, caps, seq, job"];
 live [label="Live\\nstate 5/s, requests by id" fillcolor="#e3ecf9"]; rec [label="Reconnecting\\n1 · 2 · 5 · 5 … s" fillcolor="#fbeee4"];
 off -> find [label="Connect"]; find -> conn [label="head found"]; find -> off [label="nothing found\\n(offer AP / BLE set-up)"];
 conn -> hello [label="open"]; hello -> live [label="ok"]; hello -> off [label="api too old"];
 live -> rec [label="close, error, or\\n2 s without a state event"]; rec -> conn [label="retry"];
 rec -> find [label="5 failures:\\nlook again (IP may\\nhave changed)"];
 live -> off [label="Disconnect"];
}}""",

"06-job-coordination": f"""
digraph G {{ {BASE} rankdir=LR; nodesep=0.3; ranksep=0.45;
 node [width=1.6];
 subgraph cluster_a {{ label="Shutter-port job (runs on the head alone)"; style=rounded; color="#2f6db5";
   a1 [label="app: job.start\\n{{type, shutter:\\"port\\", …}}"]; a2 [label="head: move to frame n\\n(slew, settle)"];
   a3 [label="head: fire shutter port\\nexposure_s"]; a4 [label="head: next frame\\nor done"];
   a1 -> a2 -> a3 -> a4; a4 -> a2 [label="n+1"];
   a5 [label="phone sleeps / Wi-Fi lost:\\njob carries on;\\napp catches up with hello" shape=note fillcolor="#fff8dc"];
 }}
 subgraph cluster_b {{ label="USB-camera job (head moves, app shoots)"; style=rounded; color="#b5602f";
   b1 [label="app: job.start\\n{{type, shutter:\\"app\\", ack_timeout_s}}"]; b2 [label="head: move to frame n,\\nsettle, state frame_ready"];
   b3 [label="app (native camera code):\\nexpose, download, log"]; b4 [label="app: job.ack {{frame:n}}\\n(HTTP op, works with\\nthe screen off)"];
   b1 -> b2 -> b3 -> b4 -> b2;
   b5 [label="no ack within ack_timeout_s:\\nhead pauses, keeps tracking,\\nnever moves on blind" shape=note fillcolor="#fff8dc"];
   b2 -> b5 [style=dashed];
 }}
}}""",

"06-discovery": f"""
digraph G {{ {BASE} rankdir=TB; nodesep=0.3; ranksep=0.3;
 s [label="Connect pressed (or app start)" shape=oval];
 l [label="1. Last head used\\nGET http://<last ip>/startracker/v1/info (1 s)"];
 m [label="2. mDNS\\n_startracker._tcp.local (2 s)"];
 u [label="3. Alpaca discovery\\nbroadcast alpacadiscovery1 → UDP 32227 (2 s)\\nthen GET http://<ip>:<AlpacaPort>/startracker/v1/info"];
 ap [label="4. Head's access point\\nphone on StarTracker-XXXX → 192.168.4.1"];
 b [label="5. Nothing: First set-up\\nBLE pairing (code on the OLED) → send your Wi-Fi\\nor join the head's access point"];
 ok [label="info → ws://<ip>:<ws_port><ws_path>\\nremember as last head" fillcolor="#e3ecf9"];
 s -> l; l -> ok [label="answers"]; l -> m [label="no"]; m -> ok; m -> u [label="none"]; u -> ok; u -> ap [label="none"]; ap -> ok; ap -> b [label="none"];
}}""",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, src in DIAGRAMS.items():
        for fmt in ("svg", "png"):
            args = ["dot", f"-T{fmt}", "-o", str(OUT / f"{name}.{fmt}")]
            if fmt == "png":
                args.insert(1, "-Gdpi=150")
            subprocess.run(args, input=src.encode(), check=True)
        print("wrote", name)


if __name__ == "__main__":
    main()
