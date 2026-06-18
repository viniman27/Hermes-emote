Drop your own square PNG portraits here, one folder per state:

  idle/    idle.png, idle_blink.png        (blink alternates these two)
  think/   think.png, think_hard.png
  talk/    talk_close.png, talk_small.png, talk_mid.png, talk_wide.png
  read/    read1.png, read2.png            (two frames -> animates)
  write/   write1.png, write2.png
  tool/    tool1.png, tool2.png
  failure/ failure1.png, failure2.png
  hi/      hi1.png, hi2.png
  compact/ compact1.png

emotes.json (optional) tunes blink frame, think "hard" frame and talk weights.

No images are shipped with this repo — this is just the folder layout. Point
config.yaml `emote_set` at this set (or make your own folder next to it).
PNG files in these folders are gitignored on purpose.
