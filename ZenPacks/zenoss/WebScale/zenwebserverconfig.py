##########################################################################
#
#   Copyright 2012 Zenoss, Inc. All Rights Reserved.
#
##########################################################################
import os
import sys
import shutil

zenhome = os.getenv('ZENHOME')
if not zenhome:
    raise Exception("$ZENHOME must be set")

#valid keys
# httpPort
# useSSL
# sslCert
# sslKey
defaultCert = 'ssl_certificate {INSTANCE_HOME}/etc/ssl/zenoss.crt'.format(INSTANCE_HOME=zenhome)
defaultKey = 'ssl_certificate_key {INSTANCE_HOME}/etc/ssl/zenoss.key'.format(INSTANCE_HOME=zenhome)

nginxCache = '{INSTANCE_HOME}/var/nginx/cache'.format(INSTANCE_HOME=zenhome)
nginxTmp = '{INSTANCE_HOME}/var/nginx/tmp'.format(INSTANCE_HOME=zenhome)
customHttpInclude = '{INSTANCE_HOME}/etc/nginx-custom-http-*.conf'.format(INSTANCE_HOME=zenhome)
customServerInclude = '{INSTANCE_HOME}/etc/nginx-custom-server-*.conf'.format(INSTANCE_HOME=zenhome)

config = {'useSSL': 'False',
          'httpPort': '8080',
          'sslPort': '443',
          'sslCert': defaultCert,
          'sslKey': defaultKey,
          'worker_processes': '4',
          'proxy_cache_path': nginxCache,
          'proxy_temp_path': nginxTmp + '/proxy',
          'client_body_temp_path': nginxTmp + '/client_body',
          'customServerInclude':customServerInclude,
          'customHttpInclude':customHttpInclude
}

#mapping of conf file values to substitutions
MAPPING2 = {'HTTP_PORT': 'httpPort',
            'PORT': 'httpPort',
            'SSL_PORT': 'sslPort',
            'SSL_CERT': 'sslCert',
            'SSL_KEY': 'sslKey',
            }

substitutionDefaults = {'INSTANCE_HOME':zenhome,
                        'PROTOCOL':'http',
                        'FILE_BEGIN':'',
                        'PRE_SERVERBLOCK':'',
                        'SSL_CONFIG': '',
                        }

print "Generating new config"

CONF_FILE_TEMPLATE = None
templatePath = '{INSTANCE_HOME}/etc/nginx.conf.template'.format(INSTANCE_HOME=zenhome)
try:
    lines = []
    with open(templatePath, 'r') as f:
        lines = f.readlines()
    #remove first comment
    if lines[0].startswith('#'):
        lines[0] = ''
    CONF_FILE_TEMPLATE = ''.join(lines)
except IOError:
    print "Could not find template at %s" % templatePath
    sys.exit(1)


webserverConf = '%s/etc/zenwebserver.conf' % zenhome
try:
    with open(webserverConf, 'r') as f:
        for line in f:
            line = line.strip()
            if line and  not line.startswith('#'):
                key, val = line.split(' ',1)
                config[key] = val.strip()
except IOError:
    print "%s not found; using default values" % webserverConf

substitutions = dict(substitutionDefaults)

#map conf file values to substitutions
for key, val in MAPPING2.items():
    if val in config:
        substitutions[key] = config.get(val)

#add all other values from conf file into substitutions
for key, val in config.items():
    #don't overwrite special config values
    if key not in substitutions:
        substitutions[key]=val

useSSL = config['useSSL'].lower() == 'true'
if useSSL:
    substitutions['PROTOCOL']='HTTPS'
    substitutions['PORT'] = config['sslPort']

    substitutions['FILE_BEGIN'] = """
#####################################################################################
#  SSL Configuration for zenwebserver
#####################################################################################
user zenoss zenoss;
"""
    substitutions['PRE_SERVERBLOCK']="""
    server {{
        listen 80;
        rewrite ^(.*)$ https://$host:{SSL_PORT}$1 break;
    }}

    server {{
        listen {HTTP_PORT};
        rewrite ^(.*)$ https://$host:{SSL_PORT}$1 break;
    }}
""".format(**substitutions)

    substitutions['SSL_CONFIG'] = """
        ssl on;
        # The names/paths of your certificate files
        {SSL_CERT};
        {SSL_KEY};
""".format(**substitutions)

headerline = """
#########################################################################################
# GENERATED FILE, DO NOT MODIFY. USE {INSTANCE_HOME}/etc/zenwebserver.conf to set options
#########################################################################################
""".format(**substitutions)


conf_file = CONF_FILE_TEMPLATE.format(**substitutions)

path = '%s/etc/nginx.conf' % zenhome
path_bak = '%s/etc/nginx.conf.prev' % zenhome

hasPreviousConf = False

if os.path.isfile(path):
    try:
        print "Saving copy of previous config to %s" % path_bak
        shutil.copy(path, path_bak)
        hasPreviousConf = True
    except IOError:
        print "Could not create back up of config"

try:
    print "Writing new config"
    with open(path, 'w') as f:
        f.write(headerline)
        f.write(conf_file)
except IOError as e:
    print "Error writing new config: %s" % e
    if hasPreviousConf and os.path.isfile(path_bak):
        print "Attempting to restore previous config"
        shutil.copy(path_bak, path)
        print "Previous config restored"
    sys.exit(1)
