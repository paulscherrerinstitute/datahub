#!/bin/sh

export DAQBUF_DEFAULT_COMPRESSION=gzip

exec /usr/bin/python3 -m datahub.main "$@"


