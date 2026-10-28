#!/usr/bin/env bash
# demo/cast/render.sh transcript.txt out-basename "title"  ->  out.mp4 and out.gif
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
python3 "$here/make_cast.py" "$1" "$tmp/cast.html" "${3:-a séance}"
video="$(node "$here/record.js" "$tmp/cast.html" "$tmp" | tail -n 1)"
ffmpeg -loglevel error -y -i "$video" -ss 0.4 -c:v libx264 -pix_fmt yuv420p -movflags +faststart -crf 24 "$2.mp4"
ffmpeg -loglevel error -y -i "$video" -ss 0.4 -vf "fps=12,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" "$2.gif"
ls -la "$2.mp4" "$2.gif"
