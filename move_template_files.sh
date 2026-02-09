#!/bin/sh

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync required, but not installed!"
  exit 1
else
  rsync -avh pdi-nomad-plugin-rheed/ .
  rm -rfv pdi-nomad-plugin-rheed
fi
