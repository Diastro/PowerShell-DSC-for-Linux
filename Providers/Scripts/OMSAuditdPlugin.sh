#!/bin/bash

PATH=/usr/sbin:/sbin:/usr/bin:/bin

AUDISP_DIR=/etc/audisp/plugins.d

AUDISP_CONF=$AUDISP_DIR/auoms.conf

AUOMS_BIN=/opt/microsoft/auoms/bin/auoms
AUOMS_DATA=/var/opt/microsoft/auoms/data

umask 027

get_state () {
    if [ ! -e $AUDISP_CONF ]; then
        echo None
    fi
    echo "$(grep '^ *active *= *' $AUDISP_CONF | tr -d ' ' | cut -d'=' -f2)"
}

test_state () {
    state=$(get_state)
    case $state in
        yes)
            exit 0
            ;;
        no)
            exit 1
            ;;
        *)
            exit 2
            ;;
    esac
}

set_state () {
    # Restart omsagent (/etc/opt/microsoft/omsagent/conf/omsagent.d/auoms.conf has been added or removed)
    /opt/microsoft/omsagent/bin/service_control restart
    if [ $? -ne 0 ]; then
        exit 1
    fi

    state=$(get_state)
    # Exit success if the desired state is already set
    if [ "$state" == "$1" ]; then
        exit 0
    fi

    # Edit the conf file
    sed -i "s/^\( *active *= *\)[enosy]*/\1$1/" $AUDISP_CONF
    if [ $? -ne 0 ]; then
        exit 1
    fi

    # Notify auditd of changes
    service auditd reload
    if [ $? -ne 0 ]; then
        exit 1
    fi

    if [ "$1" = "no" ]; then
        # Make sure auoms has exited
        pgrep -f ${AUOMS_BIN} 2>&1 >/dev/null
        if [ $? -eq 0 ]; then
            # Kill it if it didn't exit
            pkill -KILL -f ${AUOMS_BIN}
        fi

        # Make sure that if we re-enable the plugin, we start fresh
        # Remove all auoms data (queues, etc...)
        rm -f ${AUOMS_DATA}/*
    fi
}

case $1 in
    test)
        test_state
        ;;
    enable)
        set_state "yes"
        ;;
    disable)
        set_state "no"
        ;;
    *)
        echo "Invalid command '$1'"
        exit 3
        ;;
esac
