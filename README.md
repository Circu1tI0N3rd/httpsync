# httpsync (WIP)

Mirrors APT repo without rsync such as Raspberry Pi Archive (archive.raspberrypi.org)

No experimental mirrors provided right now.

## Preface

- Most Debian mirrors has `rysnc` as backend for regional mirror syncing, except Raspberry Pi archive
- Raspberry Pi archive uses Apache auto-indexing

## Status

Currently work-in-progress; but most functions are operational and can be experimented with.

Main programme is untested.

## To-do

- 2-stage fetching implementation
- Old files (not updated ones) clean-up
- Cronable
- Compatibility
