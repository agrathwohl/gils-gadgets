# Musical Numbers

Your child picks up a real telephone and presses one number. The phone plays the song for that number. It is a way to call up a favorite song, and to learn the numbers on the way.

```
 ┌───────────┐    Ethernet cable    ┌────────────────┐
 │   phone   │──────────────────────│  Raspberry Pi  │
 │ press  1  │◀── song 1 plays ─────│  songs/1.mp3   │
 └───────────┘                      └────────────────┘
```

## How it plays

- Pick up the handset and press a number from **1** to **9**. The song for that number plays in the handset.
- Hang up to stop the song. When the song ends, the call ends.
- A number without a song does not connect.

The Pi runs [FreeSWITCH](https://github.com/signalwire/freeswitch), a telephone server, which answers the call and plays the song. The phone and the Pi talk over one cable. There is no router and no internet.

## The songs

Put one file for each number in `musical-numbers/songs/`. The file name is the number:

```
musical-numbers/songs/1.mp3
musical-numbers/songs/2.flac
musical-numbers/songs/3.wav
```

- Any audio format that [FFmpeg](https://ffmpeg.org/) can read works. The build converts each song to the phone format (16 kHz, mono).
- Use one file for each number. You do not need all nine.
- Git ignores the `songs/` folder, but `./build.sh` puts the songs on the SD card. If the folder has no songs, the build stops and tells you.

To change the songs later, see [Customize](../CUSTOMIZE.md#the-musical-numbers).

## The phone

You need a desk phone that speaks SIP (a "VoIP phone" or "IP phone") and has an Ethernet port. See the [hardware guide](../HARDWARE.md#phone-musical-numbers).

1. **Set up the phone's account.** Most SIP phones have a settings web page. It is easiest to set the account while the phone is still on your home network, and then move its cable to the Pi. Use these values:

   | Setting | Value |
   | --- | --- |
   | SIP server (registrar, domain, proxy) | `10.42.0.1` |
   | Port and transport | `5060`, UDP |
   | User name (and auth ID) | `gil` |
   | Password | `gil` |

   The user name and the password come from `phone` in [`gadgets.nix`](../gadgets.nix). Change them there if you like.

2. **Let one number dial at once.** Many phones wait a few seconds after a number, in case more numbers come. In the phone's settings, set the dial plan (or digit map) so that one digit from 1 to 9 dials at once, for example `[1-9]`. Otherwise your child must press the dial key after the number.

3. **Connect the phone to the Pi.** Plug an Ethernet cable from the phone's network port (often marked LAN or NET) into the Pi's Ethernet port. Give the phone its own power: its power adapter, or a PoE injector. The Pi cannot power the phone.

The Pi has the address `10.42.0.1` on its Ethernet port and gives the phone an address from `10.42.0.100` to `10.42.0.199`. The phone shows that it is registered, and then it is ready.

## On the Raspberry Pi

- The musical numbers run in the background. They need no screen and no keyboard, and they work alone or with the other gadgets.
- The songs play in the phone, not on the Pi's speakers. So the musical numbers work with the other gadgets on a Pi 5 too.
- With this gadget, the Pi's Ethernet port belongs to the phone. The Pi does not join your home network over Ethernet.
