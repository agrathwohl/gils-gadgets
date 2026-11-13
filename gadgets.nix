# What goes on the SD card. Change this file, then run ./build.sh
{
  # Which Raspberry Pi: "rpi4" or "rpi5"
  board = "rpi4";

  # Which gadgets: "typing-game", "musical-keyboard", or both
  gadgets = [ "typing-game" "musical-keyboard" ];

  # Screen mode to force at boot, for a display that does not tell the Pi its size in time
  # (a 7" 1024x600 panel, for example). null: use the mode that the display asks for.
  screen = "1024x600";

  # The name of the MIDI keyboard for the musical keyboard (see `aconnect -l` when it is plugged in)
  midiKeyboard = "MPK mini";
}
