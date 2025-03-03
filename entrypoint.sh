#!/bin/sh

PERMISSION_ERROR="Check assets directory permissions & docker user or skip default assets install by setting the INIT_ASSETS env var to 0"

update_config() {
    while true; do
        echo "Updating configuration..."
        # Call your Python script here, and redirect its output to your config file
        # Replace "/path/to/your/script.py" with the actual path to your script,
        # and "/www/assets/config.yml" with the path to your config file
        python3 /traefik.py
        # Wait for 10 minutes
        sleep 60
    done
}

# Default assets & example configuration installation if possible.
if [[ "${INIT_ASSETS}" == "1" ]] && [[ ! -f "/www/assets/config.yml" ]]; then
    echo "No configuration found, installing default config & assets"
    if [[ ! -w "/www/assets/" ]]; then echo "Assets directory not writable. $PERMISSION_ERROR" && exit 1; fi

    while true; do echo n; done | cp -Ri /www/default-assets/* /www/assets/ &> /dev/null
    if [[ $? -ne 0 ]]; then echo "Fail to copy default assets. $PERMISSION_ERROR" && exit 1; fi

    yes n | cp -i /www/default-assets/config.yml.dist /www/assets/config.yml &> /dev/null
    if [[ $? -ne 0 ]]; then echo "Fail to copy default config file. $PERMISSION_ERROR" && exit 1; fi
fi

# Start the configuration update process in the background
update_config &

echo "Starting webserver"
exec lighttpd -D -f /lighttpd.conf
