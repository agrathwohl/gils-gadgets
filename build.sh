#!/usr/bin/env bash
# Build the SD card image that gadgets.nix describes. The image goes to result/sd-image/
set -euo pipefail
cd "$(dirname "$0")"
# "path:" builds from all the files in this folder, also the ones that git ignores
# (the soundfont and your own voice recordings)
nix build "path:.#nixosConfigurations.gils-gadgets.config.system.build.sdImage" \
  --extra-substituters "https://nixos-raspberrypi.cachix.org" \
  --extra-trusted-public-keys "nixos-raspberrypi.cachix.org-1:4iMO9LXa8BqhU+Rpg6LQKiGa2lsNh/j2oiYLNOQ5sPI="
echo "Done. Image: $(echo result/sd-image/*.img.zst)"
