# Background music

`original_chiptune.wav` is an original sixteen-bar chiptune composed and
synthesized for this DIY game. It is not Nintendo's 1985 music. Regenerate
it from the project directory with `python3 music.py`.

To use your local recording of the 1985 overworld music, place it here as
`overworld.ogg`, `overworld.mp3`, or `overworld.wav`. The game automatically
selects it on the next launch. If multiple files are present, OGG takes
priority, then MP3, then WAV.

Alternatively, pass any local audio path without moving the file:

```sh
./play.command --music "/path/to/your/overworld.mp3"
```

Music loops during play, pauses when the game pauses, stops when Mario dies,
and starts again on restart. Press M to mute or unmute it; sound effects stay
audible. `--no-music` disables only music, and `--no-sound` disables all audio.
