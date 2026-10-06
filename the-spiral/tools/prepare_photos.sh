#!/bin/zsh
# Turn full-size photos into mirror-ready copies (macOS only; uses built-in `sips`).
#
#   1. put your originals (JPG, PNG, HEIC...) in  photos_originals/
#   2. run:  zsh tools/prepare_photos.sh
#   3. re-run the build line in TouchDesigner's Textport
#
# Originals are never modified. photos/ is rebuilt as 1600px JPGs, which keeps
# TouchDesigner light (full-size phone photos are ~5700px and ~6MB each).
set -e
cd "$(dirname "$0")/.."
mkdir -p photos
setopt null_glob extended_glob
src=(photos_originals/*.(#i)(jpg|jpeg|png|heic|tif|tiff|webp))
if (( ${#src} == 0 )); then
  echo "No images in photos_originals/"; exit 1
fi
rm -f photos/*.jpg
for f in $src; do
  name="${${f:t}:r}"
  sips -Z 1600 -s format jpeg -s formatOptions 82 "$f" --out "photos/$name.jpg" >/dev/null
done
echo "Prepared ${#src} photos in photos/ (the build uses up to 60, alphabetically)."
