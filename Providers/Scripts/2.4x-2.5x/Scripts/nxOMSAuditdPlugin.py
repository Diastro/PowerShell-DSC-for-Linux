#!/usr/bin/env python
#============================================================================
# Copyright (C) Microsoft Corporation, All rights reserved.
#============================================================================

import os
import sys
import imp
import codecs
import subprocess

protocol = imp.load_source('protocol', '../protocol.py')
nxDSCLog = imp.load_source('nxDSCLog', '../nxDSCLog.py')

LG = nxDSCLog.DSCLog

PLUGIN_CONF = '/etc/audisp/plugins.d/auoms.conf'
OMSAGENT_CONF = '/etc/opt/microsoft/omsagent/conf/omsagent.d/auoms.conf'

OMSAGENT_CONF_TEXT = """
<source>
  @type unix
  path /var/opt/microsoft/auoms/sock/omsagent.sock
</source>

<match oms.api.audit>
  type out_oms_api
  log_level trace
  buffer_chunk_limit 1m
  buffer_type file
  buffer_path /var/opt/microsoft/omsagent/state/out_oms_api_auoms.buffer
  buffer_queue_limit 5
  buffer_queue_full_action drop_oldest_chunk
  flush_interval 20s
  retry_limit 10
  retry_wait 30s
  max_retry_wait 5m
</match>
"""


def Set_Marshall(Ensure):
    if 'value' in dir(Ensure):
        Ensure = Ensure.value
    Ensure = Ensure.encode('ascii', 'ignore')
    return Set(Ensure)

def Test_Marshall(Ensure):
    if 'value' in dir(Ensure):
        Ensure = Ensure.value
    Ensure = Ensure.encode('ascii', 'ignore')
    return Test(Ensure)

def Get_Marshall(Ensure):
    arg_names = list(locals().keys())
    if 'value' in dir(Ensure):
        Ensure = Ensure.value
    Ensure = Ensure.encode('ascii', 'ignore')

    retval = 0
    (retval, Ensure) = Get(Ensure)

    Ensure = protocol.MI_String(Ensure)

    retd = {}
    ld = locals()
    for k in arg_names:
        retd[k] = ld[k]
    return retval, retd

def Set(Ensure):
    # Add/Remove omsagent config for auoms
    if Ensure == "Present":
        WriteConf()
    else:
        RemoveConf()

    # Run script that will restart omsagent and enable+start/disable+stop auoms
    args = []
    args.append("/usr/bin/sudo")
    args.append("/opt/microsoft/omsconfig/Scripts/OMSAuditdPlugin.sh")
    if Ensure == "Present":
        args.append("enable")
    else:
        args.append("disable")
    proc = subprocess.Popen(args, -1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exit_code = proc.wait()
    if exit_code != 0:
        out_txt = proc.stdout.read().decode('utf8','replace').encode('utf8','replace')
        err_txt = proc.stderr.read().decode('utf8','replace').encode('utf8','replace')
        print("stdout: " + out_txt)
        LG().Log('INFO', "stdout: " + out_txt)
        print("stderr: " + err_txt)
        LG().Log('INFO', "stderr: " + err_txt)

    return [exit_code]

def Test(Ensure):
    DesiredState = False
    if Ensure == "Present":
        DesiredState = True

    state = IsPluginEnabled()
    if state == None:
        # Failed to determine state, return fake (Present)
        return [0]

    txt = ReadConf()
    if state != DesiredState or txt != OMSAGENT_CONF_TEXT:
        return [-1]

    return [0]

def Get(Ensure):
    state = IsPluginEnabled()
    txt = ReadConf()
    if state == None:
        return (-1, "Absent")
        
    if state and txt == OMSAGENT_CONF_TEXT:
        return (0, "Present")
    else:
        return (0, "Absent")

def IsPluginEnabled():
    args = []
    args.append("/usr/bin/sudo")
    args.append("/opt/microsoft/omsconfig/Scripts/OMSAuditdPlugin.sh")
    args.append("test")
    proc = subprocess.Popen(args, -1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exit_code = proc.wait()
    if exit_code < 0 or exit_code > 2:
        out_txt = proc.stdout.read().decode('utf8','replace').encode('utf8','replace')
        err_txt = proc.stderr.read().decode('utf8','replace').encode('utf8','replace')
        print("stdout: " + out_txt)
        LG().Log('INFO', "stdout: " + out_txt)
        print("stderr: " + err_txt)
        LG().Log('INFO', "stderr: " + err_txt)
        return None


    if exit_code == 2:
        LG().Log(
            'ERROR', 'OMS-Auditd-Plugin configuration at ' + PLUGIN_CONF + ' is missing or invalid.')
        return None
        
    if exit_code == 0:
        return True
    else:
        return False

def ReadConf():
    if not os.path.isfile(OMSAGENT_CONF):
        return None
    return codecs.open(OMSAGENT_CONF, 'r', 'utf8').read().encode('ascii','ignore')

def WriteConf():
    codecs.open(OMSAGENT_CONF, 'w', 'utf8').write(OMSAGENT_CONF_TEXT)

def RemoveConf():
    if os.path.isfile(OMSAGENT_CONF):
        os.remove(OMSAGENT_CONF)
