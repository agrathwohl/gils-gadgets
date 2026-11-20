# What goes on the SD card. Change this file, then run ./build.sh
{
  # Which Raspberry Pi: "rpi4" or "rpi5"
  board = "rpi4";

  # Which gadgets: any of "typing-game", "musical-keyboard", "musical-numbers", "screen-saver" (Pi 5 only),
  # "story" (it needs a USB microphone)
  gadgets = [ "typing-game" "musical-keyboard" "musical-numbers" ];

  # Screen mode to force at boot, for a display that does not tell the Pi its size in time
  # (a 7" 1024x600 panel, for example). null: use the mode that the display asks for.
  screen = "1024x600";

  # The name of the MIDI keyboard for the musical keyboard (see `aconnect -l` when it is plugged in)
  midiKeyboard = "MPK mini";

  # The SIP account that the phone uses for the musical numbers. Only the phone on the cable can reach it.
  phone = { user = "gil"; password = "gil"; };

  # The time zone for the screen saver times, from the tz database, for example "Europe/Berlin"
  timeZone = "America/Chicago";
}
