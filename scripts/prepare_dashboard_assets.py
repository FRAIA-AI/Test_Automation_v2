"""Prepare the dashboard HTML and static assets for GitHub Pages."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

SOURCE = Path("dashboard")
PUBLIC = Path("public")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    html = (SOURCE / "index.html").read_text(encoding="utf-8")

    # three@0.179 no longer exposes the classic global THREE build used by
    # this dashboard. r128 still provides the compatible global build.
    html = html.replace(
        "https://cdn.jsdelivr.net/npm/three@0.179.1/build/three.min.js",
        "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js",
    )

    # Add the dashboard favicon when present.
    if "rel=\"icon\"" not in html and "rel='icon'" not in html:
        html = html.replace(
            "<title>People's Clinic Monitoring</title>",
            "<title>People's Clinic Monitoring</title>\n"
            "  <link rel=\"icon\" type=\"image/png\" href=\"favicon.png\">",
        )

    # Replace the generated WebAudio ambient tones with the uploaded MP3.
    music_pattern = re.compile(
        r"\s*let audioCtx, master, playing=false, timers=\[\];.*?"
        r"\$\('volume'\)\.addEventListener\('input',e=>\{if\(master\)master\.gain\.value=Number\(e\.target\.value\)\}\);",
        re.DOTALL,
    )
    music_replacement = r'''
    const ambientAudio = new Audio('bg-music.mp3');
    ambientAudio.loop = true;
    ambientAudio.preload = 'metadata';
    ambientAudio.volume = Number($('volume').value);
    let playing = false;

    async function startMusic(){
      try {
        await ambientAudio.play();
        playing = true;
        $('music-dock').classList.add('playing');
        $('music').textContent = 'Ⅱ';
      } catch (error) {
        toast(`Music could not start: ${error.message}`);
      }
    }
    function stopMusic(){
      ambientAudio.pause();
      playing = false;
      $('music-dock').classList.remove('playing');
      $('music').textContent = '♪';
    }
    $('music').addEventListener('click',()=>playing?stopMusic():startMusic());
    $('volume').addEventListener('input',e=>{ambientAudio.volume=Number(e.target.value)});'''
    html, replacements = music_pattern.subn(music_replacement, html, count=1)
    if replacements != 1:
        print("WARNING: music block was not replaced; keeping original dashboard audio code")

    # Make the Three.js background optional so a CDN problem can never block
    # status data, charts, or evidence from loading.
    html = html.replace(
        "(function initThree(){ const canvas=$('three-bg'), renderer=new THREE.WebGLRenderer",
        "(function initThree(){ if (typeof THREE === 'undefined') { console.warn('Three.js unavailable; continuing without animated background'); return; } const canvas=$('three-bg'), renderer=new THREE.WebGLRenderer",
    )

    (PUBLIC / "index.html").write_text(html, encoding="utf-8")

    for asset in ("favicon.png", "favicon.webp", "bg-music.mp3"):
        source = SOURCE / asset
        if source.is_file():
            shutil.copy2(source, PUBLIC / source.name)
            print(f"Copied {source} -> {PUBLIC / source.name}")

    (PUBLIC / ".nojekyll").touch()
    print("Dashboard HTML and static assets prepared.")


if __name__ == "__main__":
    main()
