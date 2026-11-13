# Hardware guide

Gil's Gadgets run on a Raspberry Pi with a screen, a keyboard and speakers. This guide tells you what to get and how to connect it. Most parts are common, and you can reuse parts you already have.

## What Gil uses

- Raspberry Pi 4 Model B
- 7" HDMI display, 1024x600
- Model M replica keyboard (USB)
- Akai MPK mini (USB MIDI keyboard with drum pads)
- Speakers on the Pi's 3.5 mm jack
- 8 GB microSD card
- Skip Hop Explore & More activity center, used as a play table

See [Gil's setup](#gils-setup) for how it all fits together.

## The parts

### Raspberry Pi

| Board | Status |
| --- | --- |
| Raspberry Pi 4 Model B | Tested on Gil's Pi 4. |
| Raspberry Pi 5 | The image builds, but nobody has tested it on a real Pi 5 yet. Choose one gadget only (see [Sound](#sound)). |

Set `board = "rpi4";` or `board = "rpi5";` in [`gadgets.nix`](gadgets.nix).

### Power supply

Use a good USB-C power supply that is made for your Pi.

- Pi 4: 5 V, at least 3 A ([Raspberry Pi 4 specifications](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)).
- Pi 5: 5 V, 5 A is recommended, for example the Raspberry Pi 27W USB-C Power Supply ([Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/)).

### microSD card

Use a card of 8 GB or more. Gil's 8 GB card works. You also need a card reader for the computer that builds the image.

### Display

Any HDMI display works: a small panel, a computer monitor or a TV.

- The Pi 4 and the Pi 5 have **micro-HDMI** ports, so you need a micro-HDMI to HDMI cable or adapter.
- Use the port marked HDMI0 ([Getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html)). It is the one next to the USB-C power port ([Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=317820)). On a Pi 5, the sound goes there.
- Some small panels do not tell the Pi their size in time at boot. The Pi then uses 1024x768, and the bottom of the screen is cut off. If this happens, set `screen` in [`gadgets.nix`](gadgets.nix) to your panel's size, for example `screen = "1024x600";`. With a monitor or TV, use `screen = null;`.

### Computer keyboard

Use a USB keyboard, with a cable or with a USB receiver. The image does not set up Bluetooth.

Tips for small hands:

- A full-size keyboard with big, clear letters is better than a small one.
- Capital letters on the keys are easiest. The typing game shows capital letters.
- Choose a keyboard that you do not mind getting sticky.

### MIDI keyboard (musical keyboard)

Use a USB MIDI keyboard that works on Linux without a driver. Many are sold as "class compliant". Gil uses an Akai MPK mini, which has piano keys, drum pads and knobs.

- Drum pads must send notes on MIDI channel 10 to play the drum kits. This is the usual drum channel.
- To change the instrument, the keyboard must send a program change.
- Plug the keyboard in, and run `aconnect -l` on a computer to see its name. Put the name in `midiKeyboard` in [`gadgets.nix`](gadgets.nix).

### Sound

The gadgets have no volume control. Set the volume on the speakers, and keep it low for small ears.

| Board | Where the sound goes |
| --- | --- |
| Pi 4 | The 3.5 mm jack ([the "4-pole stereo audio and composite video port"](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)). Use powered speakers or headphones. |
| Pi 5 | HDMI 0: the speakers of the display or TV, or the audio output of the display. The Pi 5 has no 3.5 mm jack ([Introducing Raspberry Pi 5](https://www.raspberrypi.com/news/introducing-raspberry-pi-5/)). HDMI sound plays one program at a time ([Raspberry Pi white paper, page 15](https://pip-assets.raspberrypi.com/categories/1259-audio-camera-and-display/documents/RP-009699-WP-1-Using%20the%20I2S%20peripherals%20on%20Raspberry%20Pi%20SBCs.pdf)), so a Pi 5 card can have only one gadget. |

The Pi 4 has no plug detection on the jack ([checkbox issue #568](https://github.com/canonical/checkbox/issues/568)), so the gadgets work with nothing plugged in. You just do not hear them. USB sound cards are not set up.

### Case and cables

- Use a case. Small fingers and metal pins do not mix.
- Fix the Pi and the cables behind the display or under a desk, so that the cables cannot be pulled.
- Leave only the keyboards where your child can reach them.

### Gil's setup

Gil's gadgets live on a Skip Hop Explore & More activity center, set up in its play table stage.

- The middle of the table has a hollow under the gray round cover. The Pi and all the cables go in there, under the cover. Gil cannot pry at them, and he does not even know that they are there.
- The 7" HDMI panel stands propped in the keyboard. The keyboard is a Model M replica, heavy and sturdy enough to hold the screen.
- On the table, Gil sees only the screen and the keyboards.

Any table or box with a closed space under a lid works the same way. Leave some air around the Pi, because it gets warm.

## Connect it

1. Put the SD card in the Pi.
2. Connect the display to HDMI 0.
3. Connect the computer keyboard and the MIDI keyboard to USB ports.
4. Connect the speakers (Pi 4: the 3.5 mm jack).
5. Connect the power supply last. The Pi starts.

The first boot can take longer than the next ones. Then the first gadget shows on the screen.
