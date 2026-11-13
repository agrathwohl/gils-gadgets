# Build guide

You build the SD card image on a Linux computer with [Nix](https://nixos.org/), then write it to a microSD card. Nix gets everything the Pi needs from the files in this repository, so the same files always give the same card.

These steps are for Linux. We did not test other systems.

## What you need

- A Linux computer, normal PC (x86_64) or ARM (aarch64), with at least 15 GB of free disk space. A Pi 4 build with both gadgets keeps about 7 GB in the Nix store, and it needs about 5.5 GB more while it makes the image.
- A microSD card and a card reader.
- The parts in the [hardware guide](HARDWARE.md).

## 1. Install Nix

**NixOS:** Nix is already there. Go to step 2.

**Other Linux:** run the official installer ([nixos.org/download](https://nixos.org/download/)):

```sh
curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install | sh -s -- --daemon
```

Open a new terminal, then check that it works:

```sh
nix --version
```

## 2. Turn on flakes

This build uses Nix *flakes*.

**Other Linux:** add this line to `/etc/nix/nix.conf`, then run `sudo systemctl restart nix-daemon`:

```
experimental-features = nix-command flakes
```

**NixOS:** add this to your configuration, then run `sudo nixos-rebuild switch`:

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

Source: [NixOS Wiki: Flakes](https://wiki.nixos.org/wiki/Flakes).

## 3. Use the Raspberry Pi binary cache

The [nixos-raspberrypi](https://github.com/nvmd/nixos-raspberrypi) project keeps ready-made Raspberry Pi kernels and firmware in a binary cache. With the cache, your computer does not have to compile them.

`build.sh` asks Nix to use the cache, but Nix ignores that request unless you are a trusted user ([Nix manual: substituters](https://nix.dev/manual/nix/latest/command-ref/conf-file.html#conf-substituters)). So add the cache to the system settings.

**Other Linux:** add these lines to `/etc/nix/nix.conf`, then run `sudo systemctl restart nix-daemon`:

```
extra-substituters = https://nixos-raspberrypi.cachix.org
extra-trusted-public-keys = nixos-raspberrypi.cachix.org-1:4iMO9LXa8BqhU+Rpg6LQKiGa2lsNh/j2oiYLNOQ5sPI=
```

**NixOS:** add this to your configuration, then run `sudo nixos-rebuild switch`:

```nix
nix.settings.extra-substituters = [ "https://nixos-raspberrypi.cachix.org" ];
nix.settings.extra-trusted-public-keys = [ "nixos-raspberrypi.cachix.org-1:4iMO9LXa8BqhU+Rpg6LQKiGa2lsNh/j2oiYLNOQ5sPI=" ];
```

## 4. Let your computer build for the Pi

The Pi uses ARM (`aarch64-linux`). **If your computer is ARM Linux, skip this step.** A normal PC (x86_64) needs QEMU to run ARM programs during the build.

**NixOS:** add this to your configuration, then run `sudo nixos-rebuild switch`:

```nix
boot.binfmt.emulatedSystems = [ "aarch64-linux" ];
```

**Debian or Ubuntu:** install QEMU, then add two lines to `/etc/nix/nix.conf` and restart Nix ([NixOS Discourse](https://discourse.nixos.org/t/how-to-configure-qemu-binfmt-wrapper-on-a-non-nixos-machine/7879)):

```sh
sudo apt install binfmt-support qemu-user-static
```

```
extra-platforms = aarch64-linux
extra-sandbox-paths = /usr/bin/qemu-aarch64-static
```

```sh
sudo systemctl restart nix-daemon
```

**Check it.** This command runs a small ARM program. It must print `Hello, world!`:

```sh
nix run nixpkgs#legacyPackages.aarch64-linux.hello
```

## 5. Get the code

```sh
git clone https://github.com/agrathwohl/gils-gadgets.git
cd gils-gadgets
```

## 6. Choose your Pi and your gadgets

Open [`gadgets.nix`](gadgets.nix) and change it for your hardware:

```nix
{
  board = "rpi4";                                  # or "rpi5"
  gadgets = [ "typing-game" "musical-keyboard" ];  # one or both (only one on a Pi 5)
  screen = "1024x600";                             # or null for a monitor or TV
  midiKeyboard = "MPK mini";                       # see `aconnect -l`
}
```

The [hardware guide](HARDWARE.md) explains `screen` and `midiKeyboard`.

## 7. Add your own files

Some files are not in git. You add them yourself:

- **Musical keyboard:** the soundfont. See [The soundfont](musical-keyboard/README.md#the-soundfont). The build stops and tells you if it is not there.
- **Typing game:** your voices, in `typing-game/audio/`. This is optional. Without voices, the game is silent. See [Customize](CUSTOMIZE.md).

`build.sh` builds from all the files in the folder, so these files go on the card even though git ignores them.

## 8. Build

```sh
./build.sh
```

The first build downloads a lot and takes a while. When it is done, the image is in `result/sd-image/` and its name ends in `.img.zst`.

If the build stops with an error about `aarch64-linux`, do step 4 again.

## 9. Write the SD card

> **Careful:** `dd` erases the device that you give it. If you give it the wrong device, you lose the data on that disk.

1. Run `lsblk`.
2. Put the SD card in the card reader.
3. Run `lsblk` again. The new disk is your SD card, for example `/dev/sdb` or `/dev/mmcblk0`. Check that its size matches the card.
4. Write the image. Change `/dev/sdX` to your card:

   ```sh
   nix shell nixpkgs#zstd -c zstdcat result/sd-image/*.img.zst | sudo dd of=/dev/sdX bs=4M conv=fsync status=progress
   ```

5. Run `sync`, then take out the card.

## 10. Start the Pi

Put the card in the Pi and connect everything. See [Connect it](HARDWARE.md#connect-it).

## Change something later

Change the files, run `./build.sh` again, and write the new image to the card. The new card replaces everything on the old one.
