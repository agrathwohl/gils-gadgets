# Build guide

You build the SD card image on a Linux computer or a Mac with [Nix](https://nixos.org/), then write it to a microSD card. Nix gets everything the Pi needs from the files in this repository, so the same files always give the same card.

Gil's images are built on NixOS. On a Mac, do the steps in [On a Mac](#on-a-mac) instead of steps 1 to 4. We did not test the Mac steps yet.

## What you need

- A Linux computer, normal PC (x86_64) or ARM (aarch64), or a Mac with Apple Silicon. You need at least 15 GB of free disk space. A Pi 4 build with the typing game and the musical keyboard keeps about 7 GB in the Nix store, and it needs about 5.5 GB more while it makes the image.
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

## On a Mac

The Pi image is Linux, so a Mac needs a Linux computer to build it. [nix-darwin](https://github.com/nix-darwin/nix-darwin) can run one for you: a small NixOS virtual machine, the *Linux builder*, that Nix sends the Linux work to ([nixcademy](https://nixcademy.com/posts/macos-linux-builder/), [NixOS Wiki](https://wiki.nixos.org/wiki/Nix-darwin)).

Use a Mac with Apple Silicon (M1 or newer). There, the Linux builder is ARM like the Pi, so it builds the image at full speed. On an Intel Mac the Linux builder is x86_64 ([nixcademy](https://nixcademy.com/posts/macos-linux-builder/)), and this guide does not cover that case.

1. **Install Nix** ([nixos.org/download](https://nixos.org/download/)):

   ```sh
   curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install | sh
   ```

2. **Install nix-darwin.** Follow the steps in its [README](https://github.com/nix-darwin/nix-darwin#readme). They make a configuration in `/etc/nix-darwin` and then run `sudo nix run nix-darwin/master#darwin-rebuild -- switch`.

3. **Turn on flakes, the binary cache and the Linux builder.** Add this to your nix-darwin configuration, then run `sudo darwin-rebuild switch`:

   ```nix
   nix.settings.experimental-features = [ "nix-command" "flakes" ];
   nix.settings.trusted-users = [ "@admin" ];
   nix.settings.extra-substituters = [ "https://nixos-raspberrypi.cachix.org" ];
   nix.settings.extra-trusted-public-keys = [ "nixos-raspberrypi.cachix.org-1:4iMO9LXa8BqhU+Rpg6LQKiGa2lsNh/j2oiYLNOQ5sPI=" ];
   nix.linux-builder.enable = true;
   ```

   `trusted-users` lets your user reach the Linux builder ([nixcademy](https://nixcademy.com/posts/macos-linux-builder/)).

4. **Check the Linux builder.** This command builds a tiny Linux program. It must print `aarch64`:

   ```sh
   cat "$(nix build --impure --no-link --print-out-paths --expr '(builtins.getFlake "nixpkgs").legacyPackages.aarch64-linux.runCommand "check" {} "uname -m > $out"')"
   ```

5. **If the build runs out of space or memory,** give the Linux builder more. By default it has 1 CPU core, 3 GB of memory and a 20 GB disk ([nixcademy](https://nixcademy.com/posts/macos-linux-builder/)). Add this, then run `sudo darwin-rebuild switch` again. First use the builder once with its default settings, as the nix-darwin docs advise ([NixOS Wiki](https://wiki.nixos.org/wiki/Nix-darwin)).

   ```nix
   nix.linux-builder.config.virtualisation = {
     darwin-builder.diskSize = 40 * 1024;
     darwin-builder.memorySize = 8 * 1024;
     cores = 6;
   };
   ```

Then go on with step 5. `./build.sh` works the same on a Mac: Nix sends the Linux work to the Linux builder.

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
  gadgets = [ "typing-game" "musical-keyboard" "musical-numbers" ];  # any of them
  screen = "1024x600";                             # or null for a monitor or TV
  midiKeyboard = "MPK mini";                       # see `aconnect -l`
  phone = { user = "gil"; password = "gil"; };     # the SIP account of the phone
}
```

The [hardware guide](HARDWARE.md) explains `screen` and `midiKeyboard`. The [musical numbers](musical-numbers/README.md#the-phone) explain `phone`. On a Pi 5, choose the typing game or the musical keyboard, not both ([why](HARDWARE.md#sound)).

## 7. Add your own files

Some files are not in git. You add them yourself:

- **Musical keyboard:** the soundfont. See [The soundfont](musical-keyboard/README.md#the-soundfont). The build stops and tells you if it is not there.
- **Musical numbers:** your songs, in `musical-numbers/songs/`. See [The songs](musical-numbers/README.md#the-songs). The build stops and tells you if there are none.
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

**On a Mac:**

1. Run `diskutil list`, put the SD card in, and run `diskutil list` again. The new disk is your SD card, for example `/dev/disk4`. Check that its size matches the card.
2. Unmount it and write the image. Change `disk4` to your card (`rdisk4` is the same disk, and it is faster):

   ```sh
   diskutil unmountDisk /dev/disk4
   nix shell nixpkgs#zstd -c zstdcat result/sd-image/*.img.zst | sudo dd of=/dev/rdisk4 bs=4m
   ```

3. Run `diskutil eject /dev/disk4`, then take out the card.

## 10. Start the Pi

Put the card in the Pi and connect everything. See [Connect it](HARDWARE.md#connect-it).

## Change something later

Change the files, run `./build.sh` again, and write the new image to the card. The new card replaces everything on the old one.
