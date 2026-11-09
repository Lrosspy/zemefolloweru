#!/usr/bin/env python3
"""udelej_reel.py - z jedné šablony (JSON) složí hotový reel 1080x1920: záběry + hlas + hudba se ztišením pod hlasem
+ zvukové efekty + titulky vypálené přes ffmpeg (libass). Potřebuje jen Python 3 a ffmpeg.

    python udelej_reel.py sablony/nova_budova.json
    python udelej_reel.py muj_reel.json --nahled        # rychlý render v nízké kvalitě na kontrolu
    python udelej_reel.py muj_reel.json --auto-titulky  # titulky z hlasu (pip install faster-whisper)

Cesty v JSON se hledají nejdřív vedle JSON souboru, pak ve složce kitu (hudba/, zvuky/, ...).
Titulky: {y}text{/y} = žlutě. Řádky se zalomí samy, \\n = vlastní zalomení. Emoji ffmpeg neumí - vynechávají se.
"""
import json, os, re, shutil, subprocess, sys, tempfile

KIT = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

def najdi(cesta, base):
    if not cesta: return None
    for d in (base, KIT, os.getcwd()):
        p = os.path.join(d, cesta)
        if os.path.exists(p): return os.path.abspath(p)
    sys.exit(f"Soubor nenalezen: {cesta}")

def delka(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True).stdout.strip()
    return float(o or 0)

# ---------- titulky (ASS) ----------
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
def ass_cas(s):
    s = max(0, s); h = int(s // 3600); m = int(s % 3600 // 60); return f"{h}:{m:02d}:{s % 60:05.2f}"
def barvy(txt, zluta):
    txt = txt.replace("{y}", "{\\c&H" + zluta + "&}").replace("{/y}", "{\\c&HFFFFFF&}")
    return txt
def zalom(txt, maxz):
    out = []
    for odst in txt.split("\\n"):
        radek = ""
        for slovo in odst.split():
            cist = re.sub(r"\{/?y\}", "", radek + " " + slovo).strip()
            if radek and len(cist) > maxz: out.append(radek); radek = slovo
            else: radek = (radek + " " + slovo).strip()
        if radek: out.append(radek)
    return out
def velka(txt, caps):  # VELKÁ PÍSMENA jako v minulých reelech, @jména zůstanou malá
    if not caps: return txt
    return re.sub(r"(@[\w.]+)|(\\n)|([^@{}\\]+)|(\{/?y\})",
                  lambda m: m.group(1) or m.group(2) or m.group(4) or m.group(3).upper(), txt)
def hex_bgr(h):  # "#ffd23a" -> "3AD2FF"
    h = h.lstrip("#"); return (h[4:6] + h[2:4] + h[0:2]).upper()

def udelej_ass(titulky, styl, cesta):
    vel = styl.get("velikost", 134); y0 = styl.get("pozice_y", 300); maxz = styl.get("znaku_na_radek", 13); caps = styl.get("velka_pismena", True)
    zl = hex_bgr(styl.get("zvyrazneni", "#ffd23a")); pod_vel = styl.get("velikost_pod", 60)
    font = styl.get("font", "Inter Display Black")
    hl = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Velky,{font},{vel},&H00FFFFFF,&H00FFFFFF,&H002A0C12,&H8C000000,-1,0,0,0,100,100,-1,0,1,7,5,8,50,50,0,1
Style: Pod,{font},{pod_vel},&H00FFFFFF,&H00FFFFFF,&H302A0C12,&H302A0C12,-1,0,0,0,100,100,0,0,3,16,0,8,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    anim = "{\\fad(70,90)\\fscx82\\fscy82\\t(0,130,\\fscx100\\fscy100)}"
    for t in titulky:
        od, do = float(t["od"]), float(t["do"]); y = float(t.get("y", y0))
        if t.get("text"):
            rad = zalom(velka(EMOJI.sub("", t["text"]).strip(), caps), maxz)
            nejdelsi = max(len(re.sub(r"\{/?y\}", "", r)) for r in rad)
            fs = vel * min(1.0, maxz * 0.95 / nejdelsi)  # dlouhé slovo (třeba @jméno) se zmenší, aby nepřeteklo
            txt = "\\N".join(barvy(r, zl) for r in rad)
            ev.append(f"Dialogue: 1,{ass_cas(od)},{ass_cas(do)},Velky,,0,0,0,,{{\\an8\\pos({W//2},{y:.0f})\\fs{fs:.0f}}}{anim}{txt}")
            y += len(rad) * fs * 1.02 + 34
        if t.get("pod"):
            rad = zalom(EMOJI.sub("", t["pod"]).strip(), styl.get("znaku_pod", 32))  # dlouhý titulek se zalomí
            txt = "\\N".join(barvy(r, zl) for r in rad)
            ev.append(f"Dialogue: 0,{ass_cas(od + .12)},{ass_cas(do)},Pod,,0,0,0,,{{\\an8\\pos({W//2},{y:.0f})}}{anim}{txt}")
    with open(cesta, "w", encoding="utf-8") as f: f.write(hl + "\n".join(ev) + "\n")

def auto_titulky(hlas, start, slov=3):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Pro --auto-titulky: pip install faster-whisper")
    m = WhisperModel("small", compute_type="int8")
    segs, _ = m.transcribe(hlas, language="cs", word_timestamps=True)
    words = [w for s in segs for w in s.words]
    out = []
    for i in range(0, len(words), slov):
        g = words[i:i + slov]
        out.append({"od": start + g[0].start, "do": start + g[-1].end + .05, "text": "".join(w.word for w in g).strip()})
    for a, b in zip(out, out[1:]): a["do"] = min(a["do"] + .25, b["od"])
    return out

# ---------- hlavní složení ----------
def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    jpath = os.path.abspath(a[0]); base = os.path.dirname(jpath)
    S = json.load(open(jpath, encoding="utf-8"))
    nahled = "--nahled" in a
    fps = S.get("fps", 30)
    tmp = tempfile.mkdtemp(prefix="reel_")
    try:
        # 1) video: záběry za sebou, každý oříznutý a naplněný na 1080x1920
        vin, vf, cas = [], [], 0.0
        for i, z in enumerate(S["zabery"]):
            p = najdi(z["soubor"], base); od = float(z.get("od", 0)); do = z.get("do")
            do = float(do) if do is not None else delka(p); rych = float(z.get("rychlost", 1))
            vin += ["-ss", f"{od}", "-t", f"{do - od}", "-i", p]
            zoom = float(z.get("zoom", 1))
            vf.append(f"[{i}:v]setpts=(PTS-STARTPTS)/{rych},scale={int(W*zoom)}:{int(H*zoom)}:force_original_aspect_ratio=increase,"
                      f"crop={W}:{H},fps={fps},setsar=1,format=yuv420p[v{i}]")
            cas += (do - od) / rych
        n = len(S["zabery"])
        D = float(S.get("delka") or cas)
        vf.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,trim=0:{D},setpts=PTS-STARTPTS[vcat]")

        # 2) titulky
        tit = list(S.get("titulky", []))
        hl = S.get("hlas") or {}
        hlas = najdi(hl.get("soubor"), base) if hl.get("soubor") else None
        if "--auto-titulky" in a and hlas:
            tit = auto_titulky(hlas, float(hl.get("start", 0))) + [t for t in tit if t.get("ponechat")]
        if tit:
            udelej_ass(tit, S.get("styl", {}), os.path.join(tmp, "t.ass"))
            fontdir = os.path.join(KIT, "fonty").replace("\\", "/").replace(":", "\\:")
            vf.append(f"[vcat]subtitles=t.ass:fontsdir='{fontdir}'[vout]")
        else:
            vf.append("[vcat]null[vout]")

        # 3) zvuk: hlas, hudba (ztišená pod hlasem), efekty
        ain, af, mix = [], [], []
        k = n
        if hlas:
            ain += ["-i", hlas]
            f = f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo"
            if hl.get("zkratit_pauzy"):
                f += ",silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.22:stop_threshold=-42dB:stop_silence=0.12"
            f += f",volume={hl.get('hlasitost', 1.0)},adelay={int(float(hl.get('start', 0))*1000)}:all=1,apad"
            af.append(f + ",asplit=2[hlas][sc]"); mix.append("[hlas]"); k += 1
        hu = S.get("hudba") or {}
        if hu.get("soubor"):
            ain += ["-stream_loop", "-1", "-i", najdi(hu["soubor"], base)]
            f = (f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,atrim={hu.get('od', 0)},asetpts=PTS-STARTPTS,"
                 f"volume={hu.get('hlasitost', 0.35)},afade=t=in:d=0.3,afade=t=out:st={max(0, D-1.2)}:d=1.2")
            if hlas and hu.get("ztisit_pod_hlasem", True):
                af.append(f + "[hud0]"); af.append("[hud0][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[hud]")
            else:
                af.append(f + "[hud]")
                if hlas: af.append("[sc]anullsink")
            mix.append("[hud]"); k += 1
        elif hlas:
            af.append("[sc]anullsink")
        for j, z in enumerate(S.get("zvuky", [])):
            ain += ["-i", najdi(z["soubor"], base)]
            af.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,volume={z.get('hlasitost', 0.8)},"
                      f"adelay={int(float(z['cas'])*1000)}:all=1[z{j}]")
            mix.append(f"[z{j}]"); k += 1
        if mix:
            af.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{D},"
                      "alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
        graf = ";".join(vf + af)
        out = os.path.abspath(os.path.join(base, S.get("vystup", "reel.mp4")))
        if nahled: out = out.replace(".mp4", "_nahled.mp4")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"] + vin + ain + [
            "-filter_complex", graf, "-map", "[vout]"] + (["-map", "[aout]"] if mix else []) + [
            "-t", f"{D}", "-c:v", "libx264", "-preset", "ultrafast" if nahled else "veryfast",
            "-crf", "30" if nahled else "18", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
        subprocess.run(cmd, cwd=tmp, check=True)
        print(f"Hotovo: {out}  ({D:.1f} s)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
